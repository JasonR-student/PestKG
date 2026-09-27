"""Build an independent reference pack without modifying an A-Line release."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pyarrow as pa
import pyarrow.parquet as pq
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NODE_SCHEMA = pa.schema([(name, pa.string()) for name in (
    'id', 'type', 'label_original', 'label_en', 'jurisdiction', 'source_record_id',
    'source_url', 'properties_json', 'graph_scope', 'source_id', 'source_snapshot_id',
)])
EDGE_SCHEMA = pa.schema([(name, pa.string()) for name in (
    'id', 'start_id', 'predicate', 'end_id', 'jurisdiction', 'source_record_id',
    'source_url', 'properties_json', 'graph_scope',
)])
BASE_RELEASE = 'PestKG_A_Data_Release_v1.0'
AGROVOC = 'http://aims.fao.org/aos/agrovoc/'
API = 'https://agrovoc.fao.org/browse/rest/v1/agrovoc/'
SEEDS = ('cucum*', 'pear*', 'rice*', 'wheat*', 'tomato*', 'grape*',
         'aphid*', 'fungicid*', 'pesticid*', 'glyphosat*', 'botrytis*')


def opaque_id(source: str, value: str) -> str:
    return 'REF_' + uuid.uuid5(uuid.NAMESPACE_URL, f'PestKG-reference:{source}:{value}').hex


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


class PackWriter:
    def __init__(self, output: Path):
        self.nodes = pq.ParquetWriter(output / 'nodes.parquet', NODE_SCHEMA, compression='zstd')
        self.edges = pq.ParquetWriter(output / 'edges.parquet', EDGE_SCHEMA, compression='zstd')
        self.node_batch = []
        self.edge_batch = []
        self.node_ids = set()
        self.edge_ids = set()
        self.node_counts = Counter()
        self.edge_counts = Counter()
        self.types = {}
        self.predicates = {}

    def node(self, source, key, kind, original, english, url, properties):
        node_id = opaque_id(source, key)
        if node_id in self.node_ids:
            return node_id
        self.node_ids.add(node_id)
        scope = 'reference:' + source
        self.node_batch.append(dict(zip(NODE_SCHEMA.names, (
            node_id, kind, original, english, '', key, url,
            json.dumps(properties, ensure_ascii=False, sort_keys=True), scope,
            source, properties.get('reference_snapshot', ''),
        ))))
        self.node_counts[source] += 1
        self.types.setdefault(source, Counter())[kind] += 1
        if len(self.node_batch) >= 20000:
            self.flush_nodes()
        return node_id

    def edge(self, source, start, predicate, end, evidence, properties=None):
        edge_id = opaque_id(source, '\0'.join((start, predicate, end)))
        if edge_id in self.edge_ids:
            return
        self.edge_ids.add(edge_id)
        props = {'assertion_status': 'REFERENCE_SOURCE_ASSERTION',
                 'origin_kind': 'INDEPENDENT_REFERENCE', 'identity_review': 'NOT_A_LOCAL_IDENTITY_LINK'}
        props.update(properties or {})
        self.edge_batch.append(dict(zip(EDGE_SCHEMA.names, (
            edge_id, start, predicate, end, '', evidence, '',
            json.dumps(props, ensure_ascii=False, sort_keys=True), 'reference:' + source,
        ))))
        self.edge_counts[source] += 1
        self.predicates.setdefault(source, Counter())[predicate] += 1
        if len(self.edge_batch) >= 20000:
            self.flush_edges()

    def flush_nodes(self):
        if self.node_batch:
            self.nodes.write_table(pa.Table.from_pylist(self.node_batch, schema=NODE_SCHEMA))
            self.node_batch.clear()

    def flush_edges(self):
        if self.edge_batch:
            self.edges.write_table(pa.Table.from_pylist(self.edge_batch, schema=EDGE_SCHEMA))
            self.edge_batch.clear()

    def close(self):
        self.flush_nodes()
        self.flush_edges()
        self.nodes.close()
        self.edges.close()


def import_chebi(writer, path):
    import pronto
    ontology = pronto.Ontology(path, import_depth=0, threads=1, encoding='utf-8')
    sha = digest(path)
    version = ontology.metadata.data_version or 'unknown'
    terms = {term.id: term for term in ontology.terms() if not term.obsolete}
    for term in terms.values():
        writer.node('CHEBI', term.id, 'ChEBITerm', term.name or term.id, term.name or term.id,
                    'https://www.ebi.ac.uk/chebi/searchId.do?' + urlencode({'chebiId': term.id}),
                    {'external_id': term.id, 'definition': str(term.definition or ''),
                     'reference_snapshot': version, 'source_sha256': sha,
                     'identity_review': 'NOT_ALIGNED_TO_REGULATORY_RECORDS'})
    for term in terms.values():
        for parent in term.superclasses(distance=1, with_self=False):
            if parent.id in terms:
                writer.edge('CHEBI', opaque_id('CHEBI', term.id), 'CHEBI_IS_A',
                            opaque_id('CHEBI', parent.id), sha)
        for relation, targets in term.relationships.items():
            for target in targets:
                if target.id in terms:
                    writer.edge('CHEBI', opaque_id('CHEBI', term.id), relation.id,
                                opaque_id('CHEBI', target.id), sha, {'relation_name': relation.name or relation.id})
    return {'id': 'reference:CHEBI', 'name': 'ChEBI', 'kind': 'reference',
            'snapshot_id': version, 'coverage_status': 'LOCAL_OFFICIAL_ONTOLOGY_FILE',
            'source_sha256': sha, 'inputs': [{'file': path.name, 'sha256': sha}],
            'rights_status': 'SOURCE_HEADER_CC_BY_4_0; INTERNAL_DISPLAY'}


def import_legacy(writer, root, source):
    node_path, edge_path = root / source / 'nodes.csv', root / source / 'edges.csv'
    hashes = {'nodes.csv': digest(node_path), 'edges.csv': digest(edge_path)}
    snapshot = 'legacy-reference-' + hashes['nodes.csv'][:12]
    existing = set()
    with node_path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            props = json.loads(row['properties_json'] or '{}')
            props['external_ids'] = json.loads(row['external_ids_json'] or '{}')
            props['reference_snapshot'] = snapshot
            props['import_status'] = 'LEGACY_DERIVED_REFERENCE_NOT_A_LINE'
            props['source_sha256'] = hashes['nodes.csv']
            props['external_id'] = row['id']
            original = props.get('chinese_name') or row['preferred_label']
            english = props.get('english_name') or row['preferred_label']
            writer.node(source, row['id'], row['entity_type'], original, english,
                        props.get('source_url') or '', props)
            existing.add(row['id'])
    skipped = 0
    with edge_path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['relation_type'] in ('exactMatch', 'closeMatch', 'sameAs'):
                skipped += 1
                continue
            if row['start_id'] not in existing or row['end_id'] not in existing:
                raise ValueError(f'{source}: missing reference edge endpoint')
            writer.edge(source, opaque_id(source, row['start_id']), row['relation_type'],
                        opaque_id(source, row['end_id']), row['evidence_id'],
                        {'import_status': 'LEGACY_DERIVED_REFERENCE_NOT_A_LINE', 'source_sha256': hashes['edges.csv']})
    return {'id': 'reference:' + source, 'name': source, 'kind': 'reference',
            'snapshot_id': snapshot, 'coverage_status': 'LEGACY_DERIVED_REFERENCE_UNREVIEWED',
            'source_sha256': hashes['nodes.csv'], 'excluded_identity_edges': skipped,
            'rights_status': 'INTERNAL_ONLY; SOURCE_RIGHTS_REVIEW_REQUIRED',
            'inputs': [{'file': source + '/' + name, 'sha256': sha} for name, sha in hashes.items()]}


def as_list(value):
    return value if isinstance(value, list) else [value] if value is not None else []


def import_agrovoc(writer, cache, proxy):
    cache.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
    if proxy:
        session.proxies.update({'http': proxy, 'https': proxy})
    inputs, concepts, relations = [], {}, set()
    def fetch(endpoint, params):
        url = API + endpoint + '?' + urlencode(params)
        path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
        if not path.exists():
            response = session.get(url, timeout=45)
            response.raise_for_status()
            value = response.json()
            path.write_text(json.dumps({'url': url, 'captured_at': datetime.now(timezone.utc).isoformat(),
                                        'response': value}, ensure_ascii=False), encoding='utf-8')
        saved = json.loads(path.read_text(encoding='utf-8'))
        inputs.append({'request_url': url, 'sha256': digest(path), 'captured_at': saved['captured_at']})
        return saved['response']
    uris = set()
    for query in SEEDS:
        response = fetch('search', {'query': query, 'lang': 'en', 'maxhits': 10})
        uris.update(row['uri'] for row in response.get('results', [])[:10]
                    if re.fullmatch(re.escape(AGROVOC) + r'c_[0-9a-f]+', row.get('uri', '')))
    if not uris:
        raise ValueError('AGROVOC official API returned no concepts')
    for uri in sorted(uris):
        print('AGROVOC_FETCH', uri, flush=True)
        response = fetch('data', {'uri': uri, 'format': 'application/ld+json'})
        for record in response.get('graph', []):
            if 'skos:Concept' not in as_list(record.get('type')):
                continue
            subject = record['uri']
            labels = {label.get('lang', 'und'): label.get('value', '') for label in as_list(record.get('prefLabel'))}
            concepts[subject] = {'labels': labels, 'source_modified': record.get('dct:modified'), 'fetched': True}
            for predicate in ('broader', 'narrower', 'related'):
                for target in as_list(record.get(predicate)):
                    target_uri = target.get('uri', '')
                    if target_uri.startswith(AGROVOC + 'c_'):
                        relations.add((subject, 'SKOS_' + predicate.upper(), target_uri))
                        concepts.setdefault(target_uri, {'labels': {}, 'fetched': False})
    for uri, record in concepts.items():
        labels = record['labels']
        writer.node('AGROVOC', uri, 'AGROVOCConcept', labels.get('zh') or labels.get('en') or uri,
                    labels.get('en') or labels.get('zh') or uri, uri,
                    {'external_id': uri, 'labels': labels, 'source_modified': record.get('source_modified'),
                     'reference_snapshot': 'official-api-2026-09-27',
                     'coverage_status': 'FETCHED_CONCEPT' if record['fetched'] else 'REFERENCE_URI_STUB',
                     'identity_review': 'NOT_ALIGNED_TO_REGULATORY_RECORDS'})
    for start, predicate, end in sorted(relations):
        writer.edge('AGROVOC', opaque_id('AGROVOC', start), predicate, opaque_id('AGROVOC', end), start)
    return {'id': 'reference:AGROVOC', 'name': 'AGROVOC', 'kind': 'reference',
            'snapshot_id': 'official-api-2026-09-27', 'coverage_status': 'BOUNDED_OFFICIAL_API_SUBGRAPH',
            'rights_status': 'INTERNAL_DISPLAY; PUBLIC_DISTRIBUTION_UNREVIEWED',
            'source_sha256': hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
            'queries': list(SEEDS), 'max_search_results_per_query': 10, 'inputs': inputs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chebi-obo', type=Path, required=True)
    parser.add_argument('--legacy-root', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--proxy')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    writer = PackWriter(args.out)
    sources = []
    try:
        sources.append(import_agrovoc(writer, args.cache, args.proxy))
        print('AGROVOC imported', writer.node_counts['AGROVOC'], flush=True)
        sources.append(import_chebi(writer, args.chebi_obo))
        print('CHEBI imported', writer.node_counts['CHEBI'], flush=True)
        for source in ('BCPC', 'EPPO', 'FRAC', 'HRAC', 'IRAC'):
            sources.append(import_legacy(writer, args.legacy_root, source))
            print(source, 'imported', writer.node_counts[source], flush=True)
    finally:
        writer.close()
    for source in sources:
        key = source['id'].split(':', 1)[1]
        source.update(nodes=writer.node_counts[key], edges=writer.edge_counts[key],
                      node_types=dict(writer.types.get(key, {})), relation_types=dict(writer.predicates.get(key, {})))
    manifest = {'pack_id': args.out.name, 'base_release_id': BASE_RELEASE,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'INTERNAL_REFERENCE_PACK', 'exact_regulatory_identity_links': 0,
                'sources': sources, 'artifacts': {name: {'sha256': digest(args.out / name)}
                                                 for name in ('nodes.parquet', 'edges.parquet')}}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('REFERENCE_PACK_COMPLETE', sum(writer.node_counts.values()), sum(writer.edge_counts.values()))


if __name__ == '__main__':
    main()
