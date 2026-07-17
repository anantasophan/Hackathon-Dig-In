"""Merge the mapped dummy-campaign JSON files (C006-C009) into the local
dev server's mock_data fixtures (campaigns.json, leads.json, trend_data.json,
regional_weekly.json, similarity_index.json), which already contain C001-C005.

This script APPENDS -- it does not remove or modify existing C001-C005 data.

Usage:
    python scripts/merge_dummy_into_mock_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPED_DIR = ROOT / "Data Dummy" / "json" / "mapped"
MOCK_DIR = ROOT / "backend" / "local_server" / "mock_data"


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_list_file(existing_name: str, dummy_name: str) -> None:
    """Merge a JSON-array fixture (campaigns.json, leads.json, similarity_index.json)."""
    existing_path = MOCK_DIR / existing_name
    dummy_path = MAPPED_DIR / dummy_name

    existing = load(existing_path)
    dummy = load(dummy_path)

    merged = existing + dummy
    save(existing_path, merged)
    print(f"{existing_name}: {len(existing)} + {len(dummy)} = {len(merged)} records")


def merge_dict_file(existing_name: str, dummy_name: str) -> None:
    """Merge a JSON-object-keyed-by-campaign_id fixture (trend_data.json, regional_weekly.json)."""
    existing_path = MOCK_DIR / existing_name
    dummy_path = MAPPED_DIR / dummy_name

    existing = load(existing_path)
    dummy = load(dummy_path)

    overlap = set(existing.keys()) & set(dummy.keys())
    if overlap:
        raise ValueError(f"{existing_name}: campaign_id collision: {overlap}")

    merged = {**existing, **dummy}
    save(existing_path, merged)
    print(f"{existing_name}: {len(existing)} + {len(dummy)} = {len(merged)} campaign keys")


def main() -> None:
    merge_list_file("campaigns.json", "campaigns_dummy.json")
    merge_list_file("leads.json", "leads_dummy.json")
    merge_list_file("similarity_index.json", "similarity_dummy.json")
    merge_dict_file("trend_data.json", "trend_dummy.json")
    merge_dict_file("regional_weekly.json", "regional_dummy.json")
    print()
    print("Merge complete. C006-C009 are now part of the local dev server's mock data.")


if __name__ == "__main__":
    main()
