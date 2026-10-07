"""

@package src.partsmith.persistence.__init__
@brief SQLite persistence; callers own record transaction
boundaries.
@details Provides the module implementation and public interfaces.
"""

from partsmith.persistence.database import (
    connect,
    database,
    migrate,
    savepoint,
    utc_timestamp,
)
from partsmith.persistence.immutable import (
    IdentityConflictError,
    ImmutableStore,
    StaleHeadError,
    StoredRevision,
)
from partsmith.persistence.records import Build, Component, Project, Repository
from partsmith.persistence.release import (
    ReleaseStore,
    validation_semantics_hash,
)

__all__ = [
    "Build",
    "Component",
    "IdentityConflictError",
    "ImmutableStore",
    "Project",
    "Repository",
    "ReleaseStore",
    "StaleHeadError",
    "StoredRevision",
    "connect",
    "database",
    "migrate",
    "savepoint",
    "utc_timestamp",
    "validation_semantics_hash",
]
