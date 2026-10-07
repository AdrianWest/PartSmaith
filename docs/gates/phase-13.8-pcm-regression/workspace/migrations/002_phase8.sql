CREATE TABLE acquisition_inventories (
    sha256 TEXT PRIMARY KEY NOT NULL
        CHECK (length(sha256) = 64 AND sha256 = lower(sha256)),
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);

CREATE TABLE ir_revisions (
    id TEXT PRIMARY KEY NOT NULL,
    component_id TEXT NOT NULL
        REFERENCES components(id) ON DELETE RESTRICT,
    parent_id TEXT REFERENCES ir_revisions(id) ON DELETE RESTRICT,
    canonical_sha256 TEXT NOT NULL
        CHECK (
            length(canonical_sha256) = 64
            AND canonical_sha256 = lower(canonical_sha256)
        ),
    canonical_bytes BLOB NOT NULL,
    inventory_sha256 TEXT
        REFERENCES acquisition_inventories(sha256) ON DELETE RESTRICT,
    reviewed INTEGER NOT NULL CHECK (reviewed IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at),
    UNIQUE (component_id, canonical_sha256)
);
CREATE INDEX ir_revisions_component_id
    ON ir_revisions(component_id);
CREATE INDEX ir_revisions_parent_id
    ON ir_revisions(parent_id);

CREATE TABLE component_heads (
    component_id TEXT PRIMARY KEY NOT NULL
        REFERENCES components(id) ON DELETE RESTRICT,
    revision_id TEXT NOT NULL
        REFERENCES ir_revisions(id) ON DELETE RESTRICT,
    revision_hash TEXT NOT NULL
        CHECK (
            length(revision_hash) = 64
            AND revision_hash = lower(revision_hash)
        ),
    updated_at TEXT NOT NULL
);

CREATE TABLE review_proposals (
    id TEXT PRIMARY KEY NOT NULL,
    component_id TEXT NOT NULL
        REFERENCES components(id) ON DELETE RESTRICT,
    base_revision_id TEXT NOT NULL
        REFERENCES ir_revisions(id) ON DELETE RESTRICT,
    base_revision_hash TEXT NOT NULL,
    candidate_revision_id TEXT NOT NULL
        REFERENCES ir_revisions(id) ON DELETE RESTRICT,
    candidate_revision_hash TEXT NOT NULL,
    expected_head_hash TEXT NOT NULL,
    canonical_sha256 TEXT NOT NULL UNIQUE,
    canonical_bytes BLOB NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);
CREATE INDEX review_proposals_component_id
    ON review_proposals(component_id);

CREATE TABLE review_events (
    id TEXT PRIMARY KEY NOT NULL,
    proposal_id TEXT REFERENCES review_proposals(id) ON DELETE RESTRICT,
    build_id TEXT REFERENCES builds(id) ON DELETE RESTRICT,
    stage TEXT NOT NULL CHECK (stage IN ('INPUT', 'RELEASE')),
    decision TEXT NOT NULL
        CHECK (decision IN ('APPROVE', 'REJECT', 'ACCEPT_WARNING')),
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    canonical_sha256 TEXT NOT NULL UNIQUE,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at),
    CHECK (
        (stage = 'INPUT' AND proposal_id IS NOT NULL)
        OR (stage = 'RELEASE' AND build_id IS NOT NULL)
    )
);

CREATE TABLE build_state_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id TEXT NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    from_state TEXT,
    to_state TEXT NOT NULL CHECK (
        to_state IN (
            'SOURCE_RECEIVED',
            'SOURCE_ANALYZED',
            'EVIDENCE_COLLECTED',
            'IR_BUILT',
            'PACKAGE_IDENTIFIED',
            'IR_VALIDATED',
            'SYMBOL_GENERATED',
            'FOOTPRINT_GENERATED',
            '3D_GENERATED',
            'ARTIFACT_VALIDATION',
            'CROSS_VALIDATION',
            'HUMAN_REVIEW_REQUIRED',
            'APPROVED',
            'EXPORTED',
            'REJECTED',
            'EXTRACTION_FAILED',
            'EVIDENCE_CONFLICT',
            'IR_INVALID',
            'PACKAGE_UNSUPPORTED',
            'NOT_GENERATABLE',
            'ARTIFACT_VALIDATION_FAILED',
            'CROSS_VALIDATION_FAILED'
        )
    ),
    review_stage TEXT CHECK (
        review_stage IS NULL OR review_stage IN ('INPUT', 'RELEASE')
    ),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX build_state_transitions_build_id
    ON build_state_transitions(build_id, id);

CREATE TABLE build_snapshots (
    build_id TEXT PRIMARY KEY NOT NULL
        REFERENCES builds(id) ON DELETE RESTRICT,
    input_snapshot_hash TEXT NOT NULL UNIQUE,
    ir_record_hash TEXT NOT NULL,
    pdl_id TEXT NOT NULL,
    pdl_revision TEXT NOT NULL,
    pdl_hash TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);

CREATE TABLE build_dependencies (
    build_id TEXT NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    node_kind TEXT NOT NULL,
    dependency_hash TEXT NOT NULL,
    action TEXT NOT NULL CHECK (
        action IN ('GENERATE', 'REGENERATE', 'REVALIDATE', 'REUSE')
    ),
    declaration_id TEXT NOT NULL,
    declaration_version TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at),
    PRIMARY KEY (build_id, node_kind)
);

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY NOT NULL,
    build_id TEXT NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN ('SYMBOL', 'FOOTPRINT', 'MODEL_3D')),
    stage TEXT NOT NULL CHECK (stage IN ('PRELIMINARY', 'FINAL')),
    logical_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    dependency_hash TEXT NOT NULL,
    generator TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    content BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at),
    UNIQUE (build_id, artifact_type, stage)
);

CREATE TABLE validation_results (
    id TEXT PRIMARY KEY NOT NULL,
    build_id TEXT NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    stage TEXT NOT NULL CHECK (
        stage IN (
            'INPUT',
            'ARTIFACT',
            'FINAL_ARTIFACT',
            'POST_MANIFEST',
            'REPRODUCIBILITY'
        )
    ),
    rule_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    canonical_sha256 TEXT NOT NULL UNIQUE,
    canonical_bytes BLOB NOT NULL,
    superseded INTEGER NOT NULL CHECK (superseded IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);
CREATE INDEX validation_results_build_stage
    ON validation_results(build_id, stage);

CREATE TABLE engineering_manifests (
    build_id TEXT PRIMARY KEY NOT NULL
        REFERENCES builds(id) ON DELETE RESTRICT,
    sha256 TEXT NOT NULL UNIQUE,
    validation_semantics_hash TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);

CREATE TABLE post_manifest_reports (
    id TEXT PRIMARY KEY NOT NULL,
    build_id TEXT NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    manifest_hash TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);

CREATE TABLE release_decisions (
    id TEXT PRIMARY KEY NOT NULL,
    build_id TEXT NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (decision IN ('APPROVE', 'REJECT')),
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);

CREATE TABLE approval_bindings (
    build_id TEXT PRIMARY KEY NOT NULL
        REFERENCES builds(id) ON DELETE RESTRICT,
    release_decision_id TEXT NOT NULL UNIQUE
        REFERENCES release_decisions(id) ON DELETE RESTRICT,
    input_snapshot_hash TEXT NOT NULL,
    engineering_manifest_hash TEXT NOT NULL,
    validation_semantics_hash TEXT NOT NULL,
    canonical_sha256 TEXT NOT NULL UNIQUE,
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at)
);

CREATE TABLE bundle_objects (
    bundle_id TEXT NOT NULL,
    object_identity TEXT NOT NULL,
    object_kind TEXT NOT NULL,
    schema_version TEXT,
    relative_path TEXT,
    retrieval_locator TEXT,
    byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
    sha256 TEXT NOT NULL,
    content BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at = created_at),
    PRIMARY KEY (bundle_id, object_identity),
    CHECK (
        (relative_path IS NOT NULL AND retrieval_locator IS NULL)
        OR (relative_path IS NULL AND retrieval_locator IS NOT NULL)
    )
);

CREATE TABLE bundle_imports (
    id TEXT PRIMARY KEY NOT NULL,
    bundle_id TEXT NOT NULL,
    index_sha256 TEXT NOT NULL,
    availability TEXT NOT NULL CHECK (
        availability IN ('OFFLINE_COMPLETE', 'RETRIEVAL_REQUIRED')
    ),
    status TEXT NOT NULL CHECK (status IN ('STAGED', 'IMPORTED', 'FAILED')),
    canonical_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
