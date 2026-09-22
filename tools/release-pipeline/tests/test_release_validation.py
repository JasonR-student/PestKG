from __future__ import annotations

import csv
from pathlib import Path

import pytest

from validate_release import REQUIRED_COMPETENCY_OUTPUTS, sha256_file, verify_manifest


def write_manifest(release: Path, paths: list[Path]) -> None:
    with (release / "manifest_sha256.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "sha256", "bytes"])
        writer.writeheader()
        for path in paths:
            writer.writerow(
                {
                    "relative_path": path.relative_to(release).as_posix(),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )


def test_manifest_verifies_required_competency_outputs(tmp_path: Path) -> None:
    release = tmp_path / "release"
    paths = []
    for relative_path in sorted(REQUIRED_COMPETENCY_OUTPUTS):
        path = release / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative_path.encode("utf-8"))
        paths.append(path)
    write_manifest(release, paths)
    assert verify_manifest(release) == 5


def test_manifest_rejects_tampered_file(tmp_path: Path) -> None:
    release = tmp_path / "release"
    paths = []
    for relative_path in sorted(REQUIRED_COMPETENCY_OUTPUTS):
        path = release / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative_path.encode("utf-8"))
        paths.append(path)
    write_manifest(release, paths)
    paths[0].write_text("tampered", encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest verification failed"):
        verify_manifest(release)
