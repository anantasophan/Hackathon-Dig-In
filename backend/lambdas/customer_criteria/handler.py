"""Customer Criteria Lambda handler.

Handles GET /api/campaigns/customer-criteria/{campaign_id} — returns
demographic and financial attribute distributions for a given campaign,
comparing take-up vs non-take-up groups per attribute value.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import json
import os
from typing import Any

from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.calculations import compute_distribution_percentages
from shared.pii_filter import strip_pii

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The five customer attribute columns to build distributions for.
# Order is intentional: demographic attributes first (Req 5.1), then
# financial attributes (Req 5.2).
_CUSTOMER_ATTRIBUTES: list[str] = [
    "customer_segment",
    "age_group",
    "domicile_region",
    "product_holding",
    "balance_category",
]

_TAKE_UP_YES: str = "YES"

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
# Distribution builder
# ---------------------------------------------------------------------------


def _build_attribute_distribution(
    rows: list[dict[str, Any]],
    attribute: str,
) -> dict[str, Any]:
    """Build a distribution dict for one customer attribute column.

    Groups rows by the attribute's value, then computes:
    - overall percentage share per group (take-up + non-take-up combined)
    - per-group take_up_count and take_up_percentage within the group

    If all rows have ``None`` / empty string for the attribute, the
    distribution is marked as unavailable (Req 5.5).

    Args:
        rows: PII-stripped lead rows returned by Athena.  Each row is a
            ``dict[str, Any]`` with at least ``take_up_flag`` and the
            requested *attribute* key.
        attribute: Column name to group by (one of :data:`_CUSTOMER_ATTRIBUTES`).

    Returns:
        Dict with keys:

        - ``"attribute"`` (str): the column name
        - ``"available"`` (bool): ``False`` when all values are null/empty
        - ``"items"`` (list[dict]): one entry per distinct attribute value,
          each containing ``label``, ``count``, ``percentage``,
          ``take_up_count``, ``take_up_percentage``; empty list when
          unavailable
        - ``"unavailable_reason"`` (str | None): human-readable reason when
          ``available`` is ``False``
    """
    # Collect per-group counts: group_counts[value] = total, group_take_up[value] = take-up
    group_counts: dict[str, int] = {}
    group_take_up: dict[str, int] = {}

    for row in rows:
        raw_value = row.get(attribute)
        # Treat None and blank string as missing data — skip this row for
        # the current attribute.
        if raw_value is None or str(raw_value).strip() == "":
            continue

        label = str(raw_value).strip()
        group_counts[label] = group_counts.get(label, 0) + 1

        take_up_flag = str(row.get("take_up_flag") or "").upper()
        if take_up_flag == _TAKE_UP_YES:
            group_take_up[label] = group_take_up.get(label, 0) + 1
        else:
            # Ensure the key exists so group_take_up has the same key-set.
            group_take_up.setdefault(label, 0)

    # If no rows had a non-null value, mark as unavailable (Req 5.5).
    if not group_counts:
        return {
            "attribute": attribute,
            "available": False,
            "items": [],
            "unavailable_reason": (
                f"Atribut '{attribute}' tidak tersedia untuk campaign ini."
            ),
        }

    # Compute overall percentage share across groups (must sum to 100).
    try:
        percentages = compute_distribution_percentages(group_counts)
    except ValueError:
        # Total is 0 — shouldn't happen given the guard above, but be safe.
        return {
            "attribute": attribute,
            "available": False,
            "items": [],
            "unavailable_reason": (
                f"Tidak dapat menghitung distribusi untuk atribut '{attribute}'."
            ),
        }

    # Compute per-group take_up_percentage (take_up_count / group_total × 100).
    items: list[dict[str, Any]] = []
    for label, count in group_counts.items():
        take_up_count = group_take_up.get(label, 0)
        take_up_pct = (
            round((take_up_count / count) * 100, 4) if count > 0 else 0.0
        )
        items.append(
            {
                "label": label,
                "count": count,
                "percentage": percentages[label],
                "take_up_count": take_up_count,
                "take_up_percentage": take_up_pct,
            }
        )

    # Sort items by count descending for consistent presentation.
    items.sort(key=lambda x: x["count"], reverse=True)

    return {
        "attribute": attribute,
        "available": True,
        "items": items,
        "unavailable_reason": None,
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for Customer Criteria Analysis endpoint.

    ``GET /api/campaigns/customer-criteria/{campaign_id}``

    Parses the ``campaign_id`` path parameter, executes an Athena query
    for the raw lead rows of that campaign, then computes per-attribute
    distributions comparing take-up vs non-take-up groups.

    Args:
        event: API Gateway Lambda proxy event dict.  Must contain
            ``pathParameters.campaign_id``.
        context: Lambda context object (unused).

    Returns:
        API Gateway Lambda proxy response dict.  On success the body
        contains::

            {
                "campaign_id": "<id>",
                "distributions": [
                    {
                        "attribute": "customer_segment",
                        "available": true,
                        "items": [
                            {
                                "label": "MASS",
                                "count": 120,
                                "percentage": 40.0,
                                "take_up_count": 30,
                                "take_up_percentage": 25.0
                            },
                            ...
                        ],
                        "unavailable_reason": null
                    },
                    ...
                ],
                "available_attributes": [...],
                "unavailable_attributes": [...]
            }
    """
    # ------------------------------------------------------------------
    # 1. Extract campaign_id path parameter (Req 5.1)
    # ------------------------------------------------------------------
    path_params: dict[str, str] = event.get("pathParameters") or {}
    campaign_id: str | None = path_params.get("campaign_id")

    if not campaign_id or not campaign_id.strip():
        return _error(400, "Parameter 'campaign_id' wajib diisi.")

    campaign_id = campaign_id.strip()

    # ------------------------------------------------------------------
    # 2. Create Athena client from environment variables
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
    # 3. Build and execute customer criteria query
    # ------------------------------------------------------------------
    sql = athena.build_customer_criteria_query(campaign_id)

    try:
        rows = athena.execute_query(sql)
    except QueryTimeoutError as exc:
        return _error(
            408,
            f"Query Athena melewati batas waktu ({exc.timeout_seconds} detik). "
            "Coba kembali beberapa saat lagi.",
        )
    except QueryExecutionError as exc:
        return _error(
            500,
            f"Query Athena gagal dengan status {exc.state!r}: {exc.reason}",
        )

    # ------------------------------------------------------------------
    # 4. Handle empty results (Req 5.5)
    # ------------------------------------------------------------------
    if not rows:
        return _ok(
            {
                "campaign_id": campaign_id,
                "message": (
                    "Tidak ada data karakteristik nasabah untuk campaign ini."
                ),
            }
        )

    # ------------------------------------------------------------------
    # 5. Strip PII from all rows before processing (Req 7.5)
    # ------------------------------------------------------------------
    safe_rows: list[dict[str, Any]] = strip_pii(rows)  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # 6. Build per-attribute distributions (Req 5.1–5.4)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 7. Build and return response
    # ------------------------------------------------------------------
    response_body: dict[str, Any] = {
        "campaign_id": campaign_id,
        "distributions": distributions,
        "available_attributes": available_attributes,
        "unavailable_attributes": unavailable_attributes,
    }

    # Partial-data message when some attributes are unavailable (Req 5.5).
    if unavailable_attributes:
        response_body["partial_data_message"] = (
            f"Atribut berikut tidak tersedia untuk campaign ini: "
            f"{', '.join(unavailable_attributes)}."
        )

    return _ok(response_body)
