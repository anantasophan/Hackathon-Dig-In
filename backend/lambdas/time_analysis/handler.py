"""Time Analysis Lambda handler for Campaign Insight Generator.

Handles GET /api/campaigns/time-analysis/{campaign_id}.
Queries Athena for lead take-up timing data, computes a histogram
over fixed bins, and returns descriptive statistics.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from __future__ import annotations

import json
import os
from typing import Any

from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.calculations import compute_statistics

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fixed histogram bin edges: [0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+]
_HISTOGRAM_BINS: list[tuple[int, int | None]] = [
    (0, 7),
    (7, 14),
    (14, 21),
    (21, 30),
    (30, 60),
    (60, 90),
    (90, None),  # 90+ (open-ended upper bin)
]

_HEADERS: dict[str, str] = {"Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build an API Gateway proxy response dict.

    Args:
        status_code: HTTP status code.
        body: Response payload to serialise as JSON.

    Returns:
        API Gateway-compatible response dict with statusCode, headers, and body.
    """
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps(body),
    }


def _build_histogram(days_list: list[int]) -> list[dict[str, Any]]:
    """Build a histogram over the fixed time bins from a list of day counts.

    Bins are: 0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+.
    Each bin counts how many values satisfy ``range_start <= value < range_end``
    (the last bin, 90+, has no upper bound).
    Percentages are rounded to 2 decimal places.

    Args:
        days_list: Non-empty list of integer day values.

    Returns:
        List of dicts, one per bin, with keys:
        ``range_start``, ``range_end`` (``None`` for the last bin),
        ``count``, and ``percentage``.
    """
    total = len(days_list)
    result: list[dict[str, Any]] = []

    for range_start, range_end in _HISTOGRAM_BINS:
        if range_end is None:
            count = sum(1 for d in days_list if d >= range_start)
        else:
            count = sum(1 for d in days_list if range_start <= d < range_end)

        percentage = round((count / total) * 100, 2) if total > 0 else 0.0

        result.append(
            {
                "range_start": range_start,
                "range_end": range_end,
                "count": count,
                "percentage": percentage,
            }
        )

    return result


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle time-to-take-up analysis requests.

    Computes a histogram and descriptive statistics for the distribution of
    days between lead distribution and actual take-up for a given campaign.
    Supports optional filtering by channel or region.

    Args:
        event: API Gateway proxy event.  Expected keys:
            - ``pathParameters["campaign_id"]``: required campaign identifier.
            - ``queryStringParameters["channel"]``: optional channel filter.
            - ``queryStringParameters["region"]``: optional region filter.
        context: Lambda context object (unused).

    Returns:
        API Gateway proxy response dict.  Possible status codes:

        - ``200``: Success with histogram and stats, or empty-state message.
        - ``400``: Missing or invalid ``campaign_id``.
        - ``408``: Athena query timed out.
        - ``500``: Athena query execution error or unexpected failure.

    Examples:
        Successful response body structure::

            {
                "campaign_id": "C001",
                "histogram": [
                    {"range_start": 0, "range_end": 7, "count": 12, "percentage": 40.0},
                    ...
                ],
                "stats": {
                    "min_days": 1,
                    "max_days": 95,
                    "mean_days": 18.5,
                    "median_days": 14.0,
                    "total_take_up": 30
                },
                "channel_filter": null,
                "region_filter": null
            }

        Empty-state response body structure::

            {
                "message": "Belum ada data take up untuk campaign ini",
                "campaign_id": "C001"
            }
    """
    # ------------------------------------------------------------------
    # 1. Extract path parameter: campaign_id
    # ------------------------------------------------------------------
    path_params: dict[str, str] = event.get("pathParameters") or {}
    campaign_id: str | None = path_params.get("campaign_id")

    if not campaign_id:
        return _json_response(
            400,
            {"error": "campaign_id path parameter is required"},
        )

    # ------------------------------------------------------------------
    # 2. Extract optional query parameters: channel, region
    # ------------------------------------------------------------------
    query_params: dict[str, str] = event.get("queryStringParameters") or {}
    channel: str | None = query_params.get("channel") or None
    region: str | None = query_params.get("region") or None

    # ------------------------------------------------------------------
    # 3. Create AthenaClient from environment variables
    # ------------------------------------------------------------------
    athena = AthenaClient(
        database=os.environ["ATHENA_DATABASE"],
        s3_output_location=os.environ["ATHENA_OUTPUT_LOCATION"],
        region_name=os.environ.get("AWS_REGION"),
    )

    # ------------------------------------------------------------------
    # 4. Build and execute the Athena query
    # ------------------------------------------------------------------
    try:
        sql = athena.build_time_analysis_query(campaign_id)
        rows: list[dict[str, Any]] = athena.execute_query(sql)
    except QueryTimeoutError:
        return _json_response(
            408,
            {
                "error": "Query timed out. Please retry.",
                "campaign_id": campaign_id,
            },
        )
    except QueryExecutionError as exc:
        return _json_response(
            500,
            {
                "error": f"Query execution failed: {exc.reason}",
                "campaign_id": campaign_id,
            },
        )

    # ------------------------------------------------------------------
    # 5 & 6. Apply optional channel and region filters
    # ------------------------------------------------------------------
    if channel is not None:
        rows = [row for row in rows if row.get("channel") == channel]

    if region is not None:
        rows = [row for row in rows if row.get("region") == str(region)]

    # ------------------------------------------------------------------
    # 7. Handle empty data after filtering
    # ------------------------------------------------------------------
    if not rows:
        return _json_response(
            200,
            {
                "message": "Belum ada data take up untuk campaign ini",
                "campaign_id": campaign_id,
            },
        )

    # ------------------------------------------------------------------
    # 8. Extract time_to_take_up_days, skipping nulls/non-numeric values
    # ------------------------------------------------------------------
    days_list: list[int] = []
    for row in rows:
        raw = row.get("time_to_take_up_days")
        if raw is None or raw == "":
            continue
        try:
            days_list.append(int(raw))
        except (ValueError, TypeError):
            continue

    # ------------------------------------------------------------------
    # 9. Handle case where all day values are null/unparseable
    # ------------------------------------------------------------------
    if not days_list:
        return _json_response(
            200,
            {
                "message": "Belum ada data take up untuk campaign ini",
                "campaign_id": campaign_id,
            },
        )

    # ------------------------------------------------------------------
    # 10. Compute statistics
    # ------------------------------------------------------------------
    raw_stats = compute_statistics(days_list)

    stats: dict[str, Any] = {
        "min_days": int(raw_stats["min"]),
        "max_days": int(raw_stats["max"]),
        "mean_days": round(raw_stats["mean"], 1),
        "median_days": round(raw_stats["median"], 1),
        "total_take_up": len(days_list),
    }

    # ------------------------------------------------------------------
    # 11. Build histogram
    # ------------------------------------------------------------------
    histogram = _build_histogram(days_list)

    # ------------------------------------------------------------------
    # 12. Return successful response
    # ------------------------------------------------------------------
    return _json_response(
        200,
        {
            "campaign_id": campaign_id,
            "histogram": histogram,
            "stats": stats,
            "channel_filter": channel,
            "region_filter": region,
        },
    )
