"""Shift all dates for campaigns C001-C005 forward so the earliest date
(2024-07-01, from C002) becomes 2026-01-01. Durations and relative order
between campaigns are preserved (fixed +549 day offset applied uniformly).

Only touches records belonging to C001-C005. C006-C009 (already in 2026)
are left untouched.

Usage:
    python scripts/shift_old_campaign_dates.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parent.parent / "backend" / "local_server" / "mock_data"

OLD_CAMPAIGN_IDS = {"C001", "C002", "C003", "C004", "C005"}

OLD_MIN_DATE = date(2024, 7, 1)   # earliest date currently in C001-C005 (from C002)
NEW_MIN_DATE = date(2026, 1, 1)   # target earliest date
OFFSET_DAYS = (NEW_MIN_DATE - OLD_MIN_DATE).days  # 549


def shift_date_str(s: str | None) -> str | None:
    """Shift an ISO yyyy-mm-dd date string by OFFSET_DAYS. Passes through None."""
    if not s:
        return s
    d = datetime.strptime(s, "%Y-%m-%d").date()
    return (d + timedelta(days=OFFSET_DAYS)).isoformat()


def shift_campaigns(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        campaigns = json.load(f)

    for c in campaigns:
        if c.get("campaign_id") not in OLD_CAMPAIGN_IDS:
            continue
        c["periode_start"] = shift_date_str(c.get("periode_start"))
        c["periode_end"] = shift_date_str(c.get("periode_end"))

    with path.open("w", encoding="utf-8") as f:
        json.dump(campaigns, f, ensure_ascii=False, indent=2)
    print(f"campaigns.json: shifted {sum(1 for c in campaigns if c['campaign_id'] in OLD_CAMPAIGN_IDS)} records")


def shift_leads(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        leads = json.load(f)

    count = 0
    for lead in leads:
        if lead.get("campaign_id") not in OLD_CAMPAIGN_IDS:
            continue
        lead["periode_start"] = shift_date_str(lead.get("periode_start"))
        lead["take_up_date"] = shift_date_str(lead.get("take_up_date"))
        count += 1

    with path.open("w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    print(f"leads.json: shifted {count} records")


def shift_trend(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        trend = json.load(f)

    count = 0
    for cid in OLD_CAMPAIGN_IDS:
        entries = trend.get(cid, [])
        for e in entries:
            e["period_start"] = shift_date_str(e.get("period_start"))
            e["period_end"] = shift_date_str(e.get("period_end"))
            count += 1

    with path.open("w", encoding="utf-8") as f:
        json.dump(trend, f, ensure_ascii=False, indent=2)
    print(f"trend_data.json: shifted {count} entries")


def shift_regional(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        regional = json.load(f)

    count = 0
    for cid in OLD_CAMPAIGN_IDS:
        entries = regional.get(cid, [])
        for e in entries:
            e["week_start"] = shift_date_str(e.get("week_start"))
            count += 1

    with path.open("w", encoding="utf-8") as f:
        json.dump(regional, f, ensure_ascii=False, indent=2)
    print(f"regional_weekly.json: shifted {count} entries")


def main() -> None:
    print(f"Offset: +{OFFSET_DAYS} days ({OLD_MIN_DATE.isoformat()} -> {NEW_MIN_DATE.isoformat()})")
    shift_campaigns(MOCK_DIR / "campaigns.json")
    shift_leads(MOCK_DIR / "leads.json")
    shift_trend(MOCK_DIR / "trend_data.json")
    shift_regional(MOCK_DIR / "regional_weekly.json")
    print("Done.")


if __name__ == "__main__":
    main()
