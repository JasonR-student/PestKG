from __future__ import annotations

import csv
import os
from pathlib import Path

from neo4j import GraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_ROOT = (
    PROJECT_ROOT / "data" / "releases" / "2026.08.3_federated" / "sample"
)
ALLOWED_TYPES = {
    "ActiveIngredientLocal",
    "CountryJurisdiction",
    "CropLocal",
    "FormulationLocal",
    "PesticideProduct",
    "Registration",
    "RegistrationUse",
    "RegulatoryAgency",
    "TargetLocal",
}
ALLOWED_PREDICATES = {
    "containsActiveIngredient",
    "hasActiveIngredient",
    "hasFormulation",
    "hasProduct",
    "hasRegistration",
    "hasRegistrationUse",
    "registeredForCrop",
    "registeredForTarget",
    "regulatesIn",
    "usesProduct",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def chunks(rows: list[dict[str, str]], size: int = 500) -> list[list[dict[str, str]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def main() -> None:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "pestkg-paper")
    nodes = read_csv(SAMPLE_ROOT / "nodes.csv")
    edges = read_csv(SAMPLE_ROOT / "edges.csv")
    q1_rows = read_csv(SAMPLE_ROOT / "comparisons" / "q1.csv")
    for index, row in enumerate(q1_rows, start=1):
        row["row_number"] = index

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("MATCH (n:PaperSample) DETACH DELETE n").consume()
            session.run("MATCH (n:PaperProjection) DETACH DELETE n").consume()
            for node_type in sorted(ALLOWED_TYPES):
                rows = [row for row in nodes if row["type"] == node_type]
                for batch in chunks(rows):
                    session.run(
                        f"""
                        UNWIND $rows AS row
                        CREATE (n:Entity:PaperSample:`{node_type}` {{
                          nodeId: row.id,
                          labelOriginal: row.label_original,
                          labelEnglish: row.label_en,
                          jurisdiction: row.jurisdiction,
                          sourceRecordId: row.source_record_id,
                          sourceUrl: row.source_url,
                          propertiesJson: row.properties_json
                        }})
                        """,
                        rows=batch,
                    ).consume()
            for predicate in sorted(ALLOWED_PREDICATES):
                rows = [row for row in edges if row["predicate"] == predicate]
                for batch in chunks(rows):
                    session.run(
                        f"""
                        UNWIND $rows AS row
                        MATCH (start:PaperSample {{nodeId: row.start_id}})
                        MATCH (end:PaperSample {{nodeId: row.end_id}})
                        CREATE (start)-[r:`{predicate}` {{
                          relationshipId: row.id,
                          jurisdiction: row.jurisdiction,
                          sourceRecordId: row.source_record_id,
                          sourceUrl: row.source_url,
                          propertiesJson: row.properties_json
                        }}]->(end)
                        """,
                        rows=batch,
                    ).consume()
            session.run(
                "CREATE CONSTRAINT paper_sample_id IF NOT EXISTS "
                "FOR (n:PaperSample) REQUIRE n.nodeId IS UNIQUE"
            ).consume()
            for batch in chunks(q1_rows):
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (country:PaperProjection:PaperJurisdiction {
                      nodeId: 'Q1:COUNTRY:' + row.jurisdiction
                    })
                    SET country.jurisdiction = row.jurisdiction
                    MERGE (active:PaperProjection:PaperSharedActive {
                      nodeId: row.active_shared_id
                    })
                    SET active.labelEnglish = row.active_ingredient_label_en
                    MERGE (crop:PaperProjection:PaperSharedCrop {
                      nodeId: row.crop_shared_id
                    })
                    SET crop.labelEnglish = row.crop_label_en
                    CREATE (observation:PaperProjection:PaperQ1Observation {
                      rowNumber: row.row_number,
                      cropSharedId: row.crop_shared_id,
                      cropLabelEnglish: row.crop_label_en,
                      cropCountryCount: toInteger(row.crop_country_count),
                      activeSharedId: row.active_shared_id,
                      activeIngredientLabelEnglish: row.active_ingredient_label_en,
                      activeCountryCount: toInteger(row.active_country_count),
                      jurisdiction: row.jurisdiction,
                      cropLocalLabels: row.crop_local_labels,
                      activeIngredientLocalLabels: row.active_ingredient_local_labels,
                      productCount: toInteger(row.product_count),
                      registrationUseCount: toInteger(row.registration_use_count),
                      sourceRecordCount: toInteger(row.source_record_count),
                      pairingStatus: row.pairing_status,
                      sourceFile: 'sample/comparisons/q1.csv'
                    })
                    CREATE (observation)-[:OBSERVED_IN]->(country)
                    CREATE (observation)-[:ALIGNED_ACTIVE]->(active)
                    CREATE (observation)-[:ALIGNED_CROP]->(crop)
                    """,
                    rows=batch,
                ).consume()
            session.run(
                "CREATE CONSTRAINT paper_projection_id IF NOT EXISTS "
                "FOR (n:PaperProjection) REQUIRE n.nodeId IS UNIQUE"
            ).consume()
    print(
        f"Loaded {len(nodes)} sample nodes, {len(edges)} sample relationships, "
        f"and {len(q1_rows)} Q1 projection observations into Neo4j."
    )


if __name__ == "__main__":
    main()
