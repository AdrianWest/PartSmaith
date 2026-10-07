-- Integration objects and operational attempts are separate from BuildState.
CREATE TABLE integration_objects (
    sha256 TEXT PRIMARY KEY NOT NULL CHECK (length(sha256) = 64),
    kind TEXT NOT NULL,
    content BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE integration_object_refs (
    owner_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    child_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    PRIMARY KEY (owner_hash, child_hash)
);

CREATE TABLE integration_targets (
    project_id TEXT PRIMARY KEY NOT NULL,
    library_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope = 'project-local'),
    root TEXT NOT NULL UNIQUE,
    ownership_bytes BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE integration_heads (
    project_id TEXT PRIMARY KEY REFERENCES integration_targets(project_id),
    manifest_hash TEXT REFERENCES integration_objects(sha256)
);

CREATE TABLE integration_attempts (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL,
    plan_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    snapshot_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    created_at TEXT NOT NULL
);

CREATE TABLE integration_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT NOT NULL REFERENCES integration_attempts(id),
    state TEXT NOT NULL CHECK (state IN (
        'PLANNED', 'STAGED', 'AUTHORIZED', 'REJECTED', 'CANCELLED',
        'PREPARED', 'COMMITTED', 'FAILED', 'RECOVERY_REQUIRED', 'ROLLED_BACK'
    )),
    object_hash TEXT REFERENCES integration_objects(sha256),
    created_at TEXT NOT NULL
);

CREATE TABLE integration_decisions (
    attempt_id TEXT PRIMARY KEY REFERENCES integration_attempts(id),
    audit_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    authorization_hash TEXT REFERENCES integration_objects(sha256),
    created_at TEXT NOT NULL
);

CREATE TABLE integration_publications (
    attempt_id TEXT PRIMARY KEY REFERENCES integration_attempts(id),
    journal_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    manifest_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    receipt_hash TEXT NOT NULL REFERENCES integration_objects(sha256),
    created_at TEXT NOT NULL
);

CREATE TRIGGER integration_objects_no_update
BEFORE UPDATE ON integration_objects BEGIN
    SELECT RAISE(ABORT, 'Immutable integration object');
END;
CREATE TRIGGER integration_objects_no_delete
BEFORE DELETE ON integration_objects BEGIN
    SELECT RAISE(ABORT, 'Immutable integration object');
END;
CREATE TRIGGER integration_refs_no_update
BEFORE UPDATE ON integration_object_refs BEGIN
    SELECT RAISE(ABORT, 'Immutable integration reference');
END;
CREATE TRIGGER integration_refs_no_delete
BEFORE DELETE ON integration_object_refs BEGIN
    SELECT RAISE(ABORT, 'Immutable integration reference');
END;
CREATE TRIGGER integration_targets_no_update
BEFORE UPDATE ON integration_targets BEGIN
    SELECT RAISE(ABORT, 'Immutable integration target');
END;
CREATE TRIGGER integration_targets_no_delete
BEFORE DELETE ON integration_targets BEGIN
    SELECT RAISE(ABORT, 'Immutable integration target');
END;
CREATE TRIGGER integration_attempts_no_update
BEFORE UPDATE ON integration_attempts BEGIN
    SELECT RAISE(ABORT, 'Immutable integration attempt');
END;
CREATE TRIGGER integration_attempts_no_delete
BEFORE DELETE ON integration_attempts BEGIN
    SELECT RAISE(ABORT, 'Immutable integration attempt');
END;
CREATE TRIGGER integration_events_no_update
BEFORE UPDATE ON integration_events BEGIN
    SELECT RAISE(ABORT, 'Append-only integration event');
END;
CREATE TRIGGER integration_events_no_delete
BEFORE DELETE ON integration_events BEGIN
    SELECT RAISE(ABORT, 'Append-only integration event');
END;
CREATE TRIGGER integration_decisions_no_update
BEFORE UPDATE ON integration_decisions BEGIN
    SELECT RAISE(ABORT, 'Immutable integration decision');
END;
CREATE TRIGGER integration_decisions_no_delete
BEFORE DELETE ON integration_decisions BEGIN
    SELECT RAISE(ABORT, 'Immutable integration decision');
END;
CREATE TRIGGER integration_publications_no_update
BEFORE UPDATE ON integration_publications BEGIN
    SELECT RAISE(ABORT, 'Immutable integration publication');
END;
CREATE TRIGGER integration_publications_no_delete
BEFORE DELETE ON integration_publications BEGIN
    SELECT RAISE(ABORT, 'Immutable integration publication');
END;
