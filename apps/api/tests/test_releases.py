from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pestkg_api.config import Settings
from pestkg_api.main import create_app
from pestkg_api.release_cli import activate_release, register_release, rollback_release
from pestkg_api.releases import ReleaseError, ReleaseManager


ROOT = Path(__file__).resolve().parents[3]
SOURCE_RELEASE = ROOT / "data/releases/2026.08.3_federated"


def copy_release(root: Path, release_id: str, published_at: str) -> Path:
    destination = root / release_id
    shutil.copytree(SOURCE_RELEASE, destination)

    release_path = destination / "release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["release_id"] = release_id
    release["published_at"] = published_at
    release_path.write_text(
        json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    index_path = destination / "downloads/index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["release_id"] = release_id
    for artifact in index["artifacts"]:
        artifact["url"] = f"/downloads/{release_id}/{artifact['path']}"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destination


@pytest.fixture
def release_environment(tmp_path: Path) -> tuple[Path, Path, str, str]:
    data_dir = tmp_path / "releases"
    state_dir = tmp_path / "state"
    first = "2026.08.3_federated"
    second = "2026.09.1_federated"
    copy_release(data_dir, first, "2026-08-24")
    copy_release(data_dir, second, "2026-09-01")
    return data_dir, state_dir, first, second


def test_release_manager_switches_active_release_without_restart(
    release_environment: tuple[Path, Path, str, str],
) -> None:
    data_dir, state_dir, first, second = release_environment
    manager = ReleaseManager(data_dir, state_dir, first)
    assert manager.resolve().release_id == first

    state_dir.mkdir()
    (state_dir / "active-release.json").write_text(
        json.dumps({"release_id": second}), encoding="utf-8"
    )
    assert manager.resolve().release_id == second
    assert manager.resolve(first).release_id == first
    assert [item["release_id"] for item in manager.list_releases()] == [second, first]


def test_release_selector_contract_and_cursor_isolation(
    release_environment: tuple[Path, Path, str, str],
) -> None:
    data_dir, state_dir, first, second = release_environment
    application = create_app(
        Settings(
            data_dir=data_dir,
            state_dir=state_dir,
            release_id=first,
            cors_origins="http://localhost",
        )
    )
    with TestClient(application) as client:
        selected = client.get(
            "/api/v1/stats/overview",
            headers={"X-PestKG-Release": second, "X-Request-ID": "contract-test"},
        )
        assert selected.status_code == 200
        assert selected.json()["api_version"] == "1.1"
        assert selected.json()["release_id"] == second
        assert selected.headers["X-PestKG-Release"] == second
        assert selected.headers["X-Request-ID"] == "contract-test"

        query_selected = client.get(
            "/api/v1/stats/overview", params={"release": second}
        )
        assert query_selected.json()["release_id"] == second

        conflict = client.get(
            "/api/v1/stats/overview",
            params={"release": first},
            headers={"X-PestKG-Release": second},
        )
        assert conflict.status_code == 400
        assert conflict.json()["error"]["code"] == "release_selector_conflict"

        missing = client.get(
            "/api/v1/stats/overview",
            headers={"X-PestKG-Release": "2099.01.1_missing"},
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "release_not_found"
        assert missing.json()["error"]["request_id"]

        first_page = client.post(
            "/api/v1/registration-uses/query",
            headers={"X-PestKG-Release": first},
            json={"filters": {}, "page_size": 1},
        )
        cursor = first_page.json()["meta"]["next_cursor"]
        assert cursor

        wrong_release = client.post(
            "/api/v1/registration-uses/query",
            headers={"X-PestKG-Release": second},
            json={"filters": {}, "page_size": 1, "cursor": cursor},
        )
        assert wrong_release.status_code == 400
        assert wrong_release.json()["error"]["code"] == "cursor_release_mismatch"

        wrong_filters = client.post(
            "/api/v1/registration-uses/query",
            headers={"X-PestKG-Release": first},
            json={
                "filters": {"jurisdictions": ["AU"]},
                "page_size": 1,
                "cursor": cursor,
            },
        )
        assert wrong_filters.status_code == 400
        assert wrong_filters.json()["error"]["code"] == "cursor_filter_mismatch"


def test_release_cli_register_activate_and_rollback(
    release_environment: tuple[Path, Path, str, str],
) -> None:
    data_dir, state_dir, first, second = release_environment
    manager = ReleaseManager(data_dir, state_dir, first)

    entry = register_release(manager, first)
    assert entry["status"] == "blocked"
    with pytest.raises(ReleaseError, match="public distribution is blocked"):
        activate_release(manager, first)

    activate_release(manager, first, allow_blocked=True)
    activate_release(manager, second, allow_blocked=True)
    assert manager.active_release_id == second

    rollback = rollback_release(manager, allow_blocked=True)
    assert rollback["release_id"] == first
    assert manager.active_release_id == first


def test_explicit_missing_active_release_fails_closed(tmp_path: Path) -> None:
    data_dir = tmp_path / "releases"
    state_dir = tmp_path / "state"
    copy_release(data_dir, "2026.08.3_federated", "2026-08-24")
    state_dir.mkdir()
    (state_dir / "active-release.json").write_text(
        json.dumps({"release_id": "2026.09.1_missing"}), encoding="utf-8"
    )
    manager = ReleaseManager(data_dir, state_dir, None)
    with pytest.raises(ReleaseError, match="Active release is not available"):
        _ = manager.active_release_id
