"""PII filter module for Campaign Insight Generator.

Strips personally identifiable information (PII) from API responses.
All API responses are filtered regardless of user role.

Requirements: 7.5, 7.6
"""

from __future__ import annotations

from typing import Any

# Module-level constant listing all PII field names to be filtered.
PII_FIELDS: frozenset[str] = frozenset(
    {
        "nama_lengkap",
        "nomor_rekening",
        "nomor_identitas",
        "alamat_lengkap",
    }
)


def strip_pii(data: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    """Return a copy of *data* with all PII fields removed.

    This function is non-mutating: it always returns a new object and
    never modifies the input in place.

    Behaviour:
    - If *data* is a ``dict``, all keys that appear in :data:`PII_FIELDS` are
      excluded from the returned dict.  The function recurses into any nested
      ``dict`` or ``list`` values so that PII is removed at every level.
    - If *data* is a ``list``, :func:`strip_pii` is applied to every element
      and the filtered list is returned.
    - Any other value type is returned unchanged (acts as a pass-through so
      that the function can safely recurse into mixed-type structures).

    Args:
        data: A ``dict`` or ``list`` (potentially nested) that may contain
            PII fields.

    Returns:
        A new ``dict`` or ``list`` with all PII fields removed at every level
        of nesting.

    Examples:
        >>> strip_pii({"nama_lengkap": "Alice", "product": "KPR"})
        {'product': 'KPR'}

        >>> strip_pii([{"nama_lengkap": "Alice"}, {"product": "KPR"}])
        [{}, {'product': 'KPR'}]

        >>> strip_pii({"lead": {"nomor_rekening": "123", "region": "JKT"}})
        {'lead': {'region': 'JKT'}}
    """
    if isinstance(data, list):
        return [strip_pii(item) for item in data]  # type: ignore[return-value]

    if isinstance(data, dict):
        return {
            key: strip_pii(value)
            for key, value in data.items()
            if key not in PII_FIELDS
        }

    # Scalar values (str, int, float, bool, None, …) — pass through unchanged.
    return data  # type: ignore[return-value]


def has_pii(data: dict[str, Any] | list[Any]) -> bool:
    """Return ``True`` if *data* contains any PII field anywhere in its structure.

    The check is recursive: PII fields are detected at any depth of nesting,
    including inside lists and nested dicts.

    Args:
        data: A ``dict`` or ``list`` (potentially nested) to inspect.

    Returns:
        ``True`` if at least one key matching a name in :data:`PII_FIELDS`
        exists anywhere in *data*; ``False`` otherwise.

    Examples:
        >>> has_pii({"product": "KPR", "nomor_identitas": "1234567890"})
        True

        >>> has_pii({"product": "KPR", "region": "JKT"})
        False

        >>> has_pii({"lead": {"alamat_lengkap": "Jl. Merdeka 1"}})
        True

        >>> has_pii([{"product": "KPR"}, {"nama_lengkap": "Bob"}])
        True
    """
    if isinstance(data, list):
        return any(has_pii(item) for item in data)

    if isinstance(data, dict):
        for key, value in data.items():
            if key in PII_FIELDS:
                return True
            # Recurse into nested dicts and lists.
            if isinstance(value, (dict, list)) and has_pii(value):
                return True

    return False
