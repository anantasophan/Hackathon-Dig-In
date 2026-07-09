"""Campaign Comparison Lambda handler.

Handles POST /api/campaigns/comparison requests, comparing 2–5 campaigns
across five key metrics and returning chart-ready data for the frontend.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.calculations import calculate_take_up_rate
from shared.models import CampaignComparisonRequest, CampaignComparisonResponse, CampaignMetric
from shared.sorting import sort_by_attribute

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONTENT_TYPE_JSON: str = "application/json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build a standard API Gateway proxy response dict.

    Args:
        status_code: HTTP status code to return.
        body: Dict to serialise as the JSON response body.

    Returns:
        API Gateway proxy integration response dict.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": _CONTENT_TYPE_JSON},
        "body": json.dumps(body),
    }


def _build_chart(campaigns: list[CampaignMetric]) -> dict[str, Any]:
    """Build a Chart.js-compatible comparison chart data structure.

    Args:
        campaigns: Ordered list of :class:`~shared.models.CampaignMetric`
            instances to visualise.

    Returns:
        Dict with ``labels`` and ``datasets`` keys ready for Chart.js rendering.
    """
    return {
        "labels": [c.campaign_name for c in campaigns],
        "datasets": [
            {
                "label": "Total Leads",
                "data": [c.total_leads for c in campaigns],
            },
            {
                "label": "Total Take Up",
                "data": [c.total_take_up for c in campaigns],
            },
            {
                "label": "Take Up Rate (%)",
                "data": [c.take_up_rate for c in campaigns],
            },
            {
                "label": "Nilai Transaksi",
                "data": [c.total_transaction_value for c in campaigns],
            },
            {
                "label": "Durasi (hari)",
                "data": [c.duration_days for c in campaigns],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: object) -> dict[str, Any]:
    """AWS Lambda entry point for Campaign Comparison endpoint.

    POST /api/campaigns/comparison

    Expected body::

        {
            "campaign_ids": ["C001", "C002"],
            "group_by": "flag_program" | "wilayah" | "media_blasting" | null
        }

    Args:
        event: API Gateway proxy integration event dict.
        context: Lambda context object (unused).

    Returns:
        API Gateway proxy integration response dict with HTTP status and JSON
        body.  Possible status codes:

        - ``200`` – success (campaigns list may be empty if no data found).
        - ``400`` – missing/invalid request body or invalid ``campaign_ids``
          count (must be 2–5).
        - ``408`` – Athena query timed out.
        - ``500`` – Athena query execution error.
    """
    # ------------------------------------------------------------------
    # 1. Parse JSON body
    # ------------------------------------------------------------------
    raw_body = event.get("body")
    if not raw_body:
        return _response(400, {"error": "Request body is required."})

    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        return _response(400, {"error": "Request body must be valid JSON."})

    # ------------------------------------------------------------------
    # 2. Validate and build the request model
    # ------------------------------------------------------------------
    try:
        request = CampaignComparisonRequest(
            campaign_ids=payload.get("campaign_ids", []),
            group_by=payload.get("group_by"),
        )
    except (ValueError, TypeError) as exc:
        return _response(400, {"error": str(exc)})

    # ------------------------------------------------------------------
    # 3. Initialise AthenaClient from environment variables
    # ------------------------------------------------------------------
    athena = AthenaClient(
        database=os.environ.get("ATHENA_DATABASE", "campaign_db"),
        s3_output_location=os.environ.get(
            "ATHENA_S3_OUTPUT", "s3://campaign-insight-athena-results/"
        ),
        region_name=os.environ.get("AWS_REGION"),
        workgroup=os.environ.get("ATHENA_WORKGROUP", "primary"),
    )

    # ------------------------------------------------------------------
    # 4. Build and execute the comparison query
    # ------------------------------------------------------------------
    sql = athena.build_comparison_query(request.campaign_ids)

    try:
        rows: list[dict[str, Any]] = athena.execute_query(sql)
    except QueryTimeoutError as exc:
        return _response(
            408,
            {
                "error": "Query timed out.",
                "details": str(exc),
            },
        )
    except QueryExecutionError as exc:
        return _response(
            500,
            {
                "error": "Query execution failed.",
                "details": str(exc),
            },
        )

    # ------------------------------------------------------------------
    # 5. Handle empty result set
    # ------------------------------------------------------------------
    if not rows:
        empty_response = CampaignComparisonResponse(
            campaigns=[],
            comparison_chart={},
        )
        body = asdict(empty_response)
        body["message"] = "No campaign data found for the requested campaign IDs."
        return _response(200, body)

    # ------------------------------------------------------------------
    # 6. Build CampaignMetric objects from query rows
    # ------------------------------------------------------------------
    campaigns: list[CampaignMetric] = []
    for row in rows:
        total_leads = int(row.get("total_leads") or 0)
        total_take_up = int(row.get("total_take_up") or 0)

        # Recalculate take_up_rate for safety; fall back to 0.0 when leads = 0.
        if total_leads > 0:
            take_up_rate = calculate_take_up_rate(total_leads, total_take_up)
        else:
            take_up_rate = 0.0

        campaigns.append(
            CampaignMetric(
                campaign_id=row.get("campaign_id", ""),
                campaign_name=row.get("campaign_name", ""),
                # flag_program is not returned by build_comparison_query;
                # default to empty string to satisfy the model.
                flag_program=row.get("flag_program", ""),
                total_leads=total_leads,
                total_take_up=total_take_up,
                take_up_rate=take_up_rate,
                total_transaction_value=float(
                    row.get("total_transaction_value") or 0.0
                ),
                duration_days=int(row.get("duration_days") or 0),
            )
        )

    # ------------------------------------------------------------------
    # 7. Optional: sort by group_by attribute (ascending)
    # ------------------------------------------------------------------
    if request.group_by:
        campaigns_dicts = [asdict(c) for c in campaigns]
        sorted_dicts = sort_by_attribute(
            campaigns_dicts, request.group_by, ascending=True
        )
        # Reconstruct CampaignMetric objects in sorted order
        campaigns = [CampaignMetric(**d) for d in sorted_dicts]

    # ------------------------------------------------------------------
    # 8. Build chart data and return response
    # ------------------------------------------------------------------
    comparison_chart = _build_chart(campaigns)

    comparison_response = CampaignComparisonResponse(
        campaigns=campaigns,
        comparison_chart=comparison_chart,
    )

    return _response(200, asdict(comparison_response))
