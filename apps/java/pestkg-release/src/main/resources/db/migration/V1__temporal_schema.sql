CREATE TABLE IF NOT EXISTS pestkg_release (
    release_id VARCHAR(128) PRIMARY KEY,
    parent_release_id VARCHAR(128) REFERENCES pestkg_release(release_id),
    schema_version VARCHAR(64) NOT NULL,
    pipeline_version VARCHAR(128) NOT NULL,
    source_package_sha256 CHAR(64) NOT NULL,
    cutoff_at DATE,
    published_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL,
    distribution_status VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pestkg_release_artifact (
    artifact_id UUID PRIMARY KEY,
    release_id VARCHAR(128) NOT NULL REFERENCES pestkg_release(release_id),
    path TEXT NOT NULL,
    format VARCHAR(32) NOT NULL,
    media_type VARCHAR(128),
    bytes BIGINT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    UNIQUE (release_id, path)
);

CREATE TABLE IF NOT EXISTS pestkg_source_snapshot (
    snapshot_id UUID PRIMARY KEY,
    release_id VARCHAR(128) NOT NULL REFERENCES pestkg_release(release_id),
    jurisdiction VARCHAR(32) NOT NULL,
    source_url TEXT,
    source_sha256 CHAR(64),
    captured_at TIMESTAMPTZ,
    row_count BIGINT,
    time_precision VARCHAR(32) NOT NULL DEFAULT 'snapshot'
);

CREATE TABLE IF NOT EXISTS pestkg_entity_version (
    entity_id TEXT NOT NULL,
    version_no BIGINT NOT NULL,
    entity_type VARCHAR(128) NOT NULL,
    jurisdiction VARCHAR(32),
    label_original TEXT,
    label_en TEXT,
    payload JSONB NOT NULL,
    source_snapshot_id UUID REFERENCES pestkg_source_snapshot(snapshot_id),
    source_record_id TEXT,
    source_url TEXT,
    record_hash CHAR(64) NOT NULL,
    operation VARCHAR(16) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    tx_from TIMESTAMPTZ NOT NULL,
    tx_to TIMESTAMPTZ,
    time_precision VARCHAR(32) NOT NULL DEFAULT 'snapshot',
    PRIMARY KEY (entity_id, version_no),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (tx_to IS NULL OR tx_to > tx_from)
);

CREATE TABLE IF NOT EXISTS pestkg_edge_version (
    edge_id TEXT NOT NULL,
    version_no BIGINT NOT NULL,
    start_id TEXT NOT NULL,
    predicate VARCHAR(128) NOT NULL,
    end_id TEXT NOT NULL,
    jurisdiction VARCHAR(32),
    payload JSONB NOT NULL,
    source_snapshot_id UUID REFERENCES pestkg_source_snapshot(snapshot_id),
    source_record_id TEXT,
    source_url TEXT,
    assertion_id TEXT,
    evidence_id TEXT,
    method VARCHAR(128),
    confidence NUMERIC(8, 6),
    record_hash CHAR(64) NOT NULL,
    operation VARCHAR(16) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    tx_from TIMESTAMPTZ NOT NULL,
    tx_to TIMESTAMPTZ,
    time_precision VARCHAR(32) NOT NULL DEFAULT 'snapshot',
    PRIMARY KEY (edge_id, version_no),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (tx_to IS NULL OR tx_to > tx_from)
);

CREATE TABLE IF NOT EXISTS pestkg_registration_use_version (
    use_id TEXT NOT NULL,
    version_no BIGINT NOT NULL,
    jurisdiction VARCHAR(32) NOT NULL,
    product_id TEXT,
    payload JSONB NOT NULL,
    source_snapshot_id UUID REFERENCES pestkg_source_snapshot(snapshot_id),
    source_record_id TEXT,
    source_url TEXT,
    record_hash CHAR(64) NOT NULL,
    operation VARCHAR(16) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    tx_from TIMESTAMPTZ NOT NULL,
    tx_to TIMESTAMPTZ,
    time_precision VARCHAR(32) NOT NULL DEFAULT 'snapshot',
    PRIMARY KEY (use_id, version_no),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (tx_to IS NULL OR tx_to > tx_from)
);

CREATE TABLE IF NOT EXISTS pestkg_change_set (
    change_set_id UUID PRIMARY KEY,
    release_id VARCHAR(128) NOT NULL REFERENCES pestkg_release(release_id),
    parent_release_id VARCHAR(128),
    entity_added BIGINT NOT NULL DEFAULT 0,
    entity_changed BIGINT NOT NULL DEFAULT 0,
    entity_retracted BIGINT NOT NULL DEFAULT 0,
    edge_added BIGINT NOT NULL DEFAULT 0,
    edge_changed BIGINT NOT NULL DEFAULT 0,
    edge_retracted BIGINT NOT NULL DEFAULT 0,
    manifest_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pestkg_audit_event (
    event_id UUID PRIMARY KEY,
    actor_id VARCHAR(256),
    role VARCHAR(64),
    action VARCHAR(128) NOT NULL,
    release_id VARCHAR(128),
    request_id VARCHAR(128),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entity_valid_time ON pestkg_entity_version(entity_id, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_entity_transaction_time ON pestkg_entity_version(entity_id, tx_from, tx_to);
CREATE INDEX IF NOT EXISTS idx_edge_valid_time ON pestkg_edge_version(edge_id, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_edge_endpoints ON pestkg_edge_version(start_id, end_id, predicate);
CREATE INDEX IF NOT EXISTS idx_use_valid_time ON pestkg_registration_use_version(use_id, valid_from, valid_to);
