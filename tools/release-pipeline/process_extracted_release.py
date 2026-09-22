#!/usr/bin/env python3
"""
处理已经手动解压好的 PestKG release 目录。
跳过 RAR 解压步骤，直接执行：验证 -> 复制元数据模板 -> 生成Parquet -> 验证分析 -> 导出RDF -> 重建下载索引。

用法:
  python3 process_extracted_release.py \
    --release-dir /path/to/extracted/2026.08.3_federated \
    --output /srv/pestkg/releases \
    [--skip-rdf]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# 允许直接运行时导入同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_graph_formats import export_ntriples, sha256_sidecar
from materialize_parquet import materialize
from publish_downloads import publish_downloads
from validate_analytics import validate_analytics
from validate_release import validate

RELEASE_ID = "2026.08.3_federated"


def process(release_dir: Path, output_root: Path, generate_rdf: bool = True) -> Path:
    output_root = output_root.resolve()
    destination = output_root / RELEASE_ID

    release_dir = release_dir.resolve()
    if not release_dir.is_dir():
        raise FileNotFoundError(f"Release directory not found: {release_dir}")

    # 如果源目录和目标目录不同，移动过去
    if release_dir != destination:
        if destination.exists():
            raise FileExistsError(
                f"Immutable release already exists at destination: {destination}. "
                "Delete it first or use a different output root."
            )
        print(f"Moving {release_dir} -> {destination}")
        shutil.move(str(release_dir), str(destination))
    else:
        print(f"Release already at destination: {destination}")

    # 1. 验证解压后的目录
    print("Validating release directory...")
    validate(destination)

    # 2. 复制元数据模板（release.json, countries.json, schema.json, sample/, downloads/）
    template = Path(__file__).resolve().parents[2] / "data" / "releases" / RELEASE_ID
    if not template.is_dir():
        raise FileNotFoundError(
            f"Portal metadata template is missing: {template}\n"
            "请确保 data/releases/2026.08.3_federated/ 目录存在于项目根目录下。"
        )

    print("Copying metadata templates...")
    for name in ("release.json", "countries.json", "schema.json"):
        source = template / name
        if not source.exists():
            raise FileNotFoundError(f"Template file missing: {source}")
        shutil.copy2(source, destination / name)

    sample_source = template / "sample"
    if sample_source.is_dir():
        target_sample = destination / "sample"
        if target_sample.exists():
            shutil.rmtree(target_sample)
        shutil.copytree(sample_source, target_sample)

    (destination / "downloads").mkdir(exist_ok=True)
    download_readme = template / "downloads" / "README.md"
    if download_readme.exists():
        shutil.copy2(download_readme, destination / "downloads" / "README.md")

    # 3. 生成列式Parquet分析数据
    print("Materializing Parquet analytics...")
    materialize(destination)

    # 4. 验证分析数据
    print("Validating analytics...")
    validate_analytics(destination)

    # 5. 导出RDF N-Triples（可选）
    if generate_rdf:
        print("Exporting RDF N-Triples...")
        rdf_output = export_ntriples(
            destination, destination / "08_rdf" / f"pestkg-{RELEASE_ID}.nt.gz"
        )
        sha256_sidecar(rdf_output)
    else:
        print("Skipping RDF export (--skip-rdf)")

    # 6. 重建版本化下载目录索引
    print("Publishing download catalog...")
    publish_downloads(destination)

    print(f"\nProcessed immutable release: {destination}")
    print("Done.")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process an already-extracted PestKG release directory"
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        required=True,
        help="Path to the extracted 2026.08.3_federated directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/srv/pestkg/releases"),
        help="Output root directory (default: /srv/pestkg/releases)",
    )
    parser.add_argument(
        "--skip-rdf",
        action="store_true",
        help="Skip the large N-Triples RDF export",
    )
    args = parser.parse_args()
    process(args.release_dir, args.output, generate_rdf=not args.skip_rdf)


if __name__ == "__main__":
    main()
