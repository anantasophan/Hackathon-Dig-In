"""Shared filter module."""
from __future__ import annotations
from typing import Any
from shared.models import ActiveFilter

VALID_FILTER_FIELDS: frozenset[str] = frozenset({"product", "sub_product", "channel", "region", "period"})

def validate_filters(filters: list[ActiveFilter]) -> bool:
    for f in filters:
        if not f.field or f.field not in VALID_FILTER_FIELDS:
            return False
        if not f.values:
            return False
    return True

def apply_filters(dataset: list[dict[str, Any]], filters: list[ActiveFilter]) -> list[dict[str, Any]]:
    if not filters:
        return list(dataset)
    def matches(item: dict[str, Any], f: ActiveFilter) -> bool:
        if f.field == "period":
            v = item.get("period") or item.get("start_date")
            return str(v) in f.values if v is not None else False
        return f.field in item and str(item[f.field]) in f.values
    return [item for item in dataset if all(matches(item, f) for f in filters)]
