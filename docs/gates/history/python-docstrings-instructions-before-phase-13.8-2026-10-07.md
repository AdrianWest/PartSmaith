---
name: Python docstring requirements
description: Require tagged docstrings for every Python module, function, and method.
applyTo: "**/*.py"
---
# Python Documentation Requirements

All Python code MUST follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html). All Python files, functions, and methods MUST have docstrings. Use the tagged format below for every new or modified Python file and callable.

## Google Python Style

- Follow the Google Python Style Guide for naming, imports, formatting,
    whitespace, line length, exceptions, type annotations, docstrings, and
    testing practices.
- Prefer the repository's configured Ruff checks as the local automated
    enforcement of the style guide.
- Do not introduce a project-specific exception to the Google standard without
    documenting the reason in the change.

## Module Docstrings

Every Python module must begin with a docstring containing:

- `@package` or `@file`: The module or file name.
- `@brief`: One concise sentence describing the module.
- `@details`: Additional module behavior, constraints, or usage details when useful.

Example:

```python
"""@package database_connector
@brief Connects to SQL instances.
@details Provides deterministic connection and verification helpers.
"""
```

Use `@file` when documenting a script rather than a package module:

```python
"""@file migrate_schema.py
@brief Applies the database schema migration.
@details Exits with a nonzero status when migration verification fails.
"""
```

## Function and Method Docstrings

Every function and method, including private helpers, protocol methods, properties, constructors, and test functions, must have a docstring containing:

- `@brief`: A short, one-sentence overview of the callable.
- `@param name`: One entry for every parameter, excluding `self` and `cls`.
- `@return`: The return type and the meaning of the returned value. Use `@return None` for functions whose meaningful result is `None`.
- `@details`: Important behavior, side effects, validation rules, deterministic guarantees, or exceptions. Include this tag even when the details are brief.

Example:

```python
def verify_connection(timeout: float) -> bool:
    """@brief Verifies that the database connection is available.
    @param timeout Max wait time in seconds.
    @return True if verification succeeds.
    @details Does not mutate connection state and raises ValueError for a negative timeout.
    """
```

For methods, document all parameters other than `self` or `cls`:

```python
class Connector:
    """@brief Maintains a database connection.
    @details The connection is opened lazily by `connect`.
    """

    def connect(self, host: str, port: int) -> None:
        """@brief Opens a connection to the database.
        @param host Database hostname.
        @param port Database service port.
        @return None.
        @details Raises ConnectionError when the database cannot be reached.
        """
```

## Rules

- Keep the tags in the docstring and use the exact names from the Python signature.
- Document `*args` as `@param args` and `**kwargs` as `@param kwargs`.
- Do not document `self` or `cls` as parameters.
- Keep descriptions factual, concise, and consistent with runtime behavior.
- Preserve the repository's 79-character line limit where practical.
- Use normal Python triple-double-quoted docstrings; do not replace docstrings with comments.
- When modifying a callable, update its tags if its parameters, return value, side effects, or behavior change.
