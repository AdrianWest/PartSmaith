"""Stable, value-free diagnostics for untrusted IR input."""

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Issue:
    path: str
    code: str
    message: str


class IRValidationError(ValueError):
    def __init__(self, issues: list[Issue] | tuple[Issue, ...]):
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "; ".join(
                f"{i.code} at {i.path or '/'}: {i.message}"
                for i in self.issues
            )
        )


def fail(path: str, code: str, message: str):
    raise IRValidationError([Issue(path, code, message)])


def pointer(path: str, key: str | int) -> str:
    token = str(key).replace("~", "~0").replace("/", "~1")
    return f"{path}/{token}"
