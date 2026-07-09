"""Similar Campaign Lambda handler.

Handles POST /api/campaigns/similar requests, finding historical campaigns
that match a reference campaign on one or more similarity dimensions and
returning them ranked by relevance with a learning summary.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from shared.models import (
    SIMILAR_CAMPAIGN_DIMENSIONS,
    SimilarCampaignRequest,
    SimilarCampaignResponse,
    SimilarCampaignResult,
)
from shared.sorting import sort_similar_campaigns

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONTENT_TYPE_JSON: str = "application/json"
_MAX_RESULTS: int = 20

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


def _to_float(value: Any) -> float:
    """Safely convert a DynamoDB Decimal or string to float.

    Args:
        value: The raw DynamoDB attribute value, which may be a
            :class:`~decimal.Decimal`, ``float``, ``int``, or ``str``.

    Returns:
        Python ``float`` equivalent of the input value, or ``0.0`` when
        conversion fails.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    """Safely convert a DynamoDB Decimal or string to int.

    Args:
        value: The raw DynamoDB attribute value, which may be a
            :class:`~decimal.Decimal`, ``int``, or ``str``.

    Returns:
        Python ``int`` equivalent of the input value, or ``0`` when
        conversion fails.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_learning_summary(top: SimilarCampaignResult) -> dict[str, Any]:
    """Build the learning summary dict for the top similar campaign result.

    The similarity index stores only matching dimension metadata — it does
    NOT contain segment or region breakdowns.  Those would require a
    separate Athena query against the leads table.  For MVP, ``top_segment``
    and ``top_region`` are returned as ``"N/A"`` to acknowledge the
    limitation without blocking the response.

    Args:
        top: The highest-ranked :class:`~shared.models.SimilarCampaignResult`
            after sorting.

    Returns:
        Dict with keys:

        - ``take_up_rate_formatted``: take_up_rate formatted to 2 decimal
          places with a ``%`` suffix.
        - ``top_segment``: Always ``"N/A"`` for MVP (segment data not in
          similarity index — requires Athena join).
        - ``top_region``: Always ``"N/A"`` for MVP (region data not in
          similarity index — requires Athena join).

    Examples:
        >>> from shared.models import SimilarCampaignResult
        >>> r = SimilarCampaignResult("c1", "Camp", [], 2, 0.9, 18.75, 100, 18)
        >>> _build_learning_summary(r)
        {'take_up_rate_formatted': '18.75%', 'top_segment': 'N/A', 'top_region': 'N/A'}
    """
    return {
        "take_up_rate_formatted": f"{top.take_up_rate:.2f}%",
        # Segment and region data are not stored in the similarity index.
        # A future enhancement could join against Athena leads table.
        "top_segment": "N/A",
        "top_region": "N/A",
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: object) -> dict[str, Any]:
    """AWS Lambda entry point for Similar Campaign finder endpoint.

    POST /api/campaigns/similar

    Expected body::

        {
            "reference_campaign_id": "C001",
            "dimensions": ["media_blasting", "flag_program"],
            "limit": 10
        }

    The handler queries the ``CampaignSimilarityIndex`` DynamoDB table for
    all campaigns similar to the reference, filters to those matching ALL
    requested dimensions, sorts by ``dimension_count`` descending then
    ``take_up_rate`` descending, and returns at most ``min(limit, 20)``
    results.

    Args:
        event: API Gateway proxy integration event dict.
        context: Lambda context object (unused).

    Returns:
        API Gateway proxy integration response dict with HTTP status and JSON
        body.  Possible status codes:

        - ``200`` – success; ``similar_campaigns`` may be empty with an
          explanatory message when no matches are found.
        - ``400`` – missing/invalid request body, missing required field, or
          unrecognised dimension value.
    """
    # ------------------------------------------------------------------
    # 1. Parse JSON body → SimilarCampaignRequest
    # ------------------------------------------------------------------
    raw_body = event.get("body")
    if not raw_body:
        return _response(400, {"error": "Request body is required."})

    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        return _response(400, {"error": "Request body must be valid JSON."})

    reference_id: str = payload.get("reference_campaign_id", "").strip()
    if not reference_id:
        return _response(
            400, {"error": "reference_campaign_id is required and must be non-empty."}
        )

    dimensions: list[str] = payload.get("dimensions", [])
    if not dimensions:
        return _response(
            400,
            {"error": "dimensions is required and must contain at least one value."},
        )

    # ------------------------------------------------------------------
    # 2. Validate dimension values against SIMILAR_CAMPAIGN_DIMENSIONS
    # ------------------------------------------------------------------
    invalid_dims = [d for d in dimensions if d not in SIMILAR_CAMPAIGN_DIMENSIONS]
    if invalid_dims:
        return _response(
            400,
            {
                "error": (
                    f"Invalid dimension(s): {invalid_dims}. "
                    f"Allowed values: {sorted(SIMILAR_CAMPAIGN_DIMENSIONS)}."
                )
            },
        )

    try:
        request = SimilarCampaignRequest(
            reference_campaign_id=reference_id,
            dimensions=dimensions,
            limit=payload.get("limit"),
        )
    except (ValueError, TypeError) as exc:
        return _response(400, {"error": str(exc)})

    # ------------------------------------------------------------------
    # 3. Query DynamoDB CampaignSimilarityIndex table
    # ------------------------------------------------------------------
    table_name: str = os.environ.get("SIMILARITY_TABLE", "CampaignSimilarityIndex")

    dynamodb = boto3.resource(
        "dynamodb",
        region_name=os.environ.get("AWS_REGION"),
    )
    table = dynamodb.Table(table_name)

    query_response = table.query(
        KeyConditionExpression=Key("campaign_id").eq(request.reference_campaign_id),
    )
    items: list[dict[str, Any]] = query_response.get("Items", [])

    # Handle DynamoDB pagination (LastEvaluatedKey) to retrieve all pages.
    while "LastEvaluatedKey" in query_response:
        query_response = table.query(
            KeyConditionExpression=Key("campaign_id").eq(
                request.reference_campaign_id
            ),
            ExclusiveStartKey=query_response["LastEvaluatedKey"],
        )
        items.extend(query_response.get("Items", []))

    # ------------------------------------------------------------------
    # 4. Filter: keep only items where ALL requested dimensions are present
    #    in the item's matching_dimensions list
    # ------------------------------------------------------------------
    requested_dims_set: set[str] = set(request.dimensions)

    filtered_items: list[dict[str, Any]] = [
        item
        for item in items
        if requested_dims_set.issubset(set(item.get("matching_dimensions", [])))
    ]

    # ------------------------------------------------------------------
    # 5. Convert DynamoDB items to SimilarCampaignResult objects
    # ------------------------------------------------------------------
    results: list[SimilarCampaignResult] = []
    for item in filtered_items:
        matching_dimensions: list[str] = list(item.get("matching_dimensions", []))
        results.append(
            SimilarCampaignResult(
                campaign_id=str(item.get("similar_campaign_id", "")),
                campaign_name=str(item.get("campaign_name", "")),
                matching_dimensions=matching_dimensions,
                dimension_count=_to_int(item.get("dimension_count", len(matching_dimensions))),
                similarity_score=_to_float(item.get("similarity_score", 0.0)),
                take_up_rate=_to_float(item.get("take_up_rate", 0.0)),
                total_leads=_to_int(item.get("total_leads", 0)),
                total_take_up=_to_int(item.get("total_take_up", 0)),
            )
        )

    # ------------------------------------------------------------------
    # 6. Sort: dimension_count desc, take_up_rate desc (tiebreaker)
    # ------------------------------------------------------------------
    sorted_results = sort_similar_campaigns(results)

    # ------------------------------------------------------------------
    # 7. Apply limit: min(request.limit or 20, 20)
    # ------------------------------------------------------------------
    effective_limit = min(request.limit or _MAX_RESULTS, _MAX_RESULTS)
    limited_results = sorted_results[:effective_limit]

    # ------------------------------------------------------------------
    # 8. Handle no similar campaigns found (Requirement 6.5)
    # ------------------------------------------------------------------
    if not limited_results:
        empty_response = asdict(SimilarCampaignResponse(similar_campaigns=[]))
        empty_response["message"] = (
            "Tidak ada campaign serupa ditemukan. "
            "Coba perluas dimensi pencarian."
        )
        return _response(200, empty_response)

    # ------------------------------------------------------------------
    # 9. Build learning summary for top result (Requirement 6.4)
    # ------------------------------------------------------------------
    learning_summary = _build_learning_summary(limited_results[0])

    # ------------------------------------------------------------------
    # 10. Build and return SimilarCampaignResponse
    # ------------------------------------------------------------------
    similar_response = SimilarCampaignResponse(similar_campaigns=limited_results)
    body = asdict(similar_response)
    body["learning_summary"] = learning_summary

    return _response(200, body)
