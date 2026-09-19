"""Typed project, component, and build records with parameterized storage."""

import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from partsmith import __version__


@dataclass(frozen=True, kw_only=True)
class Project:
    id: str
    name: str
    root_path: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, kw_only=True)
class Component:
    id: str
    project_id: str | None
    manufacturer: str
    mpn: str
    package_variant: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, kw_only=True)
class Build:
    id: str
    component_id: str
    state: str
    started_at: str
    bft_version: str
    created_at: str
    updated_at: str
    completed_at: str | None = None
    schema_version: str | None = None
    pdl_revision: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    source_hash: str | None = None
    ir_hash: str | None = None
    build_inputs_hash: str | None = None


class Repository:
    """Create/query records without committing the caller's transaction.

    Build state is stored as supplied; engineering state transitions and
    approval checks belong to later phases, not this persistence layer.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def _insert(self, record: Project | Component | Build) -> None:
        table = {
            Project: "projects",
            Component: "components",
            Build: "builds",
        }[type(record)]
        values = asdict(record)
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        self.connection.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        )

    def create_project(self, name: str, root_path: str) -> Project:
        now = datetime.now(UTC).isoformat()
        record = Project(
            id=str(uuid4()),
            name=name,
            root_path=root_path,
            created_at=now,
            updated_at=now,
        )
        self._insert(record)
        return record

    def create_component(
        self,
        manufacturer: str,
        mpn: str,
        package_variant: str,
        *,
        project_id: str | None = None,
    ) -> Component:
        now = datetime.now(UTC).isoformat()
        record = Component(
            id=str(uuid4()),
            project_id=project_id,
            manufacturer=manufacturer,
            mpn=mpn,
            package_variant=package_variant,
            created_at=now,
            updated_at=now,
        )
        self._insert(record)
        return record

    def create_build(
        self,
        component_id: str,
        state: str,
        *,
        bft_version: str = __version__,
        schema_version: str | None = None,
        pdl_revision: str | None = None,
        ai_provider: str | None = None,
        ai_model: str | None = None,
        source_hash: str | None = None,
        ir_hash: str | None = None,
        build_inputs_hash: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> Build:
        now = datetime.now(UTC).isoformat()
        record = Build(
            id=str(uuid4()),
            component_id=component_id,
            state=state,
            bft_version=bft_version,
            schema_version=schema_version,
            pdl_revision=pdl_revision,
            ai_provider=ai_provider,
            ai_model=ai_model,
            source_hash=source_hash,
            ir_hash=ir_hash,
            build_inputs_hash=build_inputs_hash,
            started_at=started_at or now,
            completed_at=completed_at,
            created_at=now,
            updated_at=now,
        )
        self._insert(record)
        return record

    def get_project(self, record_id: str) -> Project | None:
        row = self.connection.execute(
            "SELECT * FROM projects WHERE id = ?", (record_id,)
        ).fetchone()
        return Project(**dict(row)) if row is not None else None

    def get_component(self, record_id: str) -> Component | None:
        row = self.connection.execute(
            "SELECT * FROM components WHERE id = ?", (record_id,)
        ).fetchone()
        return Component(**dict(row)) if row is not None else None

    def get_build(self, record_id: str) -> Build | None:
        row = self.connection.execute(
            "SELECT * FROM builds WHERE id = ?", (record_id,)
        ).fetchone()
        return Build(**dict(row)) if row is not None else None

    def list_components(self, project_id: str) -> list[Component]:
        return [
            Component(**dict(row))
            for row in self.connection.execute(
                "SELECT * FROM components WHERE project_id = ? ORDER BY id",
                (project_id,),
            )
        ]

    def list_builds(self, component_id: str) -> list[Build]:
        return [
            Build(**dict(row))
            for row in self.connection.execute(
                "SELECT * FROM builds WHERE component_id = ? ORDER BY id",
                (component_id,),
            )
        ]
