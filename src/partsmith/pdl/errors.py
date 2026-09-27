"""Stable diagnostics for Package Definition Library input."""

from partsmith.ir.errors import Issue


class PDLValidationError(ValueError):
    """One or more deterministic PDL validation failures."""

    def __init__(self, issues: list[Issue] | tuple[Issue, ...]):
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "; ".join(
                f"{issue.code} at {issue.path or '/'}: {issue.message}"
                for issue in self.issues
            )
        )


def fail(path: str, code: str, message: str) -> None:
    """Raise one PDL validation failure."""
    raise PDLValidationError([Issue(path, code, message)])
