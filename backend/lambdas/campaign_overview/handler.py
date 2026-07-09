"""Campaign Overview Lambda handler.

Handles GET /api/campaigns/overview — returns aggregate campaign metrics,
trend data, and active filter details for the requested date range.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.calculations import calculate_take_up_rate, select_granularity
from shared.models import (
    ActiveFilter,
    CampaignOverviewRequest,
    CampaignOverviewResponse,
    TrendDataPoint,
)
from shared.pii_filter import strip_pii

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_LOOKBACK_DAYS: int = 90  # ~3 months
_DATE_FORMAT: str = "%Y-%m-%d"

_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _ok(body: dict[str, Any]) -> dict[str, Any]:
    """Return a 200 Lambda proxy response with *body* serialised as JSON.

    Args:
        body: Dict to serialise into the response body.

    Returns:
        API Gateway Lambda proxy response dict.
    """
    return {
        "statusCode": 200,
        "headers": _HEADERS,
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return an error Lambda proxy response.

    Args:
        status_code: HTTP status code (e.g. 400, 408, 500).
        message: Human-readable error description.
        extra: Optional additional fields to merge into the body.

    Returns:
        API Gateway Lambda proxy response dict.
    """
    body: dict[str, Any] = {"message": message}
    if extra:
        body.update(extra)
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps(body),
    }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_string_list(raw: str | None) -> list[str] | None:
    """Parse a comma-separated query-string value into a list of strings.

    Args:
        raw: Comma-separated string, or ``None`` if the parameter was absent.

    Returns:
        Non-empty list of stripped values, or ``None`` when *raw* is absent
        or produces an empty list after splitting.
    """
    if not raw:
        return None
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values if values else None


def _parse_int_list(raw: str | None) -> list[int] | None:
    """Parse a comma-separated query-string value into a list of integers.

    Non-integer tokens are silently dropped.

    Args:
        raw: Comma-separated string of integer values, or ``None``.

    Returns:
        Non-empty list of ints, or ``None`` when *raw* is absent or no valid
        integers are present.
    """
    if not raw:
        return None
    result: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if token.lstrip("-").isdigit():
            result.append(int(token))
    return result if result else None


def _parse_request(params: dict[str, str | None]) -> CampaignOverviewRequest:
    """Build a :class:`~shared.models.CampaignOverviewRequest` from query params.

    Applies the following defaults when parameters are absent:
    - ``start_date``: 90 days (≈ 3 months) before today.
    - ``end_date``: today.

    Args:
        params: Raw query-string parameter dict from the API Gateway event.

    Returns:
        Populated :class:`~shared.models.CampaignOverviewRequest`.

    Raises:
        ValueError: If ``start_date`` or ``end_date`` are present but not in
            ``yyyy-mm-dd`` format.
    """
    today = date.today()
    default_start = today - timedelta(days=_DEFAULT_LOOKBACK_DAYS)

    raw_start = params.get("start_date")
    raw_end = params.get("end_date")

    # Validate and parse dates — raises ValueError on bad format.
    if raw_start:
        date.fromisoformat(raw_start)  # validates format
        start_date = raw_start
    else:
        start_date = default_start.isoformat()

    if raw_end:
        date.fromisoformat(raw_end)  # validates format
        end_date = raw_end
    else:
        end_date = today.isoformat()

    return CampaignOverviewRequest(
        start_date=start_date,
        end_date=end_date,
        flag_program=_parse_string_list(params.get("flag_program")),
        media_blasting=_parse_string_list(params.get("media_blasting")),
        wilayah=_parse_int_list(params.get("wilayah")),
        jenis_leads=_parse_string_list(params.get("jenis_leads")),
    )


# ---------------------------------------------------------------------------
# Active-filter builder
# ---------------------------------------------------------------------------


def _build_active_filters(request: CampaignOverviewRequest) -> list[ActiveFilter]:
    """Build the list of active filters from a parsed request.

    Only parameters that were explicitly provided (non-None, non-empty) are
    included so the client knows which constraints shaped the response.

    Args:
        request: Fully-parsed campaign overview request.

    Returns:
        List of :class:`~shared.models.ActiveFilter` instances, one per
        active parameter.
    """
    filters: list[ActiveFilter] = []

    # Date range is always present — include as a pseudo-filter so the client
    # can display the active period.
    filters.append(ActiveFilter(field="period", values=[f"{request.start_date}/{request.end_date}"]))

    if request.flag_program:
        filters.append(ActiveFilter(field="flag_program", values=request.flag_program))

    if request.media_blasting:
        filters.append(ActiveFilter(field="media_blasting", values=request.media_blasting))

    if request.wilayah:
        filters.append(ActiveFilter(field="wilayah", values=[str(w) for w in request.wilayah]))

    if request.jenis_leads:
        filters.append(ActiveFilter(field="jenis_leads", values=request.jenis_leads))

    return filters


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _aggregate_rows(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Sum total_leads, total_take_up, and campaign_count across all result rows.

    Args:
        rows: Raw Athena result rows as dicts.

    Returns:
        Tuple of ``(total_leads, total_take_up, total_campaigns)``.
    """
    total_leads = 0
    total_take_up = 0
    total_campaigns = 0

    for row in rows:
        try:
            total_leads += int(row.get("total_leads") or 0)
            total_take_up += int(row.get("total_take_up") or 0)
            total_campaigns += int(row.get("campaign_count") or 0)
        except (ValueError, TypeError):
            # Skip rows with unparseable values rather than crashing.
            continue

    return total_leads, total_take_up, total_campaigns


def _build_trend(rows: list[dict[str, Any]]) -> list[TrendDataPoint]:
    """Convert Athena result rows into a list of :class:`~shared.models.TrendDataPoint`.

    Each row must have ``period_start``, ``period_end``, ``total_leads``,
    ``total_take_up``, and ``take_up_rate`` columns.  Missing or unparseable
    rows are skipped.

    Args:
        rows: Raw Athena result rows ordered by ``period_start ASC``.

    Returns:
        Ordered list of trend data points for the sparkline chart.
    """
    trend: list[TrendDataPoint] = []

    for row in rows:
        try:
            period_start = row.get("period_start", "")
            period_end = row.get("period_end", "")
            total_leads = int(row.get("total_leads") or 0)
            total_take_up = int(row.get("total_take_up") or 0)

            # Prefer the pre-computed rate from Athena; fall back to local calc.
            raw_rate = row.get("take_up_rate")
            if raw_rate is not None:
                try:
                    row_rate = float(raw_rate)
                except (ValueError, TypeError):
                    row_rate = (
                        calculate_take_up_rate(total_leads, total_take_up)
                        if total_leads > 0
                        else 0.0
                    )
            else:
                row_rate = (
                    calculate_take_up_rate(total_leads, total_take_up)
                    if total_leads > 0
                    else 0.0
                )

            trend.append(
                TrendDataPoint(
                    period_start=period_start,
                    period_end=period_end,
                    take_up_rate=round(row_rate, 2),
                    total_leads=total_leads,
                    total_take_up=total_take_up,
                )
            )
        except (ValueError, TypeError):
            continue

    return trend


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for Campaign Overview endpoint.

    ``GET /api/campaigns/overview``

    Parses query-string parameters from the API Gateway event, executes an
    Athena query for aggregate campaign data, computes metrics, and returns
    a structured :class:`~shared.models.CampaignOverviewResponse`.

    Args:
        event: API Gateway Lambda proxy event dict.
        context: Lambda context object (unused).

    Returns:
        API Gateway Lambda proxy response dict.
    """
    # ------------------------------------------------------------------
    # 1. Parse query parameters
    # ------------------------------------------------------------------
    params: dict[str, str | None] = event.get("queryStringParameters") or {}

    try:
        request = _parse_request(params)
    except ValueError as exc:
        return _error(
            400,
            f"Parameter tanggal tidak valid: {exc}. Gunakan format yyyy-mm-dd.",
        )

    # ------------------------------------------------------------------
    # 2. Build active filters (used in error/empty responses too)
    # ------------------------------------------------------------------
    active_filters = _build_active_filters(request)
    filters_payload = [asdict(f) for f in active_filters]

    # ------------------------------------------------------------------
    # 3. Create Athena client from environment variables
    # ------------------------------------------------------------------
    database = os.environ.get("ATHENA_DATABASE", "campaign_db")
    s3_output = os.environ.get("ATHENA_S3_OUTPUT", "")
    workgroup = os.environ.get("ATHENA_WORKGROUP", "primary")

    athena = AthenaClient(
        database=database,
        s3_output_location=s3_output,
        workgroup=workgroup,
    )

    # ------------------------------------------------------------------
    # 4. Build and execute the overview query
    # ------------------------------------------------------------------
    sql = athena.build_campaign_overview_query(request)

    try:
        rows = athena.execute_query(sql)
    except QueryTimeoutError as exc:
        return _error(
            408,
            f"Query Athena melewati batas waktu ({exc.timeout_seconds} detik). "
            "Coba persempit filter atau coba kembali.",
            {"filters": filters_payload},
        )
    except QueryExecutionError as exc:
        return _error(
            500,
            f"Query Athena gagal dengan status {exc.state!r}: {exc.reason}",
        )

    # ------------------------------------------------------------------
    # 5. Handle empty results (Req 1.6)
    # ------------------------------------------------------------------
    if not rows:
        return _ok(
            {
                "message": "Tidak ada data untuk filter yang dipilih",
                "filters": filters_payload,
            }
        )

    # ------------------------------------------------------------------
    # 6. Aggregate totals and build trend (Req 1.1, 1.7)
    # ------------------------------------------------------------------
    total_leads, total_take_up, total_campaigns = _aggregate_rows(rows)

    overall_rate = (
        calculate_take_up_rate(total_leads, total_take_up)
        if total_leads > 0
        else 0.0
    )

    trend = _build_trend(rows)

    # ------------------------------------------------------------------
    # 7. Build response dataclass
    # ------------------------------------------------------------------
    response = CampaignOverviewResponse(
        total_leads=total_leads,
        total_take_up=total_take_up,
        take_up_rate=round(overall_rate, 2),
        total_campaigns=total_campaigns,
        trend=trend,
        filters=active_filters,
    )

    # ------------------------------------------------------------------
    # 8. Apply PII filter and return (Req 7.5)
    # ------------------------------------------------------------------
    response_dict = asdict(response)
    safe_dict = strip_pii(response_dict)

    return _ok(safe_dict)
