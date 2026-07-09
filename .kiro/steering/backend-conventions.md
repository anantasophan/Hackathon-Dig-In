# Backend Coding Conventions

Conventions established from the implemented shared modules. All subagents working on backend Python code must follow these patterns.

## File Header

Every Python module starts with:

```python
"""<One-line summary of the module's purpose>.

Requirements: <comma-separated list>
"""

from __future__ import annotations
```

## Imports Order

1. Standard library
2. Third-party
3. Internal (`from shared.models import ...`)

## Type Hints

- Use Python 3.11+ syntax: `str | None`
- Use `list[str]` not `List[str]`

## SQL Safety

- Never use f-strings to interpolate user-provided values into SQL
- Use `_quote(value)` for string literals
- Use `_in_clause(column, values)` for IN lists
