-- Identical deterministic manifests may belong to different build attempts.
-- Keep each immutable build binding and preserve all historical bytes.
CREATE TABLE build_snapshots_rebuilds (
    build_id TEXT PRIMARY KEY NOT NULL
        REFERENCES builds(id) ON DELETE RESTRICT,
    input_snapshot_hash TEXT NOT NULL,
    ir_record_hash TEXT NOT NULL,
    pdl_id TEXT NOT NULL,
    pdl_revision TEXT NOT NULL,
    pdl_hash TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);
INSERT INTO build_snapshots_rebuilds SELECT * FROM build_snapshots;
DROP TABLE build_snapshots;
ALTER TABLE build_snapshots_rebuilds RENAME TO build_snapshots;
CREATE INDEX build_snapshots_sha256 ON build_snapshots(input_snapshot_hash);

CREATE TABLE engineering_manifests_rebuilds (
    build_id TEXT PRIMARY KEY NOT NULL
        REFERENCES builds(id) ON DELETE RESTRICT,
    sha256 TEXT NOT NULL,
    validation_semantics_hash TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);
INSERT INTO engineering_manifests_rebuilds
    SELECT * FROM engineering_manifests;
DROP TABLE engineering_manifests;
ALTER TABLE engineering_manifests_rebuilds RENAME TO engineering_manifests;
CREATE INDEX engineering_manifests_sha256 ON engineering_manifests(sha256);
