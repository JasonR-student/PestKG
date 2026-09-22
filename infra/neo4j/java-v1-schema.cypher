// Java v1 release projection. The temporal source of truth remains PostgreSQL/Parquet.
CREATE CONSTRAINT pestkg_entity_key IF NOT EXISTS
FOR (n:Entity) REQUIRE n.entityKey IS UNIQUE;

CREATE CONSTRAINT pestkg_release_key IF NOT EXISTS
FOR (r:Release) REQUIRE r.releaseId IS UNIQUE;

CREATE INDEX pestkg_entity_id IF NOT EXISTS
FOR (n:Entity) ON (n.nodeId);

CREATE INDEX pestkg_entity_release IF NOT EXISTS
FOR (n:Entity) ON (n.releaseId);

CREATE INDEX pestkg_entity_jurisdiction IF NOT EXISTS
FOR (n:Entity) ON (n.jurisdiction);

CREATE INDEX pestkg_entity_label_en IF NOT EXISTS
FOR (n:Entity) ON (n.labelEnglish);

CREATE INDEX pestkg_entity_label_original IF NOT EXISTS
FOR (n:Entity) ON (n.labelOriginal);

CREATE FULLTEXT INDEX pestkg_entity_name_search IF NOT EXISTS
FOR (n:Entity) ON EACH [n.labelOriginal, n.labelEnglish];

// Import contract for every release projection:
// entityKey = releaseId + '|' + nodeId
// relationship properties include releaseId, validFrom, validTo, txFrom, txTo,
// sourceSnapshotId, sourceRecordId, assertionId, evidenceId, method, confidence.
