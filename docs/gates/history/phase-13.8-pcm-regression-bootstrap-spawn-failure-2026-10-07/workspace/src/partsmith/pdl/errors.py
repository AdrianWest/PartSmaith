"""

@package src.partsmith.pdl.errors
@brief Stable diagnostics for Package Definition Library input.
@details Provides the module implementation and public interfaces.
"""

from partsmith.ir.errors import Issue


class PDLValidationError(ValueError):
    """One or more deterministic PDL validation failures."""

    def __init__(self, issues: list[Issue] | tuple[Issue, ...]):
        """

        @brief Implements the __init__ operation.
        @param issues The issues argument.
        @return None.
        @details Implements the documented behavior without changing the
        public contract.

        """
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "; ".join(
                f"{issue.code} at {issue.path or '/'}: {issue.message}"
                for issue in self.issues
            )
        )


def fail(path: str, code: str, message: str) -> None:
    """

    @brief Raise one PDL validation failure.
    @param path The path argument.
    @param code The code argument.
    @param message The message argument.
    @return The None result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    raise PDLValidationError([Issue(path, code, message)])
