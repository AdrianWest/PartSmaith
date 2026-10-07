"""

@package src.partsmith.ir.errors
@brief Stable, value-free diagnostics for untrusted IR input.
@details Provides the module implementation and public interfaces.
"""

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Issue:
    """@brief Represents one stable validation diagnostic.

    Attributes:
        path: JSON Pointer identifying the affected value.
        code: Stable machine-readable diagnostic code.
        message: Human-readable explanation of the issue.
    """

    path: str
    code: str
    message: str


class IRValidationError(ValueError):
    """@brief Represents one or more Component IR validation failures.
    @details The `issues` attribute contains sorted unique diagnostics.
    """

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
                f"{i.code} at {i.path or '/'}: {i.message}"
                for i in self.issues
            )
        )


def fail(path: str, code: str, message: str):
    """

    @brief Implements the fail operation.
    @param path The path argument.
    @param code The code argument.
    @param message The message argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    raise IRValidationError([Issue(path, code, message)])


def pointer(path: str, key: str | int) -> str:
    """

    @brief Implements the pointer operation.
    @param path The path argument.
    @param key The key argument.
    @return The str result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    token = str(key).replace("~", "~0").replace("/", "~1")
    return f"{path}/{token}"
