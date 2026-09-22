from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from .export_graph_formats import export_ntriples, sha256_sidecar
    from .materialize_parquet import materialize
    from .publish_downloads import publish_downloads
    from .validate_analytics import validate_analytics
    from .validate_release import validate
except ImportError:
    from export_graph_formats import export_ntriples, sha256_sidecar
    from materialize_parquet import materialize
    from publish_downloads import publish_downloads
    from validate_analytics import validate_analytics
    from validate_release import validate


RELEASE_ID = "2026.08.3_federated"
ARCHIVE_ROOT = f"multicountry_pesticide_kg_research/release/{RELEASE_ID}"


def find_7zip() -> str | None:
    configured = os.environ.get("SEVEN_ZIP")
    candidates = [
        configured,
        shutil.which("7z"),
        shutil.which("7zz"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


def extract_release(archive: Path, staging: Path) -> None:
    seven_zip = find_7zip()
    if seven_zip:
        subprocess.run(
            [
                seven_zip,
                "x",
                "-y",
                f"-o{staging}",
                str(archive.resolve()),
                f"{ARCHIVE_ROOT}/*",
            ],
            check=True,
        )
        return
    if sys.platform == "win32" and archive.suffix.lower() == ".rar":
        raise RuntimeError(
            "7-Zip is required for Unicode-safe RAR extraction on Windows. "
            "Install 7-Zip or set SEVEN_ZIP to 7z.exe."
        )
    subprocess.run(
        ["tar", "-xf", str(archive.resolve()), "-C", str(staging), ARCHIVE_ROOT],
        check=True,
    )


def prepare(archive: Path, output_root: Path, generate_rdf: bool = True) -> Path:
    output_root = output_root.resolve()
    destination = output_root / RELEASE_ID
    staging = output_root / f".{RELEASE_ID}.staging"
    if destination.exists():
        raise FileExistsError(
            f"Immutable release already exists: {destination}. Choose another output root."
        )
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    extract_release(archive, staging)
    extracted = staging / ARCHIVE_ROOT
    if not extracted.exists():
        raise RuntimeError("The expected release directory was not extracted")
    validate(extracted)
    shutil.move(str(extracted), str(destination))
    shutil.rmtree(staging)
    template = Path(__file__).resolve().parents[2] / "data/releases" / RELEASE_ID
    for name in ("release.json", "countries.json", "schema.json"):
        source = template / name
        if not source.exists():
            raise FileNotFoundError(f"Portal metadata template is missing: {source}")
        shutil.copy2(source, destination / name)
    sample_source = template / "sample"
    if sample_source.is_dir():
        shutil.copytree(sample_source, destination / "sample")
    (destination / "downloads").mkdir(exist_ok=True)
    download_readme = template / "downloads/README.md"
    if download_readme.exists():
        shutil.copy2(download_readme, destination / "downloads/README.md")
    materialize(destination)
    validate_analytics(destination)
    if generate_rdf:
        rdf_output = export_ntriples(
            destination, destination / "08_rdf" / f"pestkg-{RELEASE_ID}.nt.gz"
        )
        sha256_sidecar(rdf_output)
    publish_downloads(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-rdf",
        action="store_true",
        help="Prepare analytics and downloads without the large N-Triples export",
    )
    args = parser.parse_args()
    destination = prepare(args.archive, args.output, generate_rdf=not args.skip_rdf)
    print(f"Prepared immutable release: {destination}")


if __name__ == "__main__":
    main()
