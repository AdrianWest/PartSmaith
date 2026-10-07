CREATE TABLE node_cache (
    node_kind TEXT NOT NULL,
    dependency_hash TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (node_kind, dependency_hash)
);

CREATE TABLE reproducibility_reports (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL REFERENCES builds(id),
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL')),
    sha256 TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL
);
