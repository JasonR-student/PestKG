from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings
from .releases import ReleaseError, ReleaseManager, sha256_file, validate_release_dir


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def register_release(
    manager: ReleaseManager, release_id: str, *, verify_downloads: bool = True
) -> dict[str, Any]:
    validation = validate_release_dir(
        manager.release_dir(release_id), verify_downloads=verify_downloads
    )
    registry = manager.registry()
    releases = dict(registry.get("releases", {}))
    metadata = validation["metadata"]
    entry = {
        "release_id": release_id,
        "schema_version": validation["schema_version"],
        "registered_at": timestamp(),
        "status": (
            "validated"
            if metadata.get("distribution_status") == "ready"
            else "blocked"
        ),
        "distribution_status": metadata.get("distribution_status", "unknown"),
        "release_sha256": sha256_file(manager.release_dir(release_id) / "release.json"),
    }
    releases[release_id] = entry
    atomic_write_json(
        manager.registry_path,
        {"registry_version": 1, "updated_at": timestamp(), "releases": releases},
    )
    return entry


def activate_release(
    manager: ReleaseManager, release_id: str, *, allow_blocked: bool = False
) -> dict[str, Any]:
    entry = register_release(manager, release_id)
    if entry["status"] == "blocked" and not allow_blocked:
        raise ReleaseError(
            "release_distribution_blocked",
            "Release validation passed, but public distribution is blocked",
            status_code=409,
            details={"release_id": release_id},
        )
    previous = None
    if manager.active_state_path.is_file():
        previous = json.loads(manager.active_state_path.read_text(encoding="utf-8")).get(
            "release_id"
        )
    elif manager.configured_release_id != release_id:
        previous = manager.configured_release_id
    state = {
        "release_id": release_id,
        "previous_release_id": previous,
        "activated_at": timestamp(),
    }
    atomic_write_json(manager.active_state_path, state)

    registry = manager.registry()
    releases = dict(registry["releases"])
    if previous in releases and previous != release_id:
        releases[previous] = {**releases[previous], "status": "retired"}
    releases[release_id] = {**releases[release_id], "status": "active"}
    atomic_write_json(
        manager.registry_path,
        {"registry_version": 1, "updated_at": timestamp(), "releases": releases},
    )
    return state


def rollback_release(manager: ReleaseManager, *, allow_blocked: bool = False) -> dict[str, Any]:
    if not manager.active_state_path.is_file():
        raise ReleaseError(
            "rollback_unavailable",
            "No previous active release is recorded",
            status_code=409,
        )
    state = json.loads(manager.active_state_path.read_text(encoding="utf-8"))
    previous = state.get("previous_release_id")
    if not previous:
        raise ReleaseError(
            "rollback_unavailable",
            "No previous active release is recorded",
            status_code=409,
        )
    return activate_release(manager, str(previous), allow_blocked=allow_blocked)


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="pestkg-release")
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir)
    parser.add_argument("--state-dir", type=Path, default=settings.state_dir)
    parser.add_argument("--default-release", default=settings.release_id)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")
    for name in ("validate", "register", "smoke-test"):
        command = subparsers.add_parser(name)
        command.add_argument("release_id")
        if name in {"validate", "register"}:
            command.add_argument("--skip-download-checksums", action="store_true")

    activate = subparsers.add_parser("activate")
    activate.add_argument("release_id")
    activate.add_argument("--allow-blocked", action="store_true")

    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--allow-blocked", action="store_true")
    return parser


def execute(args: argparse.Namespace) -> dict[str, Any]:
    manager = ReleaseManager(args.data_dir, args.state_dir, args.default_release)
    if args.command == "list":
        return {
            "active_release": manager.active_release_id,
            "releases": manager.list_releases(),
        }
    if args.command == "validate":
        validation = validate_release_dir(
            manager.release_dir(args.release_id),
            verify_downloads=not args.skip_download_checksums,
        )
        return {
            "release_id": validation["release_id"],
            "schema_version": validation["schema_version"],
            "distribution_status": validation["metadata"].get(
                "distribution_status", "unknown"
            ),
            "artifact_count": len(validation["artifacts"]),
            "download_checksums_verified": not args.skip_download_checksums,
        }
    if args.command == "register":
        return register_release(
            manager,
            args.release_id,
            verify_downloads=not args.skip_download_checksums,
        )
    if args.command == "activate":
        return activate_release(
            manager, args.release_id, allow_blocked=args.allow_blocked
        )
    if args.command == "rollback":
        return rollback_release(manager, allow_blocked=args.allow_blocked)
    if args.command == "smoke-test":
        context = manager.resolve(args.release_id)
        overview = context.repository.overview()
        return {
            "release_id": context.release_id,
            "schema_version": context.schema_version,
            "mode": context.repository.mode,
            "jurisdictions": overview["jurisdictions"],
            "source_records": overview["source_records"],
        }
    raise AssertionError(f"Unsupported command: {args.command}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = execute(args)
    except ReleaseError as exc:
        print(
            json.dumps(
                {"error": {"code": exc.code, "message": exc.message, **exc.details}},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
