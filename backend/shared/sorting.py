"""Shared sorting module."""
from __future__ import annotations
from typing import Any
from shared.models import SimilarCampaignResult

_SENTINEL_HIGH = float("inf")

def sort_by_attribute(items: list[dict[str, Any]], attribute: str, ascending: bool) -> list[dict[str, Any]]:
    if ascending:
        return sorted(items, key=lambda x: (1, _SENTINEL_HIGH) if attribute not in x else (0, x[attribute]))
    def key_desc(item: dict[str, Any]) -> tuple:
        if attribute not in item:
            return (1, _SENTINEL_HIGH)
        try:
            return (0, -item[attribute])
        except TypeError:
            return (0, item[attribute])
    return sorted(items, key=key_desc)

def sort_similar_campaigns(campaigns: list[SimilarCampaignResult]) -> list[SimilarCampaignResult]:
    return sorted(campaigns, key=lambda c: (-c.dimension_count, -c.take_up_rate))

def sort_regional_performance(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(regions, key=lambda r: (1, _SENTINEL_HIGH) if "take_up_rate" not in r else (0, -r["take_up_rate"]))
