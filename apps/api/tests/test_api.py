from __future__ import annotations

from fastapi.testclient import TestClient

from pestkg_api.config import get_settings


def test_health_and_release_inventory(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["data_mode"] == "sample"
    assert health.json()["neo4j_configured"] is False

    overview = client.get("/api/v1/stats/overview")
    assert overview.status_code == 200
    data = overview.json()["data"]
    assert data["jurisdictions"] == 12
    assert data["source_records"] == 821_183
    assert data["country_nodes"] == 1_204_973
    assert data["country_edges"] == 9_739_818
    assert data["distribution_status"] == "blocked_pending_manifest_rebuild"


def test_multilingual_search_and_injection_safety(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"q": "毒死蜱", "limit": 10})
    assert response.status_code == 200
    assert response.json()["data"]

    injection = client.get(
        "/api/v1/search", params={"q": "%' OR 1=1 --", "limit": 100}
    )
    assert injection.status_code == 200
    assert injection.json()["data"] == []


def test_registration_filter_cursor_and_export(client: TestClient) -> None:
    payload = {
        "filters": {"jurisdictions": ["AU"], "active_ingredient": "GLYPHOSATE"},
        "page_size": 1,
    }
    response = client.post("/api/v1/registration-uses/query", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]
    assert body["data"][0]["jurisdiction"] == "AU"

    invalid_cursor = client.post(
        "/api/v1/registration-uses/query",
        json={"filters": {}, "cursor": "not-a-cursor", "page_size": 20},
    )
    assert invalid_cursor.status_code == 400

    export = client.post(
        "/api/v1/exports/registration-uses",
        json={"filters": {"jurisdictions": ["AU"]}},
    )
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "use_id" in export.text.splitlines()[0]


def test_unfiltered_registration_cursor_preserves_nullable_fields(
    client: TestClient,
) -> None:
    first = client.post(
        "/api/v1/registration-uses/query",
        json={"filters": {}, "page_size": 20},
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert len(first_payload["data"]) == 20
    assert first_payload["meta"]["next_cursor"]
    assert any(row["registration_date"] is None for row in first_payload["data"])

    second = client.post(
        "/api/v1/registration-uses/query",
        json={
            "filters": {},
            "cursor": first_payload["meta"]["next_cursor"],
            "page_size": 20,
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["data"]
    assert second_payload["data"][0]["use_id"] != first_payload["data"][0]["use_id"]


def test_mixed_date_formats_and_export_limit(client: TestClient) -> None:
    valid_on = client.post(
        "/api/v1/registration-uses/query",
        json={
            "filters": {"jurisdictions": ["GB"], "valid_on": "2026-01-01"},
            "page_size": 20,
        },
    )
    assert valid_on.status_code == 200
    assert valid_on.json()["data"]

    settings = get_settings()
    original_limit = settings.export_limit
    settings.export_limit = 1
    try:
        oversized = client.post(
            "/api/v1/exports/registration-uses", json={"filters": {}}
        )
    finally:
        settings.export_limit = original_limit
    assert oversized.status_code == 422
    detail = oversized.json()["detail"]
    assert detail["code"] == "export_too_large"
    assert detail["download_url"] == "/downloads/2026.08.3_federated/"


def test_release_artifacts_and_versioned_downloads(client: TestClient) -> None:
    release = client.get("/api/v1/releases")
    assert release.status_code == 200
    artifacts = release.json()["data"][0]["artifacts"]
    assert any(item["path"] == "samples/pestkg-sample.jsonld" for item in artifacts)

    index = client.get("/downloads/2026.08.3_federated/index.json")
    assert index.status_code == 200
    assert index.json()["release_id"] == "2026.08.3_federated"


def test_entity_neighborhood_and_comparison(client: TestClient) -> None:
    query = client.post(
        "/api/v1/registration-uses/query",
        json={"filters": {"jurisdictions": ["AU"]}, "page_size": 1},
    )
    use_id = query.json()["data"][0]["use_id"]

    entity = client.get(f"/api/v1/entities/{use_id}")
    assert entity.status_code == 200
    assert entity.json()["data"]["id"] == use_id

    graph = client.get(
        "/api/v1/graph/neighborhood", params={"node_id": use_id, "depth": 1}
    )
    assert graph.status_code == 200
    assert len(graph.json()["data"]["nodes"]) >= 2
    assert graph.json()["data"]["edges"]

    comparison = client.get("/api/v1/compare/q5", params={"jurisdiction": "AU"})
    assert comparison.status_code == 200
    assert comparison.json()["data"]

    missing_question = client.get("/api/v1/compare/q9")
    assert missing_question.status_code == 404


def test_entity_not_found_and_path_depth_limit(client: TestClient) -> None:
    missing = client.get("/api/v1/entities/UNKNOWN:1")
    assert missing.status_code == 404

    depth = client.get(
        "/api/v1/graph/path",
        params={"start_id": "A", "end_id": "B", "max_depth": 4},
    )
    assert depth.status_code == 422
