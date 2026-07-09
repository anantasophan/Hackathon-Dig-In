"""Shared sorting module for Campaign Insight Generator.

Provides sorting utilities for campaign lists, regional performance data,
and generic attribute-based sorting used across Lambda handlers.

Requirements: 2.4, 4.2, 6.1
"""

from __future__ import annotations

from typing import Any

from shared.models import SimilarCampaignResult

# Sentinel value used to sort items with a missing attribute last.
# float('inf') ensures missing items appear after any real numeric value
# in ascending order and after any real numeric value in descending order
# when the sign is flipped.
_SENTINEL_HIGH = float("inf")
_SENTINEL_LOW = float("-inf")


def sort_by_attribute(
    items: list[dict[str, Any]],
    attribute: str,
    ascending: bool,
) -> list[dict[str, Any]]:
    """Sort a list of dicts by a given attribute key.

    Items that are missing the specified *attribute* key are always sorted
    last, regardless of the *ascending* flag.

    This function is non-mutating: it returns a new list and never modifies
    the input in place.

    Args:
        items: List of dicts to sort.
        attribute: The key to sort by.
        ascending: If ``True``, sort lowest-value first (ascending order).
            If ``False``, sort highest-value first (descending order).

    Returns:
        A new sorted list of dicts.

    Examples:
        >>> sort_by_attribute(
        ...     [{"name": "B", "score": 2}, {"name": "A", "score": 1}],
        ...     attribute="score",
        ...     ascending=True,
        ... )
        [{'name': 'A', 'score': 1}, {'name': 'B', 'score': 2}]

        >>> sort_by_attribute(
        ...     [{"name": "A", "score": 1}, {"name": "B"}],
        ...     attribute="score",
        ...     ascending=True,
        ... )
        [{'name': 'A', 'score': 1}, {'name': 'B'}]
    """
    if ascending:
        # Missing items get _SENTINEL_HIGH so they sort after real values.
        def key_asc(item: dict[str, Any]) -> tuple[int, Any]:
            if attribute not in item:
                return (1, _SENTINEL_HIGH)
            return (0, item[attribute])

        return sorted(items, key=key_asc)
    else:
        # For descending, negate numeric values or use a flag tuple.
        # Missing items get (1, ...) so they sort after present items.
        def key_desc(item: dict[str, Any]) -> tuple[int, Any]:
            if attribute not in item:
                return (1, _SENTINEL_HIGH)
            val = item[attribute]
            # Negate numeric types for descending order via tuple trick.
            try:
                return (0, -val)  # type: ignore[operator]
            except TypeError:
                # Non-numeric: fall back to string sort (ascending proxy).
                return (0, val)

        return sorted(items, key=key_desc)


def sort_similar_campaigns(
    campaigns: list[SimilarCampaignResult],
) -> list[SimilarCampaignResult]:
    """Sort similar campaign results by relevance.

    Primary sort: ``dimension_count`` descending (most matched dimensions
    first).  Secondary sort (tiebreaker): ``take_up_rate`` descending
    (higher conversion rate first among campaigns with equal dimension counts).

    This function is non-mutating: it returns a new list and never modifies
    the input in place.

    Args:
        campaigns: List of :class:`~shared.models.SimilarCampaignResult`
            instances to sort.

    Returns:
        A new list sorted by ``dimension_count`` descending, then
        ``take_up_rate`` descending.

    Examples:
        >>> from shared.models import SimilarCampaignResult
        >>> a = SimilarCampaignResult("c1", "Camp A", [], 3, 0.9, 15.0, 100, 15)
        >>> b = SimilarCampaignResult("c2", "Camp B", [], 3, 0.8, 20.0, 100, 20)
        >>> c = SimilarCampaignResult("c3", "Camp C", [], 2, 0.7, 25.0, 100, 25)
        >>> [r.campaign_id for r in sort_similar_campaigns([a, b, c])]
        ['c2', 'c1', 'c3']
    """
    return sorted(
        campaigns,
        key=lambda c: (-c.dimension_count, -c.take_up_rate),
    )


def sort_regional_performance(
    regions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort regional performance records by take-up rate descending.

    Regions with the highest ``take_up_rate`` appear first.  Regions that
    are missing the ``take_up_rate`` key are sorted last.

    This function is non-mutating: it returns a new list and never modifies
    the input in place.

    Args:
        regions: List of region performance dicts, each expected to contain
            a ``take_up_rate`` key (float, percentage 0–100).

    Returns:
        A new list sorted by ``take_up_rate`` descending, with missing-key
        items at the end.

    Examples:
        >>> sort_regional_performance([
        ...     {"region": "JKT", "take_up_rate": 12.5},
        ...     {"region": "BDG", "take_up_rate": 18.0},
        ...     {"region": "SBY", "take_up_rate": 9.0},
        ... ])
        [{'region': 'BDG', 'take_up_rate': 18.0}, {'region': 'JKT', 'take_up_rate': 12.5}, {'region': 'SBY', 'take_up_rate': 9.0}]
    """
    def _key(region: dict[str, Any]) -> tuple[int, float]:
        if "take_up_rate" not in region:
            # Sort missing items last by using a large positive sentinel
            # (we negate values below, so missing → least negative → last).
            return (1, _SENTINEL_HIGH)
        return (0, -region["take_up_rate"])

    return sorted(regions, key=_key)
