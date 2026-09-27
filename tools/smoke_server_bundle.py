"""Check real primary/reference graph queries through the delivered proxy."""

import json
import sys
from urllib.request import Request, urlopen

base = sys.argv[1].rstrip("/")


def request(path, body=None):
    encoded = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=encoded, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=120) as response:
        return json.load(response)


catalog = request("/api/v1/graph/catalog")["data"]
assert catalog["base_release_id"] == "PestKG_A_Data_Release_v1.0"
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
