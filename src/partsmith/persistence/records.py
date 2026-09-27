"""

@package src.partsmith.persistence.records
@brief Typed project, component, and build records with
parameterized storage.
@details Provides the module implementation and public interfaces.
"""

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
        """

        @brief Implements the __init__ operation.
        @param connection The connection argument.
        @return None.
        @details Implements the documented behavior without changing the
        public contract.

        """
        self.connection = connection

    def _insert(self, record: Project | Component | Build) -> None:
        """

        @brief Implements the _insert operation.
        @param record The record argument.
        @return The None result.
        @details Implements the documented behavior without changing the
        public contract.

        """
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
        """

        @brief Implements the create_project operation.
        @param name The name argument.
        @param root_path The root_path argument.
        @return The Project result.
        @details Implements the documented behavior without changing the
        public contract.

        """
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
        """

        @brief Implements the create_component operation.
        @param manufacturer The manufacturer argument.
        @param mpn The mpn argument.
        @param package_variant The package_variant argument.
        @param project_id The project_id argument.
        @return The Component result.
        @details Implements the documented behavior without changing the
        public contract.

        """
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
        """

        @brief Implements the create_build operation.
        @param component_id The component_id argument.
        @param state The state argument.
        @param bft_version The bft_version argument.
        @param schema_version The schema_version argument.
        @param pdl_revision The pdl_revision argument.
        @param ai_provider The ai_provider argument.
        @param ai_model The ai_model argument.
        @param source_hash The source_hash argument.
        @param ir_hash The ir_hash argument.
        @param build_inputs_hash The build_inputs_hash argument.
        @param started_at The started_at argument.
        @param completed_at The completed_at argument.
        @return The Build result.
        @details Implements the documented behavior without changing the
        public contract.

        """
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
        """

        @brief Implements the get_project operation.
        @param record_id The record_id argument.
        @return The Project | None result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        row = self.connection.execute(
            "SELECT * FROM projects WHERE id = ?", (record_id,)
        ).fetchone()
        return Project(**dict(row)) if row is not None else None

    def get_component(self, record_id: str) -> Component | None:
        """

        @brief Implements the get_component operation.
        @param record_id The record_id argument.
        @return The Component | None result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        row = self.connection.execute(
            "SELECT * FROM components WHERE id = ?", (record_id,)
        ).fetchone()
        return Component(**dict(row)) if row is not None else None

    def get_build(self, record_id: str) -> Build | None:
        """

        @brief Implements the get_build operation.
        @param record_id The record_id argument.
        @return The Build | None result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        row = self.connection.execute(
            "SELECT * FROM builds WHERE id = ?", (record_id,)
        ).fetchone()
        return Build(**dict(row)) if row is not None else None

    def list_components(self, project_id: str) -> list[Component]:
        """

        @brief Implements the list_components operation.
        @param project_id The project_id argument.
        @return The list[Component] result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        return [
            Component(**dict(row))
            for row in self.connection.execute(
                "SELECT * FROM components WHERE project_id = ? ORDER BY id",
                (project_id,),
            )
        ]

    def list_builds(self, component_id: str) -> list[Build]:
        """

        @brief Implements the list_builds operation.
        @param component_id The component_id argument.
        @return The list[Build] result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        return [
            Build(**dict(row))
            for row in self.connection.execute(
                "SELECT * FROM builds WHERE component_id = ? ORDER BY id",
                (component_id,),
            )
        ]
