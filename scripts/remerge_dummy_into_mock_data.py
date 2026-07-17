"""Remove any existing C006-C009 records from mock_data, then re-merge the
freshly regenerated mapped dummy JSON files. Safe to run multiple times.

Usage:
    python scripts/remerge_dummy_into_mock_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPED_DIR = ROOT / "Data Dummy" / "json" / "mapped"
MOCK_DIR = ROOT / "backend" / "local_server" / "mock_data"

DUMMY_CAMPAIGN_IDS = {"C006", "C007", "C008", "C009"}


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def remove_and_merge_list(existing_name: str, dummy_name: str, id_field: str) -> None:
    existing_path = MOCK_DIR / existing_name
    dummy_path = MAPPED_DIR / dummy_name

    existing = load(existing_path)
    before = len(existing)
    existing = [r for r in existing if r.get(id_field) not in DUMMY_CAMPAIGN_IDS]
    removed = before - len(existing)

    dummy = load(dummy_path)
    merged = existing + dummy
    save(existing_path, merged)
    print(f"{existing_name}: removed {removed} old dummy records, "
          f"added {len(dummy)} new -> {len(merged)} total")


def remove_and_merge_dict(existing_name: str, dummy_name: str) -> None:
    existing_path = MOCK_DIR / existing_name
    dummy_path = MAPPED_DIR / dummy_name

    existing = load(existing_path)
    removed_keys = [k for k in existing if k in DUMMY_CAMPAIGN_IDS]
    for k in removed_keys:
        del existing[k]

    dummy = load(dummy_path)
    merged = {**existing, **dummy}
    save(existing_path, merged)
    print(f"{existing_name}: removed {len(removed_keys)} old dummy keys, "
          f"added {len(dummy)} new -> {len(merged)} total keys")


def main() -> None:
    remove_and_merge_list("campaigns.json", "campaigns_dummy.json", "campaign_id")
    remove_and_merge_list("leads.json", "leads_dummy.json", "campaign_id")
    remove_and_merge_list("similarity_index.json", "similarity_dummy.json", "campaign_id")
    remove_and_merge_dict("trend_data.json", "trend_dummy.json")
    remove_and_merge_dict("regional_weekly.json", "regional_dummy.json")
    print()
    print("Re-merge complete.")


if __name__ == "__main__":
    main()
