from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Iterable

try:
    from .export_graph_formats import export_sample_formats
    from .validate_release import sha256_file
except ImportError:
    from export_graph_formats import export_sample_formats
    from validate_release import sha256_file


def link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size == source.stat().st_size and sha256_file(destination) == sha256_file(source):
            return
        raise FileExistsError(f"Download artifact already exists with different content: {destination}")
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def selected_files(release_dir: Path) -> Iterable[tuple[Path, Path]]:
    exact = [
        (release_dir / "release.json", Path("metadata/release.json")),
        (release_dir / "schema.json", Path("metadata/schema.json")),
        (release_dir / "countries.json", Path("metadata/countries.json")),
        (
            release_dir / "03_federation_alignment/country_to_shared_edges.csv",
            Path("federation/country_to_shared_edges.csv"),
        ),
    ]
    yield from ((source, target) for source, target in exact if source.is_file())

    directory_specs = [
        (release_dir / "01_country_graphs", Path("country_graphs"), {".csv", ".gz", ".json"}),
        (release_dir / "04_validation", Path("quality"), {".csv", ".json"}),
        (release_dir / "06_neo4j_import", Path("neo4j"), {".gz", ".json"}),
        (
            release_dir / "06_competency_questions",
            Path("competency_questions"),
            {".csv", ".gz", ".md"},
        ),
        (release_dir / "analytics", Path("parquet"), {".parquet"}),
        (release_dir / "08_rdf", Path("rdf"), {".gz", ".sha256"}),
    ]
    for source_root, target_root, suffixes in directory_specs:
        if not source_root.is_dir():
            continue
        for source in sorted(source_root.rglob("*")):
            if source.is_file() and source.suffix.lower() in suffixes:
                yield source, target_root / source.relative_to(source_root)


def artifact_category(relative_path: Path) -> str:
    return relative_path.parts[0] if len(relative_path.parts) > 1 else "release"


def publish_downloads(release_dir: Path) -> Path:
    release_dir = release_dir.resolve()
    release_id = release_dir.name
    download_dir = release_dir / "downloads"
    download_dir.mkdir(exist_ok=True)

    sample_dir = release_dir / "sample"
    if sample_dir.is_dir():
        export_sample_formats(sample_dir, download_dir / "samples")

    for source, relative_target in selected_files(release_dir):
        link_or_copy(source, download_dir / relative_target)

    files = sorted(
        path
        for path in download_dir.rglob("*")
        if path.is_file() and path.name not in {"index.json", "SHA256SUMS"}
    )
    artifacts = []
    checksum_lines = []
    for path in files:
        relative = path.relative_to(download_dir)
        relative_url = relative.as_posix()
        digest = sha256_file(path)
        checksum_lines.append(f"{digest}  {relative_url}")
        artifacts.append(
            {
                "path": relative_url,
                "url": f"/downloads/{release_id}/{relative_url}",
                "category": artifact_category(relative),
                "format": "".join(path.suffixes).lstrip("."),
                "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        )

    (download_dir / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="ascii"
    )
    index_path = download_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "release_id": release_id,
                "license": "CC BY 4.0 for project-derived data",
                "excluded_pending_license_audit": [
                    "raw official source snapshots",
                    "BCPC",
                    "ChEBI",
                    "AGROVOC",
                    "FRAC",
                    "HRAC",
                    "IRAC",
                ],
                "artifacts": artifacts,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    args = parser.parse_args()
    print(f"Published download index: {publish_downloads(args.release_dir)}")


if __name__ == "__main__":
    main()
