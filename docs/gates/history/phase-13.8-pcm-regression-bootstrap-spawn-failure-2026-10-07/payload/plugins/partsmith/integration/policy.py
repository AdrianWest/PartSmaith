"""@package partsmith.integration.policy
@brief Freezes the version 1.0 integration resource policy.
@details Explicit limits apply cumulatively before processing object data.
"""

from dataclasses import dataclass

from partsmith.integration.errors import FailureCode, IntegrationError


@dataclass(frozen=True)
class ResourcePolicy:
    """@brief Bounds integration objects, expanded bytes and worker output.
    @details Overrides cannot disable semantic or authorization validation.
    """

    version: str = "1.0"
    object_bytes: int = 128 * 1024 * 1024
    total_bytes: int = 1024 * 1024 * 1024
    object_count: int = 10_000
    log_bytes: int = 2 * 1024 * 1024
    native_timeout_seconds: int = 120
    ipc_timeout_seconds: int = 15

    def __post_init__(self) -> None:
        """@brief Rejects unsupported versions and ineffective bounds.
        @return None.
        @details Booleans, zero and negative limits are invalid.
        """
        if self.version != "1.0":
            raise ValueError("Unsupported resource policy")
        for name in (
            "object_bytes",
            "total_bytes",
            "object_count",
            "log_bytes",
            "native_timeout_seconds",
            "ipc_timeout_seconds",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError("Resource limits must be positive integers")

    def require_sizes(self, sizes: list[int]) -> None:
        """@brief Checks object counts and cumulative expanded sizes.
        @param sizes Exact object byte lengths in the proposed inventory.
        @return None.
        @details Exceeding any bound raises RESOURCE_LIMIT before processing.
        """
        if (
            len(sizes) > self.object_count
            or any(
                type(size) is not int or size < 0 or size > self.object_bytes
                for size in sizes
            )
            or sum(sizes) > self.total_bytes
        ):
            raise IntegrationError(FailureCode.RESOURCE_LIMIT)
