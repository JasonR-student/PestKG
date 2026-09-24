"""Standalone validation of optimized shortest_path BFS logic.

Uses a fake in-memory graph to verify the batched BFS produces correct
shortest paths without needing DuckDB installed.  Run with:

    python apps/api/tests/validate_bfs.py
"""
from __future__ import annotations

from typing import Any


class FakeCursor:
    def __init__(self, rows: list[tuple], columns: list[str]):
        self._rows = rows
        self.description = [(col,) for col in columns]

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchmany(self, n):
        out = self._rows[:n]
        self._rows = self._rows[n:]
        return out

    def close(self):
        pass


class FakeConnection:
    """Minimal DuckDB-like connection backed by Python dicts."""

    def __init__(self, nodes: dict[str, dict], edges: list[dict]):
        self.nodes = nodes
        self.edges = edges

    def execute(self, sql: str, params: list | None = None):
        params = params or []
        sql_upper = sql.upper().strip()
        if sql_upper.startswith("SELECT * FROM EDGES"):
            return self._query_edges(sql, params)
        if sql_upper.startswith("SELECT * FROM NODES"):
            return self._query_nodes(sql, params)
        if "COUNT(*)" in sql_upper:
            return self._query_count(sql, params)
        raise NotImplementedError(f"Unhandled SQL: {sql}")

    def _query_edges(self, sql: str, params: list):
        if "IN (" in sql:
            import re
            matches = re.findall(r"IN \((\?(?:,\?)*)\)", sql)
            count = sum(m.count("?") for m in matches)
            half = count // 2
            ids = set(params[:half])
            limit = params[count] if len(params) > count else None
            rows = []
            for e in self.edges:
                if e["start_id"] in ids or e["end_id"] in ids:
                    rows.append(tuple(e[c] for c in self._edge_cols()))
                    if limit is not None and len(rows) >= limit:
                        break
            return FakeCursor(rows, self._edge_cols())
        rows = []
        for e in self.edges:
            if e["start_id"] == params[0] or e["end_id"] == params[0]:
                rows.append(tuple(e[c] for c in self._edge_cols()))
        return FakeCursor(rows, self._edge_cols())

    def _query_nodes(self, sql: str, params: list):
        if "IN (" in sql:
            ids = set(params)
            rows = []
            for nid in ids:
                if nid in self.nodes:
                    n = self.nodes[nid]
                    rows.append(tuple(n[c] for c in self._node_cols()))
            return FakeCursor(rows, self._node_cols())
        if "WHERE ID = ?" in sql.upper():
            nid = params[0]
            if nid in self.nodes:
                n = self.nodes[nid]
                return FakeCursor([tuple(n[c] for c in self._node_cols())], self._node_cols())
            return FakeCursor([], self._node_cols())
        raise NotImplementedError(f"Unhandled node SQL: {sql}")

    def _query_count(self, sql: str, params: list):
        return FakeCursor([(len(self.nodes),)], ["count"])

    @staticmethod
    def _edge_cols():
        return ["id", "start_id", "predicate", "end_id", "jurisdiction",
                "source_record_id", "source_url", "properties_json"]

    @staticmethod
    def _node_cols():
        return ["id", "type", "label_original", "label_en", "jurisdiction",
                "source_record_id", "source_url", "properties_json"]


class FakeRepo:
    """Minimal stand-in for DataRepository with the optimized methods."""

    def __init__(self, nodes: dict, edges: list):
        self._conn = FakeConnection(nodes, edges)

    def _connection(self):
        return self._conn

    @staticmethod
    def _records(cursor):
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    @staticmethod
    def _normalize_node(row):
        row = dict(row)
        row["properties"] = {}
        return row

    @staticmethod
    def _normalize_edge(row):
        row = dict(row)
        row["properties"] = {}
        return row

    def entity(self, node_id):
        cursor = self._conn.execute("SELECT * FROM nodes WHERE id = ? LIMIT 1", [node_id])
        records = self._records(cursor)
        return self._normalize_node(records[0]) if records else None

    def shortest_path(self, start_id: str, end_id: str, max_depth: int) -> dict[str, Any]:
        if start_id == end_id:
            node = self.entity(start_id)
            return {"nodes": [node] if node else [], "edges": []}

        connection = self._connection()
        parent: dict[str, tuple[str, dict[str, Any]]] = {}
        visited = {start_id}
        frontier = {start_id}
        for _ in range(max_depth):
            if not frontier:
                break
            ids = sorted(frontier)
            placeholders = ",".join("?" for _ in ids)
            cursor = connection.execute(
                f"""
                SELECT * FROM edges
                WHERE start_id IN ({placeholders}) OR end_id IN ({placeholders})
                """,
                [*ids, *ids],
            )
            next_frontier: set[str] = set()
            found = False
            for row in self._records(cursor):
                start = row["start_id"]
                end = row["end_id"]
                if start in frontier:
                    neighbor, anchor = end, start
                elif end in frontier:
                    neighbor, anchor = start, end
                else:
                    continue
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor] = (anchor, self._normalize_edge(row))
                if neighbor == end_id:
                    found = True
                    break
                next_frontier.add(neighbor)
            if found:
                break
            frontier = next_frontier

        if end_id not in parent:
            return {"nodes": [], "edges": []}

        path_nodes: list[str] = [end_id]
        path_edges: list[dict[str, Any]] = []
        current = end_id
        while current != start_id:
            anchor, edge = parent[current]
            path_nodes.append(anchor)
            path_edges.append(edge)
            current = anchor
        path_nodes.reverse()
        path_edges.reverse()

        placeholders = ",".join("?" for _ in path_nodes)
        nodes = self._records(
            connection.execute(
                f"SELECT * FROM nodes WHERE id IN ({placeholders})", path_nodes
            )
        )
        node_map = {row["id"]: self._normalize_node(row) for row in nodes}
        return {
            "nodes": [node_map[node] for node in path_nodes if node in node_map],
            "edges": path_edges,
        }


def make_node(nid):
    return {"id": nid, "type": "Test", "label_original": nid, "label_en": nid,
            "jurisdiction": "AU", "source_record_id": "", "source_url": "",
            "properties_json": "{}"}


def make_edge(eid, start, end):
    return {"id": eid, "start_id": start, "predicate": "related", "end_id": end,
            "jurisdiction": "AU", "source_record_id": "", "source_url": "",
            "properties_json": "{}"}


def test_shortest_path():
    nodes = {n: make_node(n) for n in ["A", "B", "C", "D", "E"]}
    edges = [
        make_edge("e1", "A", "B"), make_edge("e2", "B", "C"),
        make_edge("e3", "C", "D"), make_edge("e4", "A", "E"),
        make_edge("e5", "E", "D"),
    ]
    repo = FakeRepo(nodes, edges)

    result = repo.shortest_path("A", "D", 3)
    assert len(result["edges"]) == 2, f"Expected 2 edges, got {len(result['edges'])}"
    assert [n["id"] for n in result["nodes"]] == ["A", "E", "D"]
    print("  PASS: A->D shortest path = A-E-D (2 edges)")

    result = repo.shortest_path("A", "A", 3)
    assert len(result["nodes"]) == 1 and result["nodes"][0]["id"] == "A"
    assert len(result["edges"]) == 0
    print("  PASS: A->A returns single node")

    result = repo.shortest_path("A", "C", 3)
    assert len(result["edges"]) == 2
    assert [n["id"] for n in result["nodes"]] == ["A", "B", "C"]
    print("  PASS: A->C = A-B-C (2 edges)")

    result = repo.shortest_path("A", "D", 1)
    assert result["nodes"] == [] and result["edges"] == []
    print("  PASS: A->D with max_depth=1 returns empty")

    result = repo.shortest_path("A", "Z", 3)
    assert result["nodes"] == [] and result["edges"] == []
    print("  PASS: A->Z (nonexistent) returns empty")

    nodes2 = {n: make_node(n) for n in ["X", "Y"]}
    repo2 = FakeRepo(nodes2, [])
    result = repo2.shortest_path("X", "Y", 3)
    assert result["nodes"] == [] and result["edges"] == []
    print("  PASS: disconnected X->Y returns empty")


def test_undirected():
    nodes = {n: make_node(n) for n in ["A", "B", "C"]}
    edges = [make_edge("e1", "A", "B"), make_edge("e2", "B", "C")]
    repo = FakeRepo(nodes, edges)
    result = repo.shortest_path("C", "A", 3)
    assert len(result["edges"]) == 2
    assert [n["id"] for n in result["nodes"]] == ["C", "B", "A"]
    print("  PASS: C->A = C-B-A (undirected traversal)")


def test_diamond():
    nodes = {n: make_node(n) for n in ["A", "B", "C", "D"]}
    edges = [
        make_edge("e1", "A", "B"), make_edge("e2", "B", "D"),
        make_edge("e3", "A", "C"), make_edge("e4", "C", "D"),
    ]
    repo = FakeRepo(nodes, edges)
    result = repo.shortest_path("A", "D", 3)
    assert len(result["edges"]) == 2
    path_ids = [n["id"] for n in result["nodes"]]
    assert path_ids[0] == "A" and path_ids[-1] == "D" and len(path_ids) == 3
    print(f"  PASS: diamond A->D = {'-'.join(path_ids)} (2 edges)")


if __name__ == "__main__":
    print("Validating optimized shortest_path BFS logic")
    print("=" * 60)
    test_shortest_path()
    test_undirected()
    test_diamond()
    print("=" * 60)
    print("All shortest_path validations passed.")
