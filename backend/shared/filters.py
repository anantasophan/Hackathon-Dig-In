"""Shared filter module for Campaign Insight Generator.

Provides filter application and validation using AND logic.

Requirements: 1.3, 1.4, 1.5, 3.3, 3.4, 4.4, 6.2
"""

from __future__ import annotations

from typing import Any

from shared.models import ActiveFilter

# The complete set of field names that filters may reference.
VALID_FILTER_FIELDS: frozenset[str] = frozenset(
    {"product", "sub_product", "channel", "region", "period"}
)


def validate_filters(filters: list[ActiveFilter]) -> bool:
    """Return ``True`` when every filter in *filters* is structurally valid.

    A filter is considered valid when:
    - ``field`` is a non-empty string whose value is one of the supported
      filter field names (``product``, ``sub_product``, ``channel``,
      ``region``, ``period``).
    - ``values`` is a non-empty list (each value may be any string).

    An empty *filters* list is considered valid (no constraints applied).

    Args:
        filters: List of :class:`~shared.models.ActiveFilter` instances to
            validate.

    Returns:
        ``True`` if all filters satisfy the validation rules; ``False`` if any
        filter has an invalid or unrecognised field name, or an empty
        ``values`` list.

    Examples:
        >>> from shared.models import ActiveFilter
        >>> validate_filters([ActiveFilter(field="product", values=["KPR"])])
        True
        >>> validate_filters([ActiveFilter(field="unknown", values=["x"])])
        False
        >>> validate_filters([ActiveFilter(field="region", values=[])])
        False
        >>> validate_filters([])
        True
    """
    for f in filters:
        if not f.field or f.field not in VALID_FILTER_FIELDS:
            return False
        if not f.values:
            return False
    return True


def _item_matches_filter(item: dict[str, Any], f: ActiveFilter) -> bool:
    """Return ``True`` when *item* satisfies a single :class:`ActiveFilter`.

    For most fields the check is a straightforward membership test:
    ``item[field] in filter.values``.

    The ``period`` field receives special handling because data records may
    represent a period in different ways:

    - If the item has a ``"period"`` key, that value is compared directly.
    - Otherwise, if the item has a ``"start_date"`` key, that value is used
      as a proxy for the period (allows filtering pre-aggregated rows that
      carry a ``start_date``/``end_date`` pair rather than a ``period``
      label).

    If the relevant field is absent from *item* the item is treated as
    non-matching (safe default — avoids silent data leakage through filters).

    Args:
        item: A single data record (dict).
        f: The filter to test against.

    Returns:
        ``True`` if *item* matches the filter; ``False`` otherwise.
    """
    if f.field == "period":
        # Prefer an explicit "period" key; fall back to "start_date".
        if "period" in item:
            return str(item["period"]) in f.values
        if "start_date" in item:
            return str(item["start_date"]) in f.values
        # Neither key present → no match.
        return False

    # Standard field: missing key → no match.
    if f.field not in item:
        return False

    return str(item[f.field]) in f.values


def apply_filters(
    dataset: list[dict[str, Any]],
    filters: list[ActiveFilter],
) -> list[dict[str, Any]]:
    """Return the subset of *dataset* that satisfies ALL active filters (AND logic).

    Each item in *dataset* must match every filter in *filters* to be
    included in the result.  This implements Requirement 1.5 — combined
    filters use intersection (AND) semantics, not union (OR).

    Behaviour details:

    - If *filters* is empty the full *dataset* is returned unchanged.
    - If *dataset* is empty an empty list is returned.
    - Items that are missing the field named in a filter are treated as
      non-matching and are excluded from the result.
    - The ``period`` filter compares against the item's ``"period"`` key when
      present, or falls back to the ``"start_date"`` key.

    Args:
        dataset: List of data record dicts to filter.
        filters: List of :class:`~shared.models.ActiveFilter` instances
            defining the active filter set.

    Returns:
        A new list containing only the items that satisfy all filters.  The
        original *dataset* list is not modified.

    Examples:
        >>> from shared.models import ActiveFilter
        >>> data = [
        ...     {"product": "KPR", "channel": "SMS", "region": "JKT"},
        ...     {"product": "KTA", "channel": "Email", "region": "BDG"},
        ...     {"product": "KPR", "channel": "Email", "region": "JKT"},
        ... ]
        >>> apply_filters(data, [ActiveFilter("product", ["KPR"])])
        [{'product': 'KPR', 'channel': 'SMS', 'region': 'JKT'}, {'product': 'KPR', 'channel': 'Email', 'region': 'JKT'}]

        >>> apply_filters(data, [
        ...     ActiveFilter("product", ["KPR"]),
        ...     ActiveFilter("channel", ["SMS"]),
        ... ])
        [{'product': 'KPR', 'channel': 'SMS', 'region': 'JKT'}]

        >>> apply_filters(data, [])
        [{'product': 'KPR', ...}, ...]

        >>> apply_filters([], [ActiveFilter("product", ["KPR"])])
        []
    """
    if not filters:
        return list(dataset)

    return [
        item
        for item in dataset
        if all(_item_matches_filter(item, f) for f in filters)
    ]
