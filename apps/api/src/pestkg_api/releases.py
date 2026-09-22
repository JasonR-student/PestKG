from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .repository import DataRepository


RELEASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
REQUIRED_RELEASE_FILES = ("release.json", "schema.json", "countries.json")


class ReleaseError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class ReleaseContext:
    release_id: str
    schema_version: str
    repository: DataRepository


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_without_duplicates(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ReleaseError(
                    "duplicate_json_key",
                    f"Duplicate JSON key {key!r} in {path.name}",
                    status_code=422,
                    details={"path": str(path), "key": key},
                )
            value[key] = item
        return value

    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=reject_duplicates)
    except FileNotFoundError as exc:
        raise ReleaseError(
            "release_file_missing",
            f"Required release file not found: {path.name}",
            status_code=422,
            details={"path": str(path)},
        ) from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(
            "release_json_invalid",
            f"Invalid JSON in {path.name}",
            status_code=422,
            details={"path": str(path), "line": exc.lineno, "column": exc.colno},
        ) from exc
    if not isinstance(value, dict):
        raise ReleaseError(
            "release_json_invalid",
            f"Expected an object in {path.name}",
            status_code=422,
            details={"path": str(path)},
        )
    return value


def validate_release_dir(release_dir: Path, *, verify_downloads: bool) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    if not release_dir.is_dir():
        raise ReleaseError(
            "release_not_found",
            f"Release directory not found: {release_dir.name}",
            status_code=404,
            details={"release_id": release_dir.name},
        )
    for name in REQUIRED_RELEASE_FILES:
        if not (release_dir / name).is_file():
            raise ReleaseError(
                "release_file_missing",
                f"Required release file not found: {name}",
                status_code=422,
                details={"release_id": release_dir.name, "file": name},
            )

    metadata = read_json_without_duplicates(release_dir / "release.json")
    schema = read_json_without_duplicates(release_dir / "schema.json")
    release_id = str(metadata.get("release_id", ""))
    if release_id != release_dir.name:
        raise ReleaseError(
            "release_id_mismatch",
            "release.json does not match its directory name",
            status_code=422,
            details={"directory": release_dir.name, "release_id": release_id},
        )

    download_index_path = release_dir / "downloads/index.json"
    artifacts: list[dict[str, Any]] = []
    if download_index_path.is_file():
        download_index = read_json_without_duplicates(download_index_path)
        if download_index.get("release_id") != release_id:
            raise ReleaseError(
                "download_release_mismatch",
                "Download index belongs to a different release",
                status_code=422,
                details={"release_id": release_id},
            )
        raw_artifacts = download_index.get("artifacts", [])
        if not isinstance(raw_artifacts, list):
            raise ReleaseError(
                "download_index_invalid",
                "Download index artifacts must be an array",
                status_code=422,
                details={"release_id": release_id},
            )
        artifacts = raw_artifacts

    if verify_downloads:
        download_root = (release_dir / "downloads").resolve()
        for artifact in artifacts:
            relative = str(artifact.get("path", ""))
            candidate = (download_root / relative).resolve()
            try:
                candidate.relative_to(download_root)
            except ValueError as exc:
                raise ReleaseError(
                    "download_path_invalid",
                    "Download index contains an unsafe path",
                    status_code=422,
                    details={"release_id": release_id, "path": relative},
                ) from exc
            if not candidate.is_file():
                raise ReleaseError(
                    "download_artifact_missing",
                    "Download artifact is missing",
                    status_code=422,
                    details={"release_id": release_id, "path": relative},
                )
            expected_bytes = int(artifact.get("bytes", -1))
            expected_hash = str(artifact.get("sha256", "")).lower()
            if candidate.stat().st_size != expected_bytes or sha256_file(candidate) != expected_hash:
                raise ReleaseError(
                    "download_artifact_mismatch",
                    "Download artifact does not match its catalog entry",
                    status_code=422,
                    details={"release_id": release_id, "path": relative},
                )

    return {
        "release_id": release_id,
        "schema_version": str(
            metadata.get("schema_version") or schema.get("schema_version") or "1.0"
        ),
        "metadata": metadata,
        "artifacts": artifacts,
    }


class ReleaseManager:
    def __init__(
        self,
        data_dir: Path,
        state_dir: Path,
        configured_release_id: str | None,
        *,
        cache_size: int = 3,
    ) -> None:
        self.data_dir = data_dir.resolve()
        self.state_dir = state_dir.resolve()
        self.configured_release_id = configured_release_id
        self.cache_size = max(1, cache_size)
        self._cache: OrderedDict[str, ReleaseContext] = OrderedDict()
        self._lock = threading.RLock()

    @property
    def active_state_path(self) -> Path:
        return self.state_dir / "active-release.json"

    @property
    def registry_path(self) -> Path:
        return self.state_dir / "registry.json"

    def available_release_ids(self) -> list[str]:
        if not self.data_dir.is_dir():
            return []
        return sorted(
            child.name
            for child in self.data_dir.iterdir()
            if child.is_dir()
            and RELEASE_ID_PATTERN.fullmatch(child.name)
            and (child / "release.json").is_file()
        )

    def _active_from_state(self) -> str | None:
        if not self.active_state_path.is_file():
            return None
        state = read_json_without_duplicates(self.active_state_path)
        release_id = state.get("release_id")
        return str(release_id) if release_id else None

    @property
    def active_release_id(self) -> str:
        state_release = self._active_from_state()
        if state_release:
            self._validate_release_id(state_release)
            if (self.data_dir / state_release / "release.json").is_file():
                return state_release
            raise ReleaseError(
                "active_release_unavailable",
                "Active release is not available on disk",
                status_code=503,
                details={"release_id": state_release},
            )
        if self.configured_release_id:
            self._validate_release_id(self.configured_release_id)
            if (self.data_dir / self.configured_release_id / "release.json").is_file():
                return self.configured_release_id
            raise ReleaseError(
                "configured_release_unavailable",
                "Configured release is not available on disk",
                status_code=503,
                details={"release_id": self.configured_release_id},
            )
        available = self.available_release_ids()
        if available:
            return available[-1]
        raise ReleaseError(
            "no_release_available",
            "No readable data release is available",
            status_code=503,
        )

    @staticmethod
    def _validate_release_id(release_id: str) -> None:
        if not RELEASE_ID_PATTERN.fullmatch(release_id):
            raise ReleaseError(
                "release_id_invalid",
                "Release ID contains unsupported characters",
                status_code=400,
                details={"release_id": release_id},
            )

    def release_dir(self, release_id: str) -> Path:
        self._validate_release_id(release_id)
        release_dir = (self.data_dir / release_id).resolve()
        try:
            release_dir.relative_to(self.data_dir)
        except ValueError as exc:
            raise ReleaseError(
                "release_id_invalid",
                "Release ID resolves outside the release root",
                status_code=400,
                details={"release_id": release_id},
            ) from exc
        return release_dir

    def resolve(self, release_id: str | None = None) -> ReleaseContext:
        selected = release_id or self.active_release_id
        release_dir = self.release_dir(selected)
        with self._lock:
            cached = self._cache.get(selected)
            if cached is not None:
                self._cache.move_to_end(selected)
                return cached
            validated = validate_release_dir(release_dir, verify_downloads=False)
            context = ReleaseContext(
                release_id=selected,
                schema_version=validated["schema_version"],
                repository=DataRepository(release_dir),
            )
            self._cache[selected] = context
            self._cache.move_to_end(selected)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
            return context

    def registry(self) -> dict[str, Any]:
        if not self.registry_path.is_file():
            return {"registry_version": 1, "releases": {}}
        registry = read_json_without_duplicates(self.registry_path)
        releases = registry.get("releases")
        if not isinstance(releases, dict):
            raise ReleaseError(
                "registry_invalid",
                "Release registry must contain a releases object",
                status_code=503,
            )
        return registry

    def release_summary(self, release_id: str) -> dict[str, Any]:
        validated = validate_release_dir(self.release_dir(release_id), verify_downloads=False)
        registry_entry = self.registry().get("releases", {}).get(release_id, {})
        return {
            **validated["metadata"],
            "schema_version": validated["schema_version"],
            "artifacts": validated["artifacts"],
            "is_active": release_id == self.active_release_id,
            "registry_status": registry_entry.get("status", "discovered"),
            "registered_at": registry_entry.get("registered_at"),
        }

    def list_releases(self) -> list[dict[str, Any]]:
        releases = [self.release_summary(release_id) for release_id in self.available_release_ids()]
        active = [item for item in releases if item["is_active"]]
        inactive = sorted(
            (item for item in releases if not item["is_active"]),
            key=lambda item: (
                str(item.get("published_at", "")),
                str(item["release_id"]),
            ),
            reverse=True,
        )
        return [*active, *inactive]

    def download_path(self, release_id: str, relative_path: str) -> Path:
        download_root = (self.release_dir(release_id) / "downloads").resolve()
        candidate = (download_root / relative_path).resolve()
        try:
            candidate.relative_to(download_root)
        except ValueError as exc:
            raise ReleaseError(
                "download_path_invalid",
                "Download path resolves outside the release catalog",
                status_code=400,
                details={"release_id": release_id, "path": relative_path},
            ) from exc
        if not candidate.is_file():
            raise ReleaseError(
                "download_not_found",
                "Download artifact not found",
                status_code=404,
                details={"release_id": release_id, "path": relative_path},
            )
        return candidate
