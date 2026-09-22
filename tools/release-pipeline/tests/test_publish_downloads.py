from __future__ import annotations

import json
import shutil
from pathlib import Path

from publish_downloads import publish_downloads


ROOT = Path(__file__).resolve().parents[3]
TRACKED_RELEASE = ROOT / "data/releases/2026.08.3_federated"


def load_json_without_duplicate_keys(path: Path) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            assert key not in value, f"Duplicate JSON key {key!r} in {path}"
            value[key] = item
        return value

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=reject_duplicates)


def test_publish_downloads_builds_versioned_index(tmp_path: Path) -> None:
    release = tmp_path / "2026.08.3_federated"
    release.mkdir()
    for name in ("release.json", "schema.json", "countries.json"):
        shutil.copy2(TRACKED_RELEASE / name, release / name)
    shutil.copytree(TRACKED_RELEASE / "sample", release / "sample")
    downloads = release / "downloads"
    downloads.mkdir()
    (downloads / "README.md").write_text("sample", encoding="utf-8")

    index_path = publish_downloads(release)
    with index_path.open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert index["release_id"] == "2026.08.3_federated"
    paths = {artifact["path"] for artifact in index["artifacts"]}
    assert "samples/pestkg-sample.jsonld" in paths
    assert "samples/pestkg-sample.graphml" in paths
    assert "metadata/release.json" in paths
    assert (downloads / "SHA256SUMS").is_file()
    assert (downloads / "metadata/release.json").read_bytes() == (release / "release.json").read_bytes()


def test_tracked_release_metadata_has_unique_json_keys() -> None:
    release = load_json_without_duplicate_keys(TRACKED_RELEASE / "release.json")
    published = load_json_without_duplicate_keys(TRACKED_RELEASE / "downloads/metadata/release.json")

    assert published == release
