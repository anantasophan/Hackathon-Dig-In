"""Unit tests for the customer_criteria Lambda handler.

Tests cover:
- Missing / blank campaign_id → 400
- Athena timeout → 408
- Athena execution error → 500
- Empty result set → 200 with message
- Normal distribution computation
- Partially-available attributes (some all-null)
- PII stripping (cif field removed before processing)
- Percentage sums to 100 for every available attribute
- Take-up percentage calculation correctness
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lambdas.customer_criteria.handler import (
    _build_attribute_distribution,
    lambda_handler,
)
from shared.athena_client import QueryExecutionError, QueryTimeoutError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_ENV = {
    "ATHENA_DATABASE": "test_db",
    "ATHENA_S3_OUTPUT": "s3://bucket/out",
    "ATHENA_WORKGROUP": "primary",
}


def _event(campaign_id: str | None = "C001") -> dict[str, Any]:
    """Build a minimal API Gateway event with optional campaign_id."""
    return {
        "pathParameters": (
            {"campaign_id": campaign_id} if campaign_id is not None else {}
        )
    }


def _rows(n_total: int, n_take_up: int, segment: str = "MASS") -> list[dict[str, Any]]:
    """Generate simple mock rows where all rows share the same segment."""
    rows = []
    for i in range(n_total):
        rows.append(
            {
                "customer_segment": segment,
                "age_group": "GEN Y",
                "domicile_region": "JKT",
                "product_holding": "TABUNGAN",
                "balance_category": "LOW",
                "take_up_flag": "YES" if i < n_take_up else "NO",
                "transaction_value": "1000" if i < n_take_up else None,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 400 — missing / blank campaign_id
# ---------------------------------------------------------------------------


def test_missing_campaign_id_returns_400() -> None:
    """No pathParameters at all → 400."""
    resp = lambda_handler({"pathParameters": None}, None)
    assert resp["statusCode"] == 400
    assert "campaign_id" in resp["body"]


def test_empty_campaign_id_returns_400() -> None:
    """Empty string campaign_id → 400."""
    resp = lambda_handler(_event("  "), None)
    assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# 408 — query timeout
# ---------------------------------------------------------------------------


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_timeout_returns_408(MockAthena: MagicMock) -> None:
    """Athena QueryTimeoutError → 408."""
    instance = MockAthena.return_value
    instance.execute_query.side_effect = QueryTimeoutError("qid-123", 30)

    resp = lambda_handler(_event(), None)
    assert resp["statusCode"] == 408
    assert "batas waktu" in resp["body"]


# ---------------------------------------------------------------------------
# 500 — query execution error
# ---------------------------------------------------------------------------


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_execution_error_returns_500(MockAthena: MagicMock) -> None:
    """Athena QueryExecutionError → 500."""
    instance = MockAthena.return_value
    instance.execute_query.side_effect = QueryExecutionError("qid-456", "FAILED", "syntax error")

    resp = lambda_handler(_event(), None)
    assert resp["statusCode"] == 500
    assert "gagal" in resp["body"]


# ---------------------------------------------------------------------------
# 200 — empty result set
# ---------------------------------------------------------------------------


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_empty_rows_returns_200_with_message(MockAthena: MagicMock) -> None:
    """No rows from Athena → 200 with informative message."""
    instance = MockAthena.return_value
    instance.execute_query.return_value = []

    resp = lambda_handler(_event(), None)
    assert resp["statusCode"] == 200
    import json
    body = json.loads(resp["body"])
    assert "message" in body
    assert body.get("campaign_id") == "C001"


# ---------------------------------------------------------------------------
# 200 — normal distribution
# ---------------------------------------------------------------------------


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_normal_response_structure(MockAthena: MagicMock) -> None:
    """Happy path returns expected top-level structure."""
    import json

    instance = MockAthena.return_value
    instance.execute_query.return_value = _rows(10, 3)

    resp = lambda_handler(_event(), None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    assert body["campaign_id"] == "C001"
    assert "distributions" in body
    assert "available_attributes" in body
    assert "unavailable_attributes" in body


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_percentages_sum_to_100(MockAthena: MagicMock) -> None:
    """For every available attribute the item percentages must sum to 100.0."""
    import json

    rows = []
    segments = ["MASS", "AFFLUENT", "EMERALD"]
    for i, seg in enumerate(segments):
        for _ in range(i + 1):  # 1, 2, 3 rows per segment
            rows.append(
                {
                    "customer_segment": seg,
                    "age_group": "GEN Y",
                    "domicile_region": "JKT",
                    "product_holding": "TABUNGAN",
                    "balance_category": "LOW",
                    "take_up_flag": "YES",
                    "transaction_value": "500",
                }
            )

    instance = MockAthena.return_value
    instance.execute_query.return_value = rows

    resp = lambda_handler(_event(), None)
    body = json.loads(resp["body"])

    for dist in body["distributions"]:
        if dist["available"]:
            total_pct = sum(item["percentage"] for item in dist["items"])
            assert abs(total_pct - 100.0) < 0.01, (
                f"Percentages for '{dist['attribute']}' sum to {total_pct}, expected 100"
            )


# ---------------------------------------------------------------------------
# PII stripping
# ---------------------------------------------------------------------------


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_pii_cif_field_stripped(MockAthena: MagicMock) -> None:
    """cif field must never appear in the response body."""
    import json

    rows = _rows(5, 2)
    for row in rows:
        row["cif"] = "CUSTOMER_CIF_001"  # inject PII

    instance = MockAthena.return_value
    instance.execute_query.return_value = rows

    resp = lambda_handler(_event(), None)
    raw_body = resp["body"]
    assert "cif" not in raw_body
    assert "CUSTOMER_CIF_001" not in raw_body


# ---------------------------------------------------------------------------
# _build_attribute_distribution unit tests
# ---------------------------------------------------------------------------


def test_distribution_all_null_values_unavailable() -> None:
    """When all rows have null for the attribute → available=False."""
    rows = [
        {"customer_segment": None, "take_up_flag": "YES"},
        {"customer_segment": "", "take_up_flag": "NO"},
        {"customer_segment": None, "take_up_flag": "NO"},
    ]
    result = _build_attribute_distribution(rows, "customer_segment")
    assert result["available"] is False
    assert result["items"] == []
    assert result["unavailable_reason"] is not None


def test_distribution_mixed_null_skips_nulls() -> None:
    """Null rows are skipped; non-null rows are included in the distribution."""
    rows = [
        {"customer_segment": "MASS", "take_up_flag": "YES"},
        {"customer_segment": None, "take_up_flag": "NO"},
        {"customer_segment": "MASS", "take_up_flag": "NO"},
        {"customer_segment": "AFFLUENT", "take_up_flag": "YES"},
    ]
    result = _build_attribute_distribution(rows, "customer_segment")
    assert result["available"] is True
    labels = {item["label"] for item in result["items"]}
    assert labels == {"MASS", "AFFLUENT"}
    # None rows must not appear
    assert None not in labels


def test_distribution_take_up_counts_correct() -> None:
    """Take-up counts per group must match YES rows only."""
    rows = [
        {"customer_segment": "MASS", "take_up_flag": "YES"},
        {"customer_segment": "MASS", "take_up_flag": "YES"},
        {"customer_segment": "MASS", "take_up_flag": "NO"},
        {"customer_segment": "EMERALD", "take_up_flag": "NO"},
        {"customer_segment": "EMERALD", "take_up_flag": "NO"},
    ]
    result = _build_attribute_distribution(rows, "customer_segment")
    assert result["available"] is True

    items_by_label = {item["label"]: item for item in result["items"]}
    assert items_by_label["MASS"]["take_up_count"] == 2
    assert items_by_label["MASS"]["count"] == 3
    assert items_by_label["EMERALD"]["take_up_count"] == 0
    assert items_by_label["EMERALD"]["count"] == 2


def test_distribution_take_up_percentage_formula() -> None:
    """take_up_percentage = take_up_count / count × 100 (rounded to 4 dp)."""
    rows = [
        {"age_group": "GEN Y", "take_up_flag": "YES"},
        {"age_group": "GEN Y", "take_up_flag": "NO"},
        {"age_group": "GEN Y", "take_up_flag": "NO"},
        {"age_group": "GEN Y", "take_up_flag": "NO"},
    ]
    result = _build_attribute_distribution(rows, "age_group")
    assert result["available"] is True
    item = result["items"][0]
    # 1 / 4 × 100 = 25.0
    assert item["take_up_percentage"] == pytest.approx(25.0, abs=0.001)


def test_distribution_single_group_100_percent() -> None:
    """When only one group exists its percentage must be exactly 100.0."""
    rows = [
        {"balance_category": "HIGH", "take_up_flag": "YES"},
        {"balance_category": "HIGH", "take_up_flag": "YES"},
    ]
    result = _build_attribute_distribution(rows, "balance_category")
    assert result["available"] is True
    assert len(result["items"]) == 1
    assert result["items"][0]["percentage"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Partial availability (Req 5.5)
# ---------------------------------------------------------------------------


@patch.dict("os.environ", _BASE_ENV)
@patch("lambdas.customer_criteria.handler.AthenaClient")
def test_partial_attributes_reported(MockAthena: MagicMock) -> None:
    """When some attributes have all-null data they appear in unavailable_attributes."""
    import json

    rows = [
        {
            "customer_segment": "MASS",
            "age_group": None,  # unavailable
            "domicile_region": None,  # unavailable
            "product_holding": "TABUNGAN",
            "balance_category": "LOW",
            "take_up_flag": "YES",
            "transaction_value": "500",
        }
    ]

    instance = MockAthena.return_value
    instance.execute_query.return_value = rows

    resp = lambda_handler(_event(), None)
    body = json.loads(resp["body"])

    assert "age_group" in body["unavailable_attributes"]
    assert "domicile_region" in body["unavailable_attributes"]
    assert "customer_segment" in body["available_attributes"]
    assert "partial_data_message" in body
