from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase


class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password), connection_timeout=3
        )

    def close(self) -> None:
        self._driver.close()

    def verify(self) -> bool:
        self._driver.verify_connectivity()
        return True

    def neighborhood(
        self, node_id: str, depth: int, node_limit: int, edge_limit: int
    ) -> dict[str, Any]:
        depth = max(1, min(depth, 2))
        query = f"""
        MATCH p=(root:Entity {{nodeId: $node_id}})-[*1..{depth}]-(neighbor)
        WITH root, p LIMIT $path_limit
        UNWIND nodes(p) AS node
        UNWIND relationships(p) AS rel
        RETURN collect(DISTINCT node)[0..$node_limit] AS nodes,
               collect(DISTINCT rel)[0..$edge_limit] AS relationships
        """
        with self._driver.session() as session:
            record = session.run(
                query,
                node_id=node_id,
                path_limit=min(edge_limit, 2_000),
                node_limit=node_limit,
                edge_limit=edge_limit,
            ).single()
            if record is None:
                return {"nodes": [], "edges": []}
            nodes = [self._node_to_dict(node) for node in record["nodes"]]
            edges = [self._relationship_to_dict(rel) for rel in record["relationships"]]
            return {"nodes": nodes, "edges": edges}

    def shortest_path(self, start_id: str, end_id: str, max_depth: int) -> dict[str, Any]:
        max_depth = max(1, min(max_depth, 3))
        query = f"""
        MATCH (start:Entity {{nodeId: $start_id}}), (end:Entity {{nodeId: $end_id}})
        MATCH path = shortestPath((start)-[*1..{max_depth}]-(end))
        RETURN nodes(path) AS nodes, relationships(path) AS relationships
        """
        with self._driver.session() as session:
            record = session.run(query, start_id=start_id, end_id=end_id).single()
            if record is None:
                return {"nodes": [], "edges": []}
            return {
                "nodes": [self._node_to_dict(node) for node in record["nodes"]],
                "edges": [
                    self._relationship_to_dict(rel)
                    for rel in record["relationships"]
                ],
            }

    @staticmethod
    def _node_to_dict(node: Any) -> dict[str, Any]:
        properties = dict(node)
        return {
            "id": properties.pop("nodeId", ""),
            "type": next(
                (label for label in node.labels if label not in {"Entity", "CountryEntity"}),
                "Entity",
            ),
            "label_original": properties.pop("labelOriginal", ""),
            "label_en": properties.pop("labelEnglish", ""),
            "jurisdiction": properties.pop("jurisdiction", ""),
            "source_record_id": properties.pop("sourceRecordId", ""),
            "source_url": properties.pop("sourceUrl", ""),
            "properties": properties,
        }

    @staticmethod
    def _relationship_to_dict(relationship: Any) -> dict[str, Any]:
        properties = dict(relationship)
        return {
            "id": properties.pop("relationshipId", relationship.element_id),
            "start_id": relationship.start_node.get("nodeId", ""),
            "predicate": relationship.type,
            "end_id": relationship.end_node.get("nodeId", ""),
            "jurisdiction": properties.pop("jurisdiction", ""),
            "source_record_id": properties.pop("sourceRecordId", ""),
            "source_url": properties.pop("sourceUrl", ""),
            "properties": properties,
        }
