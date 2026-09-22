from __future__ import annotations

import json
from pathlib import Path

from pestkg_api.main import app


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "packages/api-contract/openapi-v1.1.json"


def test_openapi_v1_1_snapshot_is_current() -> None:
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert app.openapi() == expected


def test_release_aware_routes_publish_both_selectors() -> None:
    contract = app.openapi()
    excluded = {
        "/api/v1/releases",
        "/api/v1/releases/active",
        "/api/v1/releases/{release_id}",
    }
    for path, operations in contract["paths"].items():
        if not path.startswith("/api/v1/") or path in excluded:
            continue
        for operation in operations.values():
            selectors = {
                (parameter["in"], parameter["name"])
                for parameter in operation.get("parameters", [])
            }
            assert ("query", "release") in selectors, path
            assert ("header", "X-PestKG-Release") in selectors, path


def test_data_routes_publish_concrete_response_schemas() -> None:
    contract = app.openapi()
    expected = {
        ("/api/v1/releases", "get"): "Envelope_list_ReleaseData__",
        ("/api/v1/releases/active", "get"): "Envelope_ReleaseData_",
        ("/api/v1/stats/overview", "get"): "Envelope_OverviewData_",
        ("/api/v1/stats/countries", "get"): "Envelope_list_CountryData__",
        ("/api/v1/search", "get"): "Envelope_list_EntityData__",
        ("/api/v1/compare/{question}", "get"): "Envelope_list_ComparisonRow__",
        ("/api/v1/registration-uses/query", "post"):
            "Envelope_list_RegistrationUseData__",
        ("/api/v1/entities/{node_id}", "get"): "Envelope_EntityData_",
        ("/api/v1/graph/neighborhood", "get"): "Envelope_GraphData_",
        ("/api/v1/graph/path", "get"): "Envelope_GraphData_",
    }

    for (path, method), schema_name in expected.items():
        schema = contract["paths"][path][method]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert schema == {"$ref": f"#/components/schemas/{schema_name}"}

    comparison = contract["components"]["schemas"]["ComparisonRow"]
    assert comparison["additionalProperties"] == {
        "anyOf": [{"type": "string"}, {"type": "null"}]
    }
