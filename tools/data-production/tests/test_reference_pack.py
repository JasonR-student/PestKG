"""Validate the delivered independent reference pack without network access."""
import hashlib
import json
from pathlib import Path
import unittest

import duckdb


ROOT = Path(__file__).resolve().parents[3]


class ReferencePackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ROOT / 'data/reference-graphs'
        cls.index = json.loads((root / 'index.json').read_text(encoding='utf-8'))
        cls.pack = root / cls.index['pack_path']
        cls.manifest = json.loads((cls.pack / 'manifest.json').read_text(encoding='utf-8'))
        cls.con = duckdb.connect()
        for name in ('nodes', 'edges'):
            path = (cls.pack / f'{name}.parquet').as_posix().replace("'", "''")
            cls.con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_manifest_and_artifact_hashes(self):
        self.assertEqual(self.index['base_release_id'], 'PestKG_A_Data_Release_v1.0')
        self.assertEqual(self.manifest['base_release_id'], self.index['base_release_id'])
        self.assertEqual(self.manifest['pack_id'], self.pack.name)
        self.assertEqual(self.manifest['exact_regulatory_identity_links'], 0)
        for name, artifact in self.manifest['artifacts'].items():
            with (self.pack / name).open('rb') as stream:
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    digest.update(chunk)
            self.assertEqual(digest.hexdigest(), artifact['sha256'], name)

    def test_unique_ids_valid_properties_and_isolated_endpoints(self):
        for table in ('nodes', 'edges'):
            total, distinct, invalid = self.con.execute(
                f"SELECT count(*),count(DISTINCT id),count(*) FILTER "
                f"(WHERE NOT json_valid(properties_json) OR id NOT LIKE 'REF_%') FROM {table}"
            ).fetchone()
            self.assertGreater(total, 0)
            self.assertEqual(total, distinct, table)
            self.assertEqual(invalid, 0, table)
        invalid = self.con.execute(
            'SELECT count(*) FROM edges e LEFT JOIN nodes s ON e.start_id=s.id '
            'LEFT JOIN nodes t ON e.end_id=t.id WHERE s.id IS NULL OR t.id IS NULL '
            'OR s.graph_scope<>e.graph_scope OR t.graph_scope<>e.graph_scope'
        ).fetchone()[0]
        self.assertEqual(invalid, 0)
        identity = self.con.execute(
            "SELECT count(*) FROM edges WHERE lower(predicate) IN "
            "('exact_chemical_identity','exactmatch','closematch','sameas','owl:sameas','skos:exactmatch','skos:closematch')"
        ).fetchone()[0]
        self.assertEqual(identity, 0)

    def test_per_website_counts_match_manifest(self):
        self.assertEqual(len(self.manifest['sources']), 7)
        for source in self.manifest['sources']:
            for table, kind in (('nodes', 'type'), ('edges', 'predicate')):
                counts = dict(self.con.execute(
                    f'SELECT {kind},count(*) FROM {table} WHERE graph_scope=? GROUP BY 1',
                    [source['id']],
                ).fetchall())
                self.assertEqual(sum(counts.values()), source[table], source['id'])
                self.assertEqual(counts, source['node_types' if table == 'nodes' else 'relation_types'])


if __name__ == '__main__':
    unittest.main()
