"""Check real primary/reference graph queries through the delivered proxy."""

import json
import sys
from urllib.request import Request, urlopen

base = sys.argv[1].rstrip("/")
release = "PestKG_A_Data_Release_v1.0"


def request(path, body=None):
    encoded = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=encoded, headers={
        "Content-Type": "application/json", "X-PestKG-Release": release,
    })
    with urlopen(req, timeout=120) as response:
        result = json.load(response)
    assert result["release_id"] == release, path
    print("Verified", path, flush=True)
    return result


assert request("/api/v1/health/ready")["status"] == "ready"
overview = request("/api/v1/datasets/overview")["data"]
assert overview["mode"] == "full"
assert overview["inventory"]["kg_nodes"] >= 1_000_000
request("/api/v1/releases/active")
assert request("/api/v1/registration-uses/query", {"filters": {}, "page_size": 1})["data"]
assert request(f"/downloads/{release}/index.json")["artifacts"]
catalog = request("/api/v1/graph/catalog")["data"]
assert catalog["base_release_id"] == release
assert {"jurisdiction:AU", "jurisdiction:TW", "reference:CHEBI", "reference:AGROVOC"}.issubset(
    {scope["id"] for scope in catalog["scopes"]})
for scope, category in [("jurisdiction:AU", "PesticideProduct"), ("reference:CHEBI", "ChEBITerm")]:
    graph = request("/api/v1/graph/query", {
        "scope": scope, "type": category, "query": "", "limit": 60, "provenance": True,
    })["data"]
    assert any(node["type"] == category for node in graph["nodes"]), scope
with urlopen(base + "/graph", timeout=30) as response:
    html = response.read().decode()
    assert 'lang="en"' in html and "PestKG" in html
print("Delivered English frontend and primary/reference graph queries passed")
