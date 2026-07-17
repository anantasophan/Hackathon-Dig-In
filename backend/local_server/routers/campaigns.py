"""Campaign routers for the Local Development Server.

Implements six FastAPI route handlers that mirror the Lambda endpoints,
reading from MockDataStore instead of Athena/DynamoDB.

No imports from athena_client, auth, audit, or rate_limiter.

Requirements: 2.1-2.9, 3.1-3.7, 4.1-4.7, 5.1-5.6, 6.1-6.7, 7.1-7.7
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from local_server.mock_store import store
from shared.calculations import calculate_take_up_rate, compute_statistics
from shared.models import (
    SIMILAR_CAMPAIGN_DIMENSIONS,
    ActiveFilter,
    CampaignMetric,
    SimilarCampaignResult,
)
from shared.pii_filter import strip_pii
from shared.sorting import (
    sort_by_attribute,
    sort_regional_performance,
    sort_similar_campaigns,
)

# ---------------------------------------------------------------------------
# Router instance
# ---------------------------------------------------------------------------

router = APIRouter()

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
    (90, None),
]

# Customer attribute columns for distributions (using actual LeadRecord field names)
_CUSTOMER_ATTRIBUTES: list[str] = [
    "segment_by_aum",
    "range_usia",
    "media_blasting",
    "segment_div_owner",
    "flag_program",
]

_MAX_SIMILAR_RESULTS: int = 20
_MAX_REGION_TREND_WEEKS: int = 8

# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------


class ComparisonRequestBody(BaseModel):
    """Request body for POST /api/campaigns/comparison."""

    campaign_ids: list[str] = []
    group_by: str | None = None


class SimilarRequestBody(BaseModel):
    """Request body for POST /api/campaigns/similar."""

    reference_campaign_id: str = ""
    dimensions: list[str] = []
    limit: int | None = None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_date(raw: str | None, field_name: str) -> str | None:
    """Validate a date string against yyyy-mm-dd format.

    Args:
        raw: Raw date string from query params, or None if absent.
        field_name: Parameter name for error messages.

    Returns:
        The original string if valid, or None if absent.

    Raises:
        HTTPException: 400 if the string is present but not valid ISO 8601.
    """
    if raw is None:
        return None
    try:
        date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Parameter tanggal tidak valid: '{raw}' untuk '{field_name}'. "
                "Gunakan format yyyy-mm-dd."
            ),
        )
    return raw


def _parse_string_list(raw: str | None) -> list[str] | None:
    """Parse a comma-separated query param into a list of strings.

    Args:
        raw: Comma-separated string or None.

    Returns:
        Non-empty list of stripped values, or None when absent.
    """
    if not raw:
        return None
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values if values else None


def _parse_int_list(raw: str | None) -> list[int] | None:
    """Parse a comma-separated query param into a list of integers.

    Non-integer tokens are silently dropped.

    Args:
        raw: Comma-separated string of integers or None.

    Returns:
        Non-empty list of ints, or None when absent.
    """
    if not raw:
        return None
    result: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if token.lstrip("-").isdigit():
            result.append(int(token))
    return result if result else None


def _build_active_filters(
    start_date: str | None,
    end_date: str | None,
    flag_program: list[str] | None,
    media_blasting: list[str] | None,
    wilayah: list[int] | None,
    jenis_leads: list[str] | None,
) -> list[ActiveFilter]:
    """Build a list of ActiveFilter objects from active query parameters.

    Args:
        start_date: Start date string (yyyy-mm-dd) or None.
        end_date: End date string (yyyy-mm-dd) or None.
        flag_program: Active flag_program filter values or None.
        media_blasting: Active media_blasting filter values or None.
        wilayah: Active wilayah filter values (ints) or None.
        jenis_leads: Active jenis_leads filter values or None.

    Returns:
        List of ActiveFilter instances for all active filters.
    """
    filters: list[ActiveFilter] = []

    if start_date or end_date:
        period_str = f"{start_date or ''}/{end_date or ''}"
        filters.append(ActiveFilter(field="period", values=[period_str]))

    if flag_program:
        filters.append(ActiveFilter(field="flag_program", values=flag_program))

    if media_blasting:
        filters.append(ActiveFilter(field="media_blasting", values=media_blasting))

    if wilayah:
        filters.append(ActiveFilter(field="wilayah", values=[str(w) for w in wilayah]))

    if jenis_leads:
        filters.append(ActiveFilter(field="jenis_leads", values=jenis_leads))

    return filters


def _build_histogram(days_list: list[int]) -> list[dict[str, Any]]:
    """Build a 7-bin histogram from a list of take-up day values.

    Bins: 0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+.
    Each bin satisfies ``range_start <= value < range_end`` (last bin open-ended).

    Args:
        days_list: List of integer day counts (must be non-empty).

    Returns:
        List of 7 dicts with keys: range_start, range_end, count, percentage.
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


def _build_attribute_distribution(
    rows: list[dict[str, Any]],
    attribute: str,
) -> dict[str, Any]:
    """Build a distribution dict for one customer attribute column.

    Args:
        rows: PII-stripped lead dicts.
        attribute: The field name to group by.

    Returns:
        Dict with attribute, available, items, unavailable_reason.
    """
    from shared.calculations import compute_distribution_percentages  # local import avoids circular

    group_counts: dict[str, int] = {}
    group_take_up: dict[str, int] = {}

    for row in rows:
        raw_value = row.get(attribute)
        if raw_value is None or str(raw_value).strip() == "":
            continue

        label = str(raw_value).strip()
        group_counts[label] = group_counts.get(label, 0) + 1

        take_up_flag = str(row.get("take_up_flag") or "").upper()
        if take_up_flag == "YES":
            group_take_up[label] = group_take_up.get(label, 0) + 1
        else:
            group_take_up.setdefault(label, 0)

    if not group_counts:
        return {
            "attribute": attribute,
            "available": False,
            "items": [],
            "unavailable_reason": (
                f"Atribut '{attribute}' tidak tersedia untuk campaign ini."
            ),
        }

    try:
        percentages = compute_distribution_percentages(group_counts)
    except ValueError:
        return {
            "attribute": attribute,
            "available": False,
            "items": [],
            "unavailable_reason": (
                f"Tidak dapat menghitung distribusi untuk atribut '{attribute}'."
            ),
        }

    items: list[dict[str, Any]] = []
    for label, count in group_counts.items():
        take_up_count = group_take_up.get(label, 0)
        take_up_pct = round((take_up_count / count) * 100, 4) if count > 0 else 0.0
        items.append(
            {
                "label": label,
                "count": count,
                "percentage": percentages[label],
                "take_up_count": take_up_count,
                "take_up_percentage": take_up_pct,
            }
        )

    items.sort(key=lambda x: x["count"], reverse=True)

    return {
        "attribute": attribute,
        "available": True,
        "items": items,
        "unavailable_reason": None,
    }


def _build_chart(campaigns: list[CampaignMetric]) -> dict[str, Any]:
    """Build a Chart.js-compatible comparison chart data structure.

    Args:
        campaigns: List of CampaignMetric instances.

    Returns:
        Dict with labels and datasets keys.
    """
    return {
        "labels": [c.campaign_name for c in campaigns],
        "datasets": [
            {"label": "Total Leads", "data": [c.total_leads for c in campaigns]},
            {"label": "Total Take Up", "data": [c.total_take_up for c in campaigns]},
            {"label": "Take Up Rate (%)", "data": [c.take_up_rate for c in campaigns]},
            {"label": "Nilai Transaksi", "data": [c.total_transaction_value for c in campaigns]},
            {"label": "Durasi (hari)", "data": [c.duration_days for c in campaigns]},
        ],
    }

# ---------------------------------------------------------------------------
# 4.1  GET /campaigns/overview
# ---------------------------------------------------------------------------


@router.get("/campaigns/overview")
async def campaign_overview(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    flag_program: str | None = Query(default=None),
    media_blasting: str | None = Query(default=None),
    wilayah: str | None = Query(default=None),
    jenis_leads: str | None = Query(default=None),
) -> JSONResponse:
    """Return aggregate campaign metrics with optional filters.

    Query parameters (all optional):
        start_date: Filter period start (yyyy-mm-dd).
        end_date: Filter period end (yyyy-mm-dd).
        flag_program: Comma-separated program type values.
        media_blasting: Comma-separated channel values.
        wilayah: Comma-separated region code integers.
        jenis_leads: Comma-separated leads purpose values.

    Returns:
        200 with total_leads, total_take_up, take_up_rate, total_campaigns,
        trend (≥4 data points), and filters.
        400 if date format is invalid.

    Requirements: 2.1-2.9
    """
    # Validate dates
    _validate_date(start_date, "start_date")
    _validate_date(end_date, "end_date")

    # Parse list params
    fp_list = _parse_string_list(flag_program)
    mb_list = _parse_string_list(media_blasting)
    wil_list = _parse_int_list(wilayah)
    jl_list = _parse_string_list(jenis_leads)

    # Build active filters for response
    active_filters = _build_active_filters(
        start_date, end_date, fp_list, mb_list, wil_list, jl_list
    )
    filters_payload = [asdict(f) for f in active_filters]

    # Query leads
    leads = store.get_leads(
        flag_program=fp_list,
        media_blasting=mb_list,
        wilayah=wil_list,
        jenis_leads=jl_list,
        start_date=start_date,
        end_date=end_date,
    )

    # Empty result
    if not leads:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Tidak ada data untuk filter yang dipilih",
                "filters": filters_payload,
            },
        )

    # Aggregate metrics
    total_leads = len(leads)
    total_take_up = sum(1 for r in leads if r.get("take_up_flag") == "YES")
    overall_rate = (
        round(calculate_take_up_rate(total_leads, total_take_up), 2)
        if total_leads > 0
        else 0.0
    )
    distinct_campaign_ids = {r.get("campaign_id") for r in leads}
    total_campaigns = len(distinct_campaign_ids)

    # Build trend — aggregate across all campaigns that appear in filtered leads
    all_trend_entries: list[dict[str, Any]] = []
    for cid in distinct_campaign_ids:
        all_trend_entries.extend(store.get_trend_data(cid))

    # Sort chronologically and deduplicate by period_start+period_end
    seen: set[tuple[str, str]] = set()
    unique_trend: list[dict[str, Any]] = []
    for entry in sorted(all_trend_entries, key=lambda e: e.get("period_start", "")):
        key = (entry.get("period_start", ""), entry.get("period_end", ""))
        if key not in seen:
            seen.add(key)
            unique_trend.append(entry)

    body: dict[str, Any] = {
        "total_leads": total_leads,
        "total_take_up": total_take_up,
        "take_up_rate": overall_rate,
        "total_campaigns": total_campaigns,
        "trend": unique_trend,
        "filters": filters_payload,
    }

    safe_body = strip_pii(body)
    return JSONResponse(status_code=200, content=safe_body)

# ---------------------------------------------------------------------------
# 4.2  POST /campaigns/comparison
# ---------------------------------------------------------------------------


@router.post("/campaigns/comparison")
async def campaign_comparison(body: ComparisonRequestBody | None = None) -> JSONResponse:
    """Compare 2-5 campaigns across key metrics.

    Request body:
        campaign_ids (list[str]): 2–5 campaign IDs to compare.
        group_by (optional str): Attribute to sort campaigns by (ascending).

    Returns:
        200 with campaigns list and comparison_chart.
        400 if body is missing, campaign_ids < 2, or > 5.

    Requirements: 3.1-3.7
    """
    if body is None:
        raise HTTPException(status_code=400, detail="Request body is required.")

    campaign_ids = body.campaign_ids or []

    if len(campaign_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"campaign_ids must contain at least 2 campaign identifiers, "
                f"got {len(campaign_ids)}."
            ),
        )

    if len(campaign_ids) > 5:
        raise HTTPException(
            status_code=400,
            detail=(
                f"campaign_ids must contain at most 5 campaign identifiers, "
                f"got {len(campaign_ids)}."
            ),
        )

    group_by = body.group_by

    # Build CampaignMetric per campaign
    campaigns: list[CampaignMetric] = []
    for cid in campaign_ids:
        campaign_master = store.get_campaign(cid)
        campaign_leads = store.get_leads(campaign_id=cid)

        total_leads = len(campaign_leads)
        total_take_up = sum(1 for r in campaign_leads if r.get("take_up_flag") == "YES")
        take_up_rate = (
            round(calculate_take_up_rate(total_leads, total_take_up), 2)
            if total_leads > 0
            else 0.0
        )
        total_transaction_value = sum(
            float(r.get("total_transaction_value") or 0.0) for r in campaign_leads
        )

        # Get campaign-level metadata from master record
        nama_program = ""
        flag_program_val = ""
        duration_days = 0

        if campaign_master:
            nama_program = campaign_master.get("nama_program", "")
            flag_program_val = campaign_master.get("flag_program", "")
            duration_days = int(campaign_master.get("duration_days") or 0)

        campaigns.append(
            CampaignMetric(
                campaign_id=cid,
                campaign_name=nama_program,
                flag_program=flag_program_val,
                total_leads=total_leads,
                total_take_up=total_take_up,
                take_up_rate=take_up_rate,
                total_transaction_value=round(total_transaction_value, 2),
                duration_days=duration_days,
            )
        )

    # Optional sort via group_by (ascending)
    if group_by:
        campaigns_dicts = [asdict(c) for c in campaigns]
        sorted_dicts = sort_by_attribute(campaigns_dicts, group_by, ascending=True)
        campaigns = [CampaignMetric(**d) for d in sorted_dicts]

    chart = _build_chart(campaigns)

    return JSONResponse(
        status_code=200,
        content={
            "campaigns": [asdict(c) for c in campaigns],
            "comparison_chart": chart,
        },
    )

# ---------------------------------------------------------------------------
# 4.3  GET /campaigns/time-analysis/{campaign_id}
# ---------------------------------------------------------------------------


@router.get("/campaigns/time-analysis/{campaign_id}")
async def time_analysis(
    campaign_id: str,
    channel: str | None = Query(default=None),
    region: str | None = Query(default=None),
) -> JSONResponse:
    """Return time-to-take-up histogram and statistics for a campaign.

    Path parameter:
        campaign_id: Campaign identifier.

    Query parameters (optional):
        channel: Filter by media_blasting value.
        region: Filter by wilayah integer value.

    Returns:
        200 with histogram (7 bins), stats, channel_filter, region_filter.
        400 if campaign_id is empty.
        200 with message if no take-up data found.

    Requirements: 4.1-4.7
    """
    if not campaign_id or not campaign_id.strip():
        raise HTTPException(
            status_code=400,
            detail="campaign_id path parameter is required",
        )

    campaign_id = campaign_id.strip()

    # Load leads where take_up_flag == "YES"
    take_up_leads = [
        r for r in store.get_leads(campaign_id=campaign_id)
        if r.get("take_up_flag") == "YES"
    ]

    # Apply optional channel filter (maps to media_blasting)
    if channel:
        take_up_leads = [r for r in take_up_leads if r.get("media_blasting") == channel]

    # Apply optional region filter (maps to wilayah)
    if region:
        try:
            region_int = int(region)
            take_up_leads = [r for r in take_up_leads if r.get("wilayah") == region_int]
        except ValueError:
            take_up_leads = []

    # Empty data
    if not take_up_leads:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Belum ada data take up untuk campaign ini",
                "campaign_id": campaign_id,
            },
        )

    # Extract time_to_take_up_days — skip None/unparseable
    days_list: list[int] = []
    for row in take_up_leads:
        raw = row.get("time_to_take_up_days")
        if raw is None:
            continue
        try:
            days_list.append(int(raw))
        except (ValueError, TypeError):
            continue

    if not days_list:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Belum ada data take up untuk campaign ini",
                "campaign_id": campaign_id,
            },
        )

    # Compute statistics
    raw_stats = compute_statistics(days_list)
    stats: dict[str, Any] = {
        "min_days": int(raw_stats["min"]),
        "max_days": int(raw_stats["max"]),
        "mean_days": round(raw_stats["mean"], 1),
        "median_days": round(raw_stats["median"], 1),
        "total_take_up": len(days_list),
    }

    histogram = _build_histogram(days_list)

    return JSONResponse(
        status_code=200,
        content={
            "campaign_id": campaign_id,
            "histogram": histogram,
            "stats": stats,
            "channel_filter": channel,
            "region_filter": region,
        },
    )

# ---------------------------------------------------------------------------
# 4.4  GET /campaigns/regional/{campaign_id}
# ---------------------------------------------------------------------------


@router.get("/campaigns/regional/{campaign_id}")
async def regional_performance(
    campaign_id: str,
    flag_program: str | None = Query(default=None),
    selected_region: str | None = Query(default=None),
) -> JSONResponse:
    """Return per-region performance metrics for a campaign.

    Path parameter:
        campaign_id: Campaign identifier.

    Query parameters (optional):
        flag_program: Filter leads by program type.
        selected_region: Integer region code for weekly trend data.

    Returns:
        200 with regions (sorted by take_up_rate desc), selected_region_trend,
        and flag_program_filter.

    Requirements: 5.1-5.6
    """
    campaign_id = campaign_id.strip() if campaign_id else ""

    # Load leads, optionally filtered by flag_program
    fp_filter = [flag_program] if flag_program else None
    leads = store.get_leads(campaign_id=campaign_id, flag_program=fp_filter)

    # Empty result
    if not leads:
        return JSONResponse(
            status_code=200,
            content={
                "campaign_id": campaign_id,
                "message": "Data regional tidak tersedia untuk campaign ini",
                "regions": [],
                "selected_region_trend": [],
                "flag_program_filter": flag_program,
            },
        )

    # Group by wilayah
    region_map: dict[int, dict[str, Any]] = {}
    for row in leads:
        wil = row.get("wilayah")
        if wil is None:
            continue
        wil = int(wil)
        if wil not in region_map:
            region_map[wil] = {
                "wilayah": wil,
                "leads_count": 0,
                "take_up_count": 0,
                "total_transaction_value": 0.0,
            }
        region_map[wil]["leads_count"] += 1
        if row.get("take_up_flag") == "YES":
            region_map[wil]["take_up_count"] += 1
            region_map[wil]["total_transaction_value"] += float(
                row.get("total_transaction_value") or 0.0
            )

    regions: list[dict[str, Any]] = []
    for wil, data in region_map.items():
        l_count = data["leads_count"]
        t_count = data["take_up_count"]
        take_up_rate = (
            round(calculate_take_up_rate(l_count, t_count), 2) if l_count > 0 else 0.0
        )
        avg_transaction_value = (
            round(data["total_transaction_value"] / t_count, 2) if t_count > 0 else 0.0
        )
        regions.append(
            {
                "wilayah": wil,
                "region_name": f"Wilayah {wil}",
                "total_leads": l_count,
                "total_take_up": t_count,
                "take_up_rate": take_up_rate,
                "avg_transaction_value": avg_transaction_value,
            }
        )

    regions = sort_regional_performance(regions)

    # Build selected region trend (≤ 8 weekly entries)
    selected_region_trend: list[dict[str, Any]] = []
    if selected_region is not None:
        try:
            selected_region_int = int(selected_region)
        except ValueError:
            selected_region_int = None

        if selected_region_int is not None:
            weekly_entries = store.get_regional_weekly(campaign_id)
            filtered_weekly = [
                e for e in weekly_entries
                if e.get("wilayah") == selected_region_int
            ]
            # Sort by week_start ascending, cap at 8
            filtered_weekly.sort(key=lambda e: e.get("week_start", ""))
            selected_region_trend = filtered_weekly[:_MAX_REGION_TREND_WEEKS]

    return JSONResponse(
        status_code=200,
        content={
            "campaign_id": campaign_id,
            "campaign_name": store.get_campaign(campaign_id).get("nama_program", campaign_id) if store.get_campaign(campaign_id) else campaign_id,
            "flag_program": flag_program,
            "regions": regions,
            "trend": selected_region_trend,
            "selected_region_trend": selected_region_trend,
            "flag_program_filter": flag_program,
        },
    )

# ---------------------------------------------------------------------------
# 4.5  GET /campaigns/customer-criteria/{campaign_id}
# ---------------------------------------------------------------------------


@router.get("/campaigns/customer-criteria/{campaign_id}")
async def customer_criteria(campaign_id: str) -> JSONResponse:
    """Return demographic attribute distributions for a campaign.

    Path parameter:
        campaign_id: Campaign identifier.

    Returns:
        200 with distributions for 5 attributes, available_attributes,
        and unavailable_attributes.
        400 if campaign_id is empty.
        200 with message if no leads data found.

    Requirements: 6.1-6.7
    """
    if not campaign_id or not campaign_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Parameter 'campaign_id' wajib diisi.",
        )

    campaign_id = campaign_id.strip()

    leads = store.get_leads(campaign_id=campaign_id)

    if not leads:
        return JSONResponse(
            status_code=200,
            content={
                "campaign_id": campaign_id,
                "message": "Tidak ada data karakteristik nasabah untuk campaign ini.",
            },
        )

    # Strip PII from all rows before processing
    safe_rows: list[dict[str, Any]] = strip_pii(leads)  # type: ignore[assignment]

    distributions: list[dict[str, Any]] = []
    available_attributes: list[str] = []
    unavailable_attributes: list[str] = []

    for attribute in _CUSTOMER_ATTRIBUTES:
        dist = _build_attribute_distribution(safe_rows, attribute)
        distributions.append(dist)
        if dist["available"]:
            available_attributes.append(attribute)
        else:
            unavailable_attributes.append(attribute)

    response_body: dict[str, Any] = {
        "campaign_id": campaign_id,
        "distributions": distributions,
        "available_attributes": available_attributes,
        "unavailable_attributes": unavailable_attributes,
    }

    if unavailable_attributes:
        response_body["partial_data_message"] = (
            f"Atribut berikut tidak tersedia untuk campaign ini: "
            f"{', '.join(unavailable_attributes)}."
        )

    return JSONResponse(status_code=200, content=response_body)

# ---------------------------------------------------------------------------
# 4.6  POST /campaigns/similar
# ---------------------------------------------------------------------------


@router.post("/campaigns/similar")
async def similar_campaign(body: SimilarRequestBody | None = None) -> JSONResponse:
    """Find campaigns similar to a reference campaign on requested dimensions.

    Request body:
        reference_campaign_id (str): Reference campaign ID (required, non-empty).
        dimensions (list[str]): One or more of media_blasting, jenis_leads,
            flag_program (required, non-empty).
        limit (optional int): Max results; capped at 20.

    Returns:
        200 with similar_campaigns list and learning_summary.
        400 for missing/invalid fields or invalid dimension values.

    Requirements: 7.1-7.7
    """
    if body is None:
        raise HTTPException(status_code=400, detail="Request body is required.")

    reference_id = (body.reference_campaign_id or "").strip()
    if not reference_id:
        raise HTTPException(
            status_code=400,
            detail="reference_campaign_id is required and must be non-empty.",
        )

    dimensions = body.dimensions or []
    if not dimensions:
        raise HTTPException(
            status_code=400,
            detail="dimensions is required and must contain at least one value.",
        )

    # Validate dimensions against allowed values
    invalid_dims = [d for d in dimensions if d not in SIMILAR_CAMPAIGN_DIMENSIONS]
    if invalid_dims:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid dimension(s): {invalid_dims}. "
                f"Allowed values: {sorted(SIMILAR_CAMPAIGN_DIMENSIONS)}."
            ),
        )

    # Determine effective limit: min(requested, 20)
    raw_limit = body.limit
    effective_limit = min(raw_limit, _MAX_SIMILAR_RESULTS) if raw_limit is not None else _MAX_SIMILAR_RESULTS

    # Load similarity index entries for the reference campaign
    candidates = store.get_similarity_index(reference_id)

    # Filter: keep entries where ALL requested dimensions are in matching_dimensions
    requested_dims_set = set(dimensions)
    filtered = [
        entry for entry in candidates
        if requested_dims_set.issubset(set(entry.get("matching_dimensions", [])))
    ]

    # Convert to SimilarCampaignResult objects
    results: list[SimilarCampaignResult] = []
    for entry in filtered:
        matching_dims: list[str] = list(entry.get("matching_dimensions", []))
        results.append(
            SimilarCampaignResult(
                campaign_id=str(entry.get("similar_campaign_id", "")),
                campaign_name=str(entry.get("campaign_name", "")),
                matching_dimensions=matching_dims,
                dimension_count=int(entry.get("dimension_count", len(matching_dims))),
                similarity_score=float(entry.get("similarity_score", 0.0)),
                take_up_rate=float(entry.get("take_up_rate", 0.0)),
                total_leads=int(entry.get("total_leads", 0)),
                total_take_up=int(entry.get("total_take_up", 0)),
            )
        )

    # Sort: dimension_count desc, take_up_rate desc
    sorted_results = sort_similar_campaigns(results)

    # Apply limit cap
    limited_results = sorted_results[:effective_limit]

    if not limited_results:
        return JSONResponse(
            status_code=200,
            content={
                "similar_campaigns": [],
                "message": (
                    "Tidak ada campaign serupa ditemukan. "
                    "Coba perluas dimensi pencarian."
                ),
            },
        )

    # Build learning summary from top result
    top = limited_results[0]
    learning_summary: dict[str, Any] = {
        "take_up_rate_formatted": f"{top.take_up_rate:.2f}%",
        "top_segment": "N/A",
        "top_region": "N/A",
    }

    return JSONResponse(
        status_code=200,
        content={
            "similar_campaigns": [asdict(r) for r in limited_results],
            "learning_summary": learning_summary,
        },
    )
