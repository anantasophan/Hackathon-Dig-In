"""Regional Performance Lambda handler.

Returns per-region metrics sorted by take-up rate with optional product
filtering and an 8-week trend for a selected region.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import json
import os
from typing import Any

from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.sorting import sort_regional_performance

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEADERS: dict[str, str] = {"Content-Type": "application/json"}

# Number of weekly trend points to return for a selected region.
_TREND_WEEKS: int = 8


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build an API Gateway-compatible Lambda response.

    Args:
        status_code: HTTP status code.
        body: Dict payload to serialize as JSON.

    Returns:
        Lambda proxy integration response dict.
    """
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps(body),
    }


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """GET /api/campaigns/regional/{id}

    Path parameters:
        campaign_id: Unique campaign identifier.

    Query parameters:
        flag_program (optional): Filter rows to a single product/program type.
        selected_region (optional int): Region code whose 8-week trend to return.

    Returns:
        API Gateway proxy response with regional performance data.

    Raises:
        No exceptions — all errors are caught and returned as HTTP responses.
    """
    # ------------------------------------------------------------------
    # 1. Extract campaign_id from path parameters
    # ------------------------------------------------------------------
    path_params: dict[str, str] = event.get("pathParameters") or {}
    campaign_id: str | None = path_params.get("campaign_id")

    if not campaign_id:
        return _response(400, {"error": "campaign_id path parameter is required"})

    # ------------------------------------------------------------------
    # 2. Extract optional query parameters
    # ------------------------------------------------------------------
    query_params: dict[str, str] = event.get("queryStringParameters") or {}
    flag_program: str | None = query_params.get("flag_program")

    selected_region: int | None = None
    selected_region_raw: str | None = query_params.get("selected_region")
    if selected_region_raw is not None:
        try:
            selected_region = int(selected_region_raw)
        except ValueError:
            return _response(
                400,
                {"error": "selected_region must be an integer"},
            )

    # ------------------------------------------------------------------
    # 3. Create AthenaClient from environment variables
    # ------------------------------------------------------------------
    athena = AthenaClient(
        database=os.environ.get("ATHENA_DATABASE", "campaign_db"),
        s3_output_location=os.environ.get(
            "ATHENA_S3_OUTPUT", "s3://campaign-datalake/athena-results/"
        ),
        region_name=os.environ.get("AWS_REGION"),
        workgroup=os.environ.get("ATHENA_WORKGROUP", "primary"),
    )

    # ------------------------------------------------------------------
    # 4. Build and execute regional performance query
    # ------------------------------------------------------------------
    sql = athena.build_regional_query(campaign_id)

    try:
        rows: list[dict[str, Any]] = athena.execute_query(sql)
    except QueryTimeoutError:
        return _response(
            408,
            {
                "error": "Regional performance query timed out. Please try again.",
                "campaign_id": campaign_id,
            },
        )
    except QueryExecutionError as exc:
        return _response(
            500,
            {
                "error": f"Regional performance query failed: {exc.reason}",
                "campaign_id": campaign_id,
            },
        )

    # ------------------------------------------------------------------
    # 5. Handle empty results (Requirement 4.5)
    # ------------------------------------------------------------------
    if not rows:
        return _response(
            200,
            {
                "campaign_id": campaign_id,
                "message": "Data regional tidak tersedia untuk campaign ini",
                "regions": [],
                "selected_region_trend": None,
                "flag_program_filter": flag_program,
            },
        )

    # ------------------------------------------------------------------
    # 6. Apply optional product filter (Requirement 4.4)
    # ------------------------------------------------------------------
    if flag_program:
        rows = [row for row in rows if row.get("product") == flag_program]

    # After filtering, it's possible all rows were eliminated.
    if not rows:
        return _response(
            200,
            {
                "campaign_id": campaign_id,
                "message": "Data regional tidak tersedia untuk campaign ini",
                "regions": [],
                "selected_region_trend": None,
                "flag_program_filter": flag_program,
            },
        )

    # ------------------------------------------------------------------
    # 7. Build per-region dicts (Requirements 4.1, 4.2)
    # ------------------------------------------------------------------
    regions: list[dict[str, Any]] = []
    for row in rows:
        try:
            leads_count = int(row.get("leads_count") or 0)
            take_up_count = int(row.get("take_up_count") or 0)
            take_up_rate = float(row.get("take_up_rate") or 0.0)
            avg_transaction_value = float(row.get("avg_transaction_value") or 0.0)
        except (ValueError, TypeError):
            # Skip malformed rows rather than crashing the entire response.
            continue

        regions.append(
            {
                "wilayah": row.get("region"),
                "leads_count": leads_count,
                "take_up_count": take_up_count,
                "take_up_rate": take_up_rate,
                "avg_transaction_value": avg_transaction_value,
            }
        )

    # ------------------------------------------------------------------
    # 8. Sort by take_up_rate descending (defensive sort — Requirement 4.2)
    # ------------------------------------------------------------------
    regions = sort_regional_performance(regions)

    # ------------------------------------------------------------------
    # 9. Build 8-week trend for selected region (Requirement 4.3)
    # ------------------------------------------------------------------
    selected_region_trend: list[dict[str, Any]] | None = None

    if selected_region is not None:
        # Extract weekly rows for the selected region from the raw query
        # results.  The regional_performance_agg table contains a
        # ``week_start`` column when un-aggregated weekly data is returned;
        # we filter and sort those rows to produce the last _TREND_WEEKS
        # data points.
        weekly_rows = [
            row
            for row in rows
            if _to_int(row.get("region")) == selected_region
            and row.get("week_start") is not None
        ]

        # Sort by week_start ascending so chronological order is preserved,
        # then take the last _TREND_WEEKS entries.
        weekly_rows.sort(key=lambda r: r.get("week_start", ""))
        weekly_rows = weekly_rows[-_TREND_WEEKS:]

        selected_region_trend = [
            {
                "week_start": row.get("week_start"),
                "leads_count": _to_int(row.get("leads_count")),
                "take_up_count": _to_int(row.get("take_up_count")),
                "take_up_rate": _to_float(row.get("take_up_rate")),
            }
            for row in weekly_rows
        ]

    # ------------------------------------------------------------------
    # 10. Return 200 with full response payload
    # ------------------------------------------------------------------
    return _response(
        200,
        {
            "campaign_id": campaign_id,
            "regions": regions,
            "selected_region_trend": selected_region_trend,
            "flag_program_filter": flag_program,
        },
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _to_int(value: Any) -> int:
    """Safely coerce *value* to ``int``, returning 0 on failure.

    Args:
        value: Any value (typically a string from Athena results).

    Returns:
        Integer representation, or 0 if conversion fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _to_float(value: Any) -> float:
    """Safely coerce *value* to ``float``, returning 0.0 on failure.

    Args:
        value: Any value (typically a string from Athena results).

    Returns:
        Float representation, or 0.0 if conversion fails.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
