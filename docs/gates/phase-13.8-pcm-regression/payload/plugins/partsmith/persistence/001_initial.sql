CREATE TABLE projects (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE components (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT REFERENCES projects(id) ON DELETE RESTRICT,
    manufacturer TEXT NOT NULL,
    mpn TEXT NOT NULL,
    package_variant TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX components_project_id ON components(project_id);

CREATE TABLE builds (
    id TEXT PRIMARY KEY NOT NULL,
    component_id TEXT NOT NULL REFERENCES components(id) ON DELETE RESTRICT,
    state TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    bft_version TEXT NOT NULL,
    schema_version TEXT,
    pdl_revision TEXT,
    ai_provider TEXT,
    ai_model TEXT,
    source_hash TEXT,
    ir_hash TEXT,
    build_inputs_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX builds_component_id ON builds(component_id);
