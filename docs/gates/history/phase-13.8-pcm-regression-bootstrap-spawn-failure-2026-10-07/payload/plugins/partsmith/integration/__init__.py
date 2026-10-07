"""@package partsmith.integration
@brief Exposes immutable integration contracts and exact binding validation.
@details Component release approval does not grant integration authority.
"""

from partsmith.integration.bindings import (
    verify_audit_binding,
    verify_contract_bindings,
    verify_files,
    verify_journal_binding,
)
from partsmith.integration.contracts import (
    REQUIRED_RULES,
    InstallationManifest,
    IntegrationAuditEnvelope,
    IntegrationAuthorizationBinding,
    IntegrationJournal,
    IntegrationPlan,
    IntegrationValidationReport,
    portable_path,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.sources import (
    ApprovedSource,
    resolve_approved_source,
    verify_source_bindings,
)

__all__ = [
    "REQUIRED_RULES",
    "ApprovedSource",
    "FailureCode",
    "InstallationManifest",
    "IntegrationAuditEnvelope",
    "IntegrationAuthorizationBinding",
    "IntegrationError",
    "IntegrationJournal",
    "IntegrationPlan",
    "IntegrationValidationReport",
    "ResourcePolicy",
    "portable_path",
    "resolve_approved_source",
    "verify_contract_bindings",
    "verify_audit_binding",
    "verify_files",
    "verify_journal_binding",
    "verify_source_bindings",
]
