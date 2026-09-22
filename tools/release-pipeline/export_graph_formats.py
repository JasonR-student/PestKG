from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote
from xml.etree import ElementTree as ET

import duckdb


BASE = "https://pestkg.org/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
VOCAB = f"{BASE}vocab/"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_properties(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def resource_iri(identifier: str) -> str:
    return f"{BASE}resource/{quote(identifier, safe='')}"


def relationship_iri(identifier: str) -> str:
    return f"{BASE}relationship/{quote(identifier, safe='')}"


def vocab_iri(term: str) -> str:
    return f"{VOCAB}{quote(term, safe='')}"


def iri(value: str) -> str:
    return f"<{value}>"


def literal(value: Any, language: str | None = None, datatype: str | None = None) -> str:
    encoded = json.dumps(str(value), ensure_ascii=False)
    if language:
        return f"{encoded}@{language}"
    if datatype:
        return f"{encoded}^^<{datatype}>"
    return encoded


def triple(subject: str, predicate: str, obj: str) -> str:
    return f"{iri(subject)} {iri(predicate)} {obj} .\n"


def export_sample_formats(sample_dir: Path, output_dir: Path) -> list[Path]:
    nodes = read_csv(sample_dir / "nodes.csv")
    edges = read_csv(sample_dir / "edges.csv")
    output_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "@vocab": VOCAB,
        "id": "@id",
        "type": "@type",
        "label_original": "labelOriginal",
        "label_en": {"@id": "labelEnglish", "@language": "en"},
        "jurisdiction": "jurisdiction",
        "source_record_id": "sourceRecordId",
        "source_url": "sourceUrl",
        "properties": "properties",
        "start_id": {"@id": "subject", "@type": "@id"},
        "end_id": {"@id": "object", "@type": "@id"},
        "predicate": "predicate",
    }
    graph: list[dict[str, Any]] = []
    for node in nodes:
        graph.append(
            {
                "id": resource_iri(node["id"]),
                "type": vocab_iri(node["type"]),
                "node_id": node["id"],
                "label_original": node["label_original"],
                "label_en": node["label_en"],
                "jurisdiction": node["jurisdiction"],
                "source_record_id": node["source_record_id"],
                "source_url": node["source_url"],
                "properties": parse_properties(node["properties_json"]),
            }
        )
    for edge in edges:
        graph.append(
            {
                "id": relationship_iri(edge["id"]),
                "type": vocab_iri("Relationship"),
                "relationship_id": edge["id"],
                "start_id": resource_iri(edge["start_id"]),
                "end_id": resource_iri(edge["end_id"]),
                "predicate": edge["predicate"],
                "jurisdiction": edge["jurisdiction"],
                "source_record_id": edge["source_record_id"],
                "source_url": edge["source_url"],
                "properties": parse_properties(edge["properties_json"]),
            }
        )
    jsonld_path = output_dir / "pestkg-sample.jsonld"
    with jsonld_path.open("w", encoding="utf-8") as handle:
        json.dump({"@context": context, "@graph": graph}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    ET.register_namespace("", "http://graphml.graphdrawing.org/xmlns")
    root = ET.Element("{http://graphml.graphdrawing.org/xmlns}graphml")
    node_fields = [
        "type",
        "label_original",
        "label_en",
        "jurisdiction",
        "source_record_id",
        "source_url",
        "properties_json",
    ]
    edge_fields = [
        "predicate",
        "jurisdiction",
        "source_record_id",
        "source_url",
        "properties_json",
    ]
    for scope, fields in (("node", node_fields), ("edge", edge_fields)):
        for field in fields:
            ET.SubElement(
                root,
                "{http://graphml.graphdrawing.org/xmlns}key",
                {"id": f"{scope}_{field}", "for": scope, "attr.name": field, "attr.type": "string"},
            )
    graph_element = ET.SubElement(
        root,
        "{http://graphml.graphdrawing.org/xmlns}graph",
        {"id": "PestKGSample", "edgedefault": "directed"},
    )
    for node in nodes:
        element = ET.SubElement(
            graph_element,
            "{http://graphml.graphdrawing.org/xmlns}node",
            {"id": node["id"]},
        )
        for field in node_fields:
            data = ET.SubElement(
                element,
                "{http://graphml.graphdrawing.org/xmlns}data",
                {"key": f"node_{field}"},
            )
            data.text = node[field]
    for edge in edges:
        element = ET.SubElement(
            graph_element,
            "{http://graphml.graphdrawing.org/xmlns}edge",
            {"id": edge["id"], "source": edge["start_id"], "target": edge["end_id"]},
        )
        for field in edge_fields:
            data = ET.SubElement(
                element,
                "{http://graphml.graphdrawing.org/xmlns}data",
                {"key": f"edge_{field}"},
            )
            data.text = edge[field]
    graphml_path = output_dir / "pestkg-sample.graphml"
    ET.ElementTree(root).write(graphml_path, encoding="utf-8", xml_declaration=True)
    return [jsonld_path, graphml_path]


def parquet_expression(path: Path) -> str:
    source = path / "**/*.parquet" if path.is_dir() else path
    escaped = str(source.resolve()).replace("\\", "/").replace("'", "''")
    return f"read_parquet('{escaped}', hive_partitioning=true)"


def rows(cursor: duckdb.DuckDBPyConnection, batch_size: int = 10_000) -> Iterable[tuple[Any, ...]]:
    while batch := cursor.fetchmany(batch_size):
        yield from batch


def export_ntriples(release_dir: Path, output_path: Path) -> Path:
    analytics = release_dir / "analytics"
    nodes_path = analytics / "nodes"
    edges_path = analytics / "edges"
    if not nodes_path.exists():
        nodes_path = analytics / "nodes.parquet"
        edges_path = analytics / "edges.parquet"
    if not nodes_path.exists() or not edges_path.exists():
        raise FileNotFoundError("Materialized node and edge Parquet data is required")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    with gzip.open(output_path, "wt", encoding="utf-8", newline="\n") as output:
        node_cursor = connection.execute(
            "SELECT id, type, label_original, label_en, jurisdiction, "
            "source_record_id, source_url, properties_json "
            f"FROM {parquet_expression(nodes_path)}"
        )
        for node_id, node_type, original, english, jurisdiction, source_id, source_url, properties in rows(node_cursor):
            subject = resource_iri(node_id)
            output.write(triple(subject, f"{RDF}type", iri(vocab_iri(node_type))))
            if original:
                output.write(triple(subject, f"{RDFS}label", literal(original)))
            if english and english != original:
                output.write(triple(subject, f"{VOCAB}labelEnglish", literal(english, language="en")))
            output.write(triple(subject, f"{VOCAB}jurisdiction", literal(jurisdiction)))
            output.write(triple(subject, f"{VOCAB}sourceRecordId", literal(source_id)))
            output.write(triple(subject, f"{VOCAB}sourceUrl", literal(source_url)))
            output.write(triple(subject, f"{VOCAB}propertiesJson", literal(properties, datatype=f"{RDF}JSON")))

        edge_cursor = connection.execute(
            "SELECT id, start_id, predicate, end_id, jurisdiction, "
            "source_record_id, source_url, properties_json "
            f"FROM {parquet_expression(edges_path)}"
        )
        for edge_id, start_id, predicate, end_id, jurisdiction, source_id, source_url, properties in rows(edge_cursor):
            statement = relationship_iri(edge_id)
            predicate_iri = vocab_iri(predicate)
            output.write(triple(resource_iri(start_id), predicate_iri, iri(resource_iri(end_id))))
            output.write(triple(statement, f"{RDF}type", iri(f"{RDF}Statement")))
            output.write(triple(statement, f"{RDF}subject", iri(resource_iri(start_id))))
            output.write(triple(statement, f"{RDF}predicate", iri(predicate_iri)))
            output.write(triple(statement, f"{RDF}object", iri(resource_iri(end_id))))
            output.write(triple(statement, f"{VOCAB}relationshipId", literal(edge_id)))
            output.write(triple(statement, f"{VOCAB}jurisdiction", literal(jurisdiction)))
            output.write(triple(statement, f"{VOCAB}sourceRecordId", literal(source_id)))
            output.write(triple(statement, f"{VOCAB}sourceUrl", literal(source_url)))
            output.write(triple(statement, f"{VOCAB}propertiesJson", literal(properties, datatype=f"{RDF}JSON")))
    connection.close()
    return output_path


def sha256_sidecar(path: Path) -> Path:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(f"{digest.hexdigest()}  {path.name}\n", encoding="ascii")
    return sidecar


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("--full-ntriples", action="store_true")
    args = parser.parse_args()
    sample_outputs = export_sample_formats(
        args.release_dir / "sample", args.release_dir / "sample/formats"
    )
    for path in sample_outputs:
        print(f"Exported sample: {path}")
    if args.full_ntriples:
        release_id = args.release_dir.name
        output = export_ntriples(
            args.release_dir, args.release_dir / "08_rdf" / f"pestkg-{release_id}.nt.gz"
        )
        sha256_sidecar(output)
        print(f"Exported full RDF: {output}")


if __name__ == "__main__":
    main()
