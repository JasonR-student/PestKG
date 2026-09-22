from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGURE_ROOT = PROJECT_ROOT / "research" / "figures"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "research" / "figures"
OUTPUT_ROOT = ARTIFACT_ROOT / "output"
DELIVERY_PARENT = ARTIFACT_ROOT / "delivery"
PACKAGE_NAME = "pestkg_figure_delivery_2026-09-02"
PACKAGE_ROOT = DELIVERY_PARENT / PACKAGE_NAME
ZIP_PATH = DELIVERY_PARENT / f"{PACKAGE_NAME}.zip"
FIGURE_STEMS = [f"figure_{index:02d}_" for index in range(1, 9)]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def figure_files(index: int) -> list[Path]:
    prefix = f"figure_{index:02d}_"
    return sorted(path for path in OUTPUT_ROOT.glob(f"{prefix}*") if path.suffix in {".svg", ".pdf", ".png"})


def checked_reset_package_root() -> None:
    delivery_resolved = DELIVERY_PARENT.resolve()
    package_resolved = PACKAGE_ROOT.resolve()
    if package_resolved.parent != delivery_resolved:
        raise RuntimeError(f"Refusing to reset unexpected path: {package_resolved}")
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    PACKAGE_ROOT.mkdir(parents=True)


def copy_files(paths: list[Path], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, destination / path.name)


def write_delivery_readme(source_mode: str, neo4j_verified: bool) -> None:
    runtime_note = (
        "Neo4j runtime verified: the figures were queried from the isolated PaperSample/PaperProjection database."
        if neo4j_verified
        else "Neo4j runtime not verified on this machine: figures were generated from the frozen release CSV fallback. Docker Compose configuration is validated separately."
    )
    text = f"""# PestKG complete figure delivery package

Release: 2026.08.3_federated
Generated: 2026-09-02
Graph source mode: {source_mode}

{runtime_note}

## Contents

- main_figures: Figure 8 in SVG, PDF, and 600 dpi PNG.
- supplementary_figures: Figures 1-7 in SVG, PDF, and 600 dpi PNG.
- editable: all SVG files for journal editing.
- raster_600dpi: all review-ready PNG files.
- source_tables: node, edge, and projection weights used by Figure 6.
- captions: English and Chinese figure captions.
- methods: reproducibility notes, Neo4j queries, and local run instructions.
- MANIFEST_SHA256.csv: checksum and byte size for every packaged file.

The reference images supplied by the researcher informed only the choice of diagram families. Their data, labels, and copyrighted layouts are not reproduced.
"""
    (PACKAGE_ROOT / "README.md").write_text(text, encoding="utf-8")


def write_checksum_manifest() -> None:
    files = sorted(path for path in PACKAGE_ROOT.rglob("*") if path.is_file() and path.name != "MANIFEST_SHA256.csv")
    with (PACKAGE_ROOT / "MANIFEST_SHA256.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "sha256", "bytes"])
        writer.writeheader()
        for path in files:
            writer.writerow(
                {
                    "file": str(path.relative_to(PACKAGE_ROOT)).replace("\\", "/"),
                    "sha256": digest(path),
                    "bytes": path.stat().st_size,
                }
            )


def build_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACKAGE_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, Path(PACKAGE_NAME) / path.relative_to(PACKAGE_ROOT))


def main() -> None:
    required = [
        OUTPUT_ROOT / f"figure_{index:02d}_{name}.{suffix}"
        for index, name in [
            (1, "dataset_landscape"),
            (2, "single_site_apvma"),
            (3, "federated_chebi_agrovoc"),
            (4, "pestkg_storyboard"),
            (5, "apvma_entity_relationship"),
            (6, "bipartite_and_projections"),
            (7, "multisite_external_chain"),
            (8, "complete_main_figure"),
        ]
        for suffix in ("svg", "pdf", "png")
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing figure outputs: {[path.name for path in missing]}")

    figure_manifest = json.loads((OUTPUT_ROOT / "FIGURE_MANIFEST.json").read_text(encoding="utf-8"))
    checked_reset_package_root()
    copy_files(figure_files(8), PACKAGE_ROOT / "main_figures")
    copy_files([path for index in range(1, 8) for path in figure_files(index)], PACKAGE_ROOT / "supplementary_figures")
    copy_files(sorted(OUTPUT_ROOT.glob("figure_*.svg")), PACKAGE_ROOT / "editable")
    copy_files(sorted(OUTPUT_ROOT.glob("figure_*.png")), PACKAGE_ROOT / "raster_600dpi")
    copy_files(sorted((OUTPUT_ROOT / "source_tables").glob("*.csv")), PACKAGE_ROOT / "source_tables")
    copy_files(
        [OUTPUT_ROOT / "CAPTIONS_EN.md", OUTPUT_ROOT / "CAPTIONS_ZH.md"],
        PACKAGE_ROOT / "captions",
    )
    copy_files(
        [
            FIGURE_ROOT / "FIGURE_METHODS.md",
            FIGURE_ROOT / "LOCAL_RUN_2026-09-02.md",
            FIGURE_ROOT / "neo4j" / "queries.cypher",
        ],
        PACKAGE_ROOT / "methods",
    )
    copy_files([OUTPUT_ROOT / "FIGURE_MANIFEST.json"], PACKAGE_ROOT / "methods")
    write_delivery_readme(
        figure_manifest["source_mode"],
        bool(figure_manifest.get("neo4j_runtime_verified")),
    )
    write_checksum_manifest()
    build_zip()
    print(f"Built delivery directory: {PACKAGE_ROOT}")
    print(f"Built ZIP archive: {ZIP_PATH}")


if __name__ == "__main__":
    main()
