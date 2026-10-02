"""

@package src.partsmith.persistence.__init__
@brief SQLite persistence; callers own record transaction
boundaries.
@details Provides the module implementation and public interfaces.
"""

from partsmith.persistence.database import connect, database, migrate
from partsmith.persistence.immutable import (
    IdentityConflictError,
    ImmutableStore,
    StaleHeadError,
    StoredRevision,
)
from partsmith.persistence.records import Build, Component, Project, Repository

__all__ = [
    "Build",
    "Component",
    "IdentityConflictError",
    "ImmutableStore",
    "Project",
    "Repository",
    "StaleHeadError",
    "StoredRevision",
    "connect",
    "database",
    "migrate",
]
