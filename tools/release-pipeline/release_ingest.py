from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

try:
    from .build_release_sample import build_release_sample
    from .export_graph_formats import export_ntriples, sha256_sidecar
    from .materialize_parquet import materialize
    from .portal_metadata import ensure_portal_metadata
    from .publish_downloads import publish_downloads
    from .validate_analytics import validate_analytics
    from .validate_release import sha256_file, validate
except ImportError:
    from build_release_sample import build_release_sample
    from export_graph_formats import export_ntriples, sha256_sidecar
    from materialize_parquet import materialize
    from portal_metadata import ensure_portal_metadata
    from publish_downloads import publish_downloads
    from validate_analytics import validate_analytics
    from validate_release import sha256_file, validate


REQUIRED_SENTINELS = (
    "manifest_sha256.csv",
    "04_validation/final_integrity_report.json",
    "04_validation/federated_build_report.json",
    "04_validation/entity_relation_inventory.json",
    "04_validation/semantic_coverage_corrected.csv",
    "06_neo4j_import/nodes.csv.gz",
    "06_neo4j_import/relationships.csv.gz",
    "06_neo4j_import/preparation_report.json",
)
STAGES = (
    "inspect",
    "extract",
    "validate_source",
    "metadata",
    "analytics",
    "validate_analytics",
    "sample",
    "rdf",
    "downloads",
    "finalize",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


@dataclass(frozen=True)
class ArchiveEntry:
    path: str
    size: int
    is_dir: bool = False


@dataclass(frozen=True)
class ArchiveInspection:
    archive: str
    archive_sha256: str
    archive_bytes: int
    release_id: str
    archive_root: str
    member_count: int
    uncompressed_bytes: int


@dataclass(frozen=True)
class IngestOptions:
    release_root: Path
    state_root: Path
    release_id: str | None = None
    published_at: str | None = None
    generate_rdf: bool = True
    sample_uses_per_jurisdiction: int = 2
    max_members: int = 200_000
    max_uncompressed_bytes: int = 1_000_000_000_000
    disk_headroom_ratio: float = 1.15
    threads: int | None = None
    memory_limit: str | None = None
    seven_zip: str | None = None


def safe_member_name(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if not normalized or "\x00" in normalized:
        raise RuntimeError(f"Unsafe empty archive member: {value!r}")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe archive member path: {value}")
    if re.match(r"^[A-Za-z]:", normalized):
        raise RuntimeError(f"Unsafe drive-qualified archive member: {value}")
    return path.as_posix()


def find_7zip(configured: str | None = None) -> str | None:
    candidates = (
        configured,
        os.environ.get("SEVEN_ZIP"),
        shutil.which("7zz"),
        shutil.which("7z"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    )
    return next(
        (str(candidate) for candidate in candidates if candidate and Path(candidate).is_file()),
        None,
    )


def _zip_entries(archive: Path) -> list[ArchiveEntry]:
    with zipfile.ZipFile(archive) as handle:
        return [
            ArchiveEntry(
                path=safe_member_name(info.filename),
                size=int(info.file_size),
                is_dir=info.is_dir(),
            )
            for info in handle.infolist()
            if info.filename.strip("/\\")
        ]


def _tar_entries(archive: Path) -> list[ArchiveEntry]:
    with tarfile.open(archive, mode="r:*") as handle:
        result = []
        for member in handle.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f"Archive links are not allowed: {member.name}")
            if not member.isfile() and not member.isdir():
                continue
            result.append(
                ArchiveEntry(
                    path=safe_member_name(member.name),
                    size=int(member.size),
                    is_dir=member.isdir(),
                )
            )
        return result


def _seven_zip_entries(archive: Path, executable: str) -> list[ArchiveEntry]:
    result = subprocess.run(
        [executable, "l", "-slt", str(archive.resolve())],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    entries: list[ArchiveEntry] = []
    record: dict[str, str] = {}
    inside_files = False
    for line in result.stdout.splitlines():
        if line.startswith("----------"):
            inside_files = True
            record = {}
            continue
        if not inside_files:
            continue
        if not line.strip():
            if record.get("Path"):
                entries.append(
                    ArchiveEntry(
                        path=safe_member_name(record["Path"]),
                        size=int(record.get("Size", "0") or 0),
                        is_dir=record.get("Folder") == "+",
                    )
                )
            record = {}
            continue
        if " = " in line:
            key, value = line.split(" = ", 1)
            record[key] = value
    if record.get("Path"):
        entries.append(
            ArchiveEntry(
                path=safe_member_name(record["Path"]),
                size=int(record.get("Size", "0") or 0),
                is_dir=record.get("Folder") == "+",
            )
        )
    if not entries:
        raise RuntimeError("7-Zip did not report any archive members")
    return entries


def list_archive(archive: Path, seven_zip: str | None = None) -> list[ArchiveEntry]:
    suffixes = "".join(archive.suffixes).lower()
    if suffixes.endswith(".zip"):
        return _zip_entries(archive)
    if any(
        suffixes.endswith(suffix)
        for suffix in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz")
    ):
        return _tar_entries(archive)
    executable = find_7zip(seven_zip)
    if executable:
        return _seven_zip_entries(archive, executable)
    raise RuntimeError(
        "RAR and 7z archives require 7-Zip. Install 7zz/7z or set SEVEN_ZIP."
    )


def discover_release_root(
    entries: list[ArchiveEntry], requested_release_id: str | None = None
) -> tuple[str, str]:
    files = {entry.path for entry in entries if not entry.is_dir}
    candidates: set[str] = set()
    anchor = REQUIRED_SENTINELS[1]
    for name in files:
        suffix = f"/{anchor}"
        if name == anchor:
            candidates.add("")
        elif name.endswith(suffix):
            candidates.add(name[: -len(suffix)])
    valid = [
        root
        for root in candidates
        if all((f"{root}/{sentinel}" if root else sentinel) in files for sentinel in REQUIRED_SENTINELS)
    ]
    if requested_release_id:
        valid = [root for root in valid if PurePosixPath(root).name == requested_release_id]
    if len(valid) != 1:
        raise RuntimeError(
            "Expected exactly one complete release root in the archive; "
            f"found {len(valid)}: {sorted(valid)}"
        )
    root = valid[0]
    release_id = PurePosixPath(root).name if root else requested_release_id
    if not release_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", release_id):
        raise RuntimeError(f"Invalid release identifier discovered from archive: {release_id!r}")
    return root, release_id


def inspect_archive(archive: Path, options: IngestOptions) -> tuple[ArchiveInspection, list[ArchiveEntry]]:
    archive = archive.resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"Archive not found: {archive}")
    entries = list_archive(archive, options.seven_zip)
    if len(entries) > options.max_members:
        raise RuntimeError(
            f"Archive member limit exceeded: {len(entries)} > {options.max_members}"
        )
    total_size = sum(entry.size for entry in entries if not entry.is_dir)
    if total_size > options.max_uncompressed_bytes:
        raise RuntimeError(
            "Archive uncompressed-size limit exceeded: "
            f"{total_size} > {options.max_uncompressed_bytes}"
        )
    archive_root, release_id = discover_release_root(entries, options.release_id)
    return (
        ArchiveInspection(
            archive=str(archive),
            archive_sha256=sha256_file(archive),
            archive_bytes=archive.stat().st_size,
            release_id=release_id,
            archive_root=archive_root,
            member_count=len(entries),
            uncompressed_bytes=total_size,
        ),
        entries,
    )


def _selected_entries(entries: list[ArchiveEntry], archive_root: str) -> list[ArchiveEntry]:
    prefix = f"{archive_root}/" if archive_root else ""
    return [entry for entry in entries if entry.path == archive_root or entry.path.startswith(prefix)]


def _safe_destination(root: Path, member_name: str) -> Path:
    destination = (root / PurePosixPath(member_name)).resolve()
    if not destination.is_relative_to(root.resolve()):
        raise RuntimeError(f"Archive extraction escaped staging root: {member_name}")
    return destination


def extract_release(
    archive: Path,
    entries: list[ArchiveEntry],
    archive_root: str,
    extraction_root: Path,
    seven_zip: str | None = None,
) -> Path:
    selected = _selected_entries(entries, archive_root)
    if not selected:
        raise RuntimeError("No release members were selected for extraction")
    extraction_root.mkdir(parents=True, exist_ok=False)
    suffixes = "".join(archive.suffixes).lower()
    if suffixes.endswith(".zip"):
        with zipfile.ZipFile(archive) as handle:
            by_name = {safe_member_name(info.filename): info for info in handle.infolist()}
            for entry in selected:
                destination = _safe_destination(extraction_root, entry.path)
                if entry.is_dir:
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with handle.open(by_name[entry.path]) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
    elif any(
        suffixes.endswith(suffix)
        for suffix in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz")
    ):
        selected_names = {entry.path for entry in selected}
        with tarfile.open(archive, mode="r:*") as handle:
            for member in handle.getmembers():
                normalized = safe_member_name(member.name)
                if normalized not in selected_names:
                    continue
                destination = _safe_destination(extraction_root, normalized)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise RuntimeError(f"Unsupported archive member type: {member.name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = handle.extractfile(member)
                if source is None:
                    raise RuntimeError(f"Unable to extract archive member: {member.name}")
                with source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
    else:
        executable = find_7zip(seven_zip)
        if not executable:
            raise RuntimeError("7-Zip is required to extract this archive")
        include = f"{archive_root}/*" if archive_root else "*"
        subprocess.run(
            [
                executable,
                "x",
                "-y",
                "-spf-",
                f"-o{extraction_root}",
                str(archive.resolve()),
                include,
            ],
            check=True,
        )
    release_dir = _safe_destination(extraction_root, archive_root) if archive_root else extraction_root
    if not release_dir.is_dir():
        raise RuntimeError(f"Extracted release root is missing: {release_dir}")
    return release_dir


@contextmanager
def ingest_lock(state_root: Path) -> Iterator[None]:
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "ingest.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        details = lock_path.read_text(encoding="utf-8", errors="replace")
        raise RuntimeError(f"Another release ingest is active: {details}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started_at": utc_now()}, handle)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


class IngestJob:
    def __init__(self, path: Path, initial: dict[str, Any]) -> None:
        self.path = path
        if path.is_file():
            self.value = json.loads(path.read_text(encoding="utf-8"))
            if self.value.get("archive_sha256") != initial["archive_sha256"]:
                raise RuntimeError("Existing ingest job belongs to different archive bytes")
        else:
            self.value = initial
            self.save()

    def save(self) -> None:
        self.value["updated_at"] = utc_now()
        atomic_write_json(self.path, self.value)

    def stage_complete(self, name: str) -> bool:
        return self.value.get("stages", {}).get(name, {}).get("status") in {
            "completed",
            "skipped",
        }

    def run(self, name: str, operation: Callable[[], Any]) -> Any:
        if self.stage_complete(name):
            return self.value["stages"][name].get("result")
        stages = self.value.setdefault("stages", {})
        previous = stages.get(name, {})
        stages[name] = {
            "status": "running",
            "started_at": utc_now(),
            "attempt": int(previous.get("attempt", 0)) + 1,
        }
        self.value["status"] = "running"
        self.value["current_stage"] = name
        self.save()
        try:
            result = operation()
        except Exception as exc:
            stages[name].update(
                {
                    "status": "failed",
                    "finished_at": utc_now(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            self.value["status"] = "failed"
            self.save()
            raise
        stages[name].update(
            {
                "status": "completed",
                "finished_at": utc_now(),
                "result": result,
            }
        )
        self.save()
        return result

    def skip(self, name: str, reason: str) -> None:
        if self.stage_complete(name):
            return
        self.value.setdefault("stages", {})[name] = {
            "status": "skipped",
            "finished_at": utc_now(),
            "reason": reason,
        }
        self.save()


def ingest_archive(archive: Path, options: IngestOptions) -> Path:
    options.release_root.mkdir(parents=True, exist_ok=True)
    options.state_root.mkdir(parents=True, exist_ok=True)
    with ingest_lock(options.state_root):
        inspection, entries = inspect_archive(archive, options)
        release_id = inspection.release_id
        destination = options.release_root.resolve() / release_id
        job_id = f"{release_id}-{inspection.archive_sha256[:12]}"
        work_root = options.release_root.resolve() / ".staging" / job_id
        extraction_root = work_root / "extracted"
        release_work = (
            extraction_root / PurePosixPath(inspection.archive_root)
            if inspection.archive_root
            else extraction_root
        )
        state_path = options.state_root.resolve() / "ingest-jobs" / f"{job_id}.json"
        job = IngestJob(
            state_path,
            {
                "schema_version": 1,
                "job_id": job_id,
                "status": "pending",
                "release_id": release_id,
                "archive": inspection.archive,
                "archive_sha256": inspection.archive_sha256,
                "archive_bytes": inspection.archive_bytes,
                "archive_root": inspection.archive_root,
                "created_at": utc_now(),
                "stages": {},
            },
        )
        if destination.is_dir() and job.value.get("status") == "completed":
            return destination
        if destination.exists():
            raise FileExistsError(f"Immutable release already exists: {destination}")

        required_free = max(
            256 * 1024 * 1024,
            int(inspection.uncompressed_bytes * options.disk_headroom_ratio),
        )
        available = shutil.disk_usage(options.release_root).free
        if available < required_free:
            raise RuntimeError(
                f"Insufficient free space for release staging: {available} < {required_free}"
            )

        job.run("inspect", lambda: asdict(inspection))

        def extract_stage() -> str:
            if extraction_root.exists():
                shutil.rmtree(extraction_root)
            extracted = extract_release(
                Path(inspection.archive),
                entries,
                inspection.archive_root,
                extraction_root,
                options.seven_zip,
            )
            return str(extracted)

        job.run("extract", extract_stage)
        if not release_work.is_dir():
            raise RuntimeError(
                "Ingest state marks extraction complete, but the staging release is missing"
            )
        job.run("validate_source", lambda: validate(release_work))
        job.run(
            "metadata",
            lambda: [
                str(path)
                for path in ensure_portal_metadata(
                    release_work, published_at=options.published_at
                )
            ],
        )
        job.run(
            "analytics",
            lambda: str(
                materialize(
                    release_work,
                    threads=options.threads,
                    memory_limit=options.memory_limit,
                    temp_directory=work_root / "duckdb-tmp",
                )
            ),
        )
        job.run("validate_analytics", lambda: validate_analytics(release_work))

        def sample_stage() -> str:
            sample_dir = release_work / "sample"
            if sample_dir.is_dir():
                return str(sample_dir)
            return str(
                build_release_sample(
                    release_work,
                    uses_per_jurisdiction=options.sample_uses_per_jurisdiction,
                )
            )

        job.run("sample", sample_stage)
        if options.generate_rdf:
            job.run(
                "rdf",
                lambda: str(
                    sha256_sidecar(
                        export_ntriples(
                            release_work,
                            release_work / "08_rdf" / f"pestkg-{release_id}.nt.gz",
                        )
                    )
                ),
            )
        else:
            job.skip("rdf", "disabled by --skip-rdf")
        job.run("downloads", lambda: str(publish_downloads(release_work)))

        def finalize_stage() -> str:
            provenance = {
                **asdict(inspection),
                "processed_at": utc_now(),
                "generate_rdf": options.generate_rdf,
                "sample_uses_per_jurisdiction": options.sample_uses_per_jurisdiction,
                "pipeline_threads": options.threads,
                "pipeline_memory_limit": options.memory_limit,
            }
            atomic_write_json(release_work / "ingest.json", provenance)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(release_work, destination)
            return str(destination)

        job.run("finalize", finalize_stage)
        job.value["status"] = "completed"
        job.value["current_stage"] = None
        job.value["destination"] = str(destination)
        job.save()
        shutil.rmtree(work_root, ignore_errors=True)
        return destination


def job_status(state_root: Path) -> list[dict[str, Any]]:
    jobs = state_root / "ingest-jobs"
    if not jobs.is_dir():
        return []
    result = []
    for path in sorted(jobs.glob("*.json"), reverse=True):
        result.append(json.loads(path.read_text(encoding="utf-8")))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pestkg-ingest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_command = subparsers.add_parser("inspect")
    inspect_command.add_argument("archive", type=Path)
    inspect_command.add_argument("--release-id")
    inspect_command.add_argument("--seven-zip")

    process = subparsers.add_parser("process")
    process.add_argument("archive", type=Path)
    process.add_argument("--release-root", type=Path, required=True)
    process.add_argument("--state-root", type=Path, required=True)
    process.add_argument("--release-id")
    process.add_argument("--published-at")
    process.add_argument("--skip-rdf", action="store_true")
    process.add_argument("--sample-uses-per-jurisdiction", type=int, default=2)
    process.add_argument("--threads", type=int)
    process.add_argument("--memory-limit")
    process.add_argument("--seven-zip")

    status = subparsers.add_parser("status")
    status.add_argument("--state-root", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "inspect":
            options = IngestOptions(
                release_root=Path.cwd(),
                state_root=Path.cwd(),
                release_id=args.release_id,
                seven_zip=args.seven_zip,
            )
            inspection, _ = inspect_archive(args.archive, options)
            result: Any = asdict(inspection)
        elif args.command == "status":
            result = job_status(args.state_root)
        else:
            destination = ingest_archive(
                args.archive,
                IngestOptions(
                    release_root=args.release_root,
                    state_root=args.state_root,
                    release_id=args.release_id,
                    published_at=args.published_at,
                    generate_rdf=not args.skip_rdf,
                    sample_uses_per_jurisdiction=args.sample_uses_per_jurisdiction,
                    threads=args.threads,
                    memory_limit=args.memory_limit,
                    seven_zip=args.seven_zip,
                ),
            )
            result = {"release_id": destination.name, "destination": str(destination)}
    except Exception as exc:
        print(
            json.dumps(
                {"error": {"type": type(exc).__name__, "message": str(exc)}},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
