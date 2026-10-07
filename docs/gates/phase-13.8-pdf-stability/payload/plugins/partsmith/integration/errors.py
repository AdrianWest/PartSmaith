"""@package partsmith.integration.errors
@brief Defines stable machine-readable integration failure categories.
@details Error text never includes transient session data or credentials.
"""

import re
from enum import StrEnum


class FailureCode(StrEnum):
    """@brief Classifies integration failures for service adapters.
    @details Values remain separate from component build state.
    """

    INVALID_CONTRACT = "INVALID_CONTRACT"
    MISSING_SOURCE = "MISSING_SOURCE"
    UNAPPROVED_SOURCE = "UNAPPROVED_SOURCE"
    TAMPERED_SOURCE = "TAMPERED_SOURCE"
    STALE_BASE = "STALE_BASE"
    TARGET_CONFLICT = "TARGET_CONFLICT"
    NAMESPACE_CONFLICT = "NAMESPACE_CONFLICT"
    PATH_CONFLICT = "PATH_CONFLICT"
    SEMANTIC_CHECK_FAILED = "SEMANTIC_CHECK_FAILED"
    NATIVE_CHECK_FAILED = "NATIVE_CHECK_FAILED"
    IPC_UNAVAILABLE = "IPC_UNAVAILABLE"
    WRONG_IPC_SESSION = "WRONG_IPC_SESSION"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    UNSUPPORTED_ATOMIC_INSTALL = "UNSUPPORTED_ATOMIC_INSTALL"
    PUBLICATION_FAILED = "PUBLICATION_FAILED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class IntegrationError(ValueError):
    """@brief Carries a stable failure code and safe operation references.
    @details Caller secrets and exception values are excluded from the text.
    """

    def __init__(
        self,
        code: FailureCode,
        *,
        action: str = "validate",
        attempt_id: str | None = None,
        target_id: str | None = None,
        object_hashes: tuple[str, ...] = (),
        check_hashes: tuple[str, ...] = (),
    ):
        """@brief Initializes a structured integration failure.
        @param code Stable machine-readable category.
        @param action Failing service operation.
        @param attempt_id Optional safe attempt reference.
        @param target_id Optional logical target reference.
        @param object_hashes Safe referenced object identities.
        @param check_hashes Safe referenced deterministic check identities.
        @return None.
        @details The message contains only the category and a bounded operation
        identifier; reference values never enter exception text.
        """
        if not isinstance(code, FailureCode) or not re.fullmatch(
            r"[a-z][a-z0-9_-]{0,63}", action
        ):
            raise ValueError("Invalid integration failure metadata")
        for references in (object_hashes, check_hashes):
            if not isinstance(references, tuple) or any(
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                for digest in references
            ):
                raise ValueError("Invalid integration failure references")
        self.code = code
        self.action = action
        self.attempt_id = attempt_id
        self.target_id = target_id
        self.object_hashes = object_hashes
        self.check_hashes = check_hashes
        super().__init__(f"{code}: {action}")
