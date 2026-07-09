# Backend Coding Conventions

Conventions established from the implemented shared modules. All subagents working on backend Python code must follow these patterns.

## File Header

Every Python module starts with:

```python
"""<One-line summary of the module's purpose>.

<Optional longer description paragraph.>

Requirements: <comma-separated list, e.g. 1.2, 3.1>
"""

from __future__ import annotations
```

## Imports Order

1. Standard library (`time`, `datetime`, `dataclasses`, etc.)
2. Third-party (`boto3`, `pydantic`, etc.)
3. Internal (`from shared.models import ...`)

Separated by blank lines. No wildcard imports.

## Type Hints

- Use Python 3.11+ syntax: `str | None` (not `Optional[str]`)
- Exception: `Optional` from `typing` is still used in dataclass fields for clarity
- Use `list[str]` not `List[str]`, `dict[str, Any]` not `Dict`
- Always annotate function parameters and return types

## Docstrings

Google-style docstrings on all public functions and classes:

```python
def my_func(items: list[dict], key: str) -> list[dict]:
    """One-line summary ending with period.

    Optional longer explanation paragraph.

    Args:
        items: Description of items parameter.
        key: Description of key parameter.

    Returns:
        Description of what is returned.

    Raises:
        ValueError: When and why this is raised.

    Examples:
        >>> my_func([{"x": 1}], "x")
        [{'x': 1}]
    """
```

## Constants

Module-level constants use `ALL_CAPS` with type annotation:

```python
_POLL_INTERVAL_SECONDS: float = 1.0
VALID_MEDIA_BLASTING: frozenset[str] = frozenset({"wa", "digisales"})
```

Private constants prefixed with `_`.

## Non-Mutating Functions

All sorting and transformation functions must be **non-mutating** — return a new collection, never modify input in place.

## Error Handling

- Define custom exception classes for domain errors (e.g. `QueryTimeoutError`, `QueryExecutionError`)
- Include descriptive attributes on exception classes
- Use `except Exception:  # noqa: BLE001` with `pass` only for best-effort cleanup (not general catching)

## Sentinel Values

Use `float("inf")` / `float("-inf")` as sentinels for missing-key sort ordering. Always document why.

## SQL Safety

- Never use f-strings to interpolate user-provided values into SQL
- Use `_quote(value)` for string literals → doubles internal single-quotes
- Use `_in_clause(column, values)` for IN lists → empty list returns `(1 = 0)`
- Use `_bind_params(sql, params)` for `:name` placeholder substitution (longest-key-first)
