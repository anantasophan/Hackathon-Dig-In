"""Unit tests for the Regional Performance Lambda handler.

Tests cover path-parameter extraction, product filtering, sorting,
8-week trend building, and empty-data handling.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lambdas.regional_performance.handler import _to_float, _to_int, lambda_handler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    campaign_id: str | None = "C001",
    flag_program: str | None = None,
    selected_region: str | None = None,
) -> dict[str, Any]:
    """Build a minimal API Gateway proxy event for the regional handler."""
    path_params: dict[str, str] = {}
    if campaign_id is not None:
        path_params["campaign_id"] = campaign_id

    query_params: dict[str, str] = {}
    if flag_program is not None:
        query_params["flag_program"] = flag_program
    if selected_region is not None:
        query_params["selected_region"] = selected_region

    return {
        "pathParameters": path_params if path_params else None,
        "queryStringParameters": query_params if query_params else None,
    }


def _parse_body(response: dict[str, Any]) -> dict[str, Any]:
    """Decode the JSON body from a Lambda response dict."""
    return json.loads(response["body"])


# Sample rows returned by the mocked AthenaClient
_SAMPLE_ROWS = [
    {
        "campaign_id": "C001",
        "region": "1",
        "leads_count": "200",
        "take_up_count": "40",
        "take_up_rate": "20.0",
        "avg_transaction_value": "500000.0",
    },
    {
        "campaign_id": "C001",
        "region": "2",
        "leads_count": "100",
        "take_up_count": "30",
        "take_up_rate": "30.0",
        "avg_transaction_value": "750000.0",
    },
    {
        "campaign_id": "C001",
        "region": "3",
        "leads_count": "150",
        "take_up_count": "15",
        "take_up_rate": "10.0",
        "avg_transaction_value": "300000.0",
    },
]


# ---------------------------------------------------------------------------
# Tests: input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Tests for path/query parameter validation."""

    def test_missing_campaign_id_returns_400(self) -> None:
        event = {"pathParameters": None, "queryStringParameters": None}
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 400
        body = _parse_body(resp)
        assert "campaign_id" in body["error"]

    def test_empty_path_params_returns_400(self) -> None:
        event = {"pathParameters": {}, "queryStringParameters": None}
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 400

    def test_invalid_selected_region_returns_400(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as _mock_cls:
            event = _make_event(selected_region="not_a_number")
            resp = lambda_handler(event, None)
        assert resp["statusCode"] == 400
        body = _parse_body(resp)
        assert "selected_region" in body["error"]


# ---------------------------------------------------------------------------
# Tests: empty data (Requirement 4.5)
# ---------------------------------------------------------------------------


class TestEmptyData:
    """Tests for the empty-data case (Requirement 4.5)."""

    def test_empty_rows_returns_200_with_message(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = []
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        assert resp["statusCode"] == 200
        body = _parse_body(resp)
        assert body["message"] == "Data regional tidak tersedia untuk campaign ini"
        assert body["regions"] == []
        assert body["selected_region_trend"] is None

    def test_empty_after_product_filter_returns_200_with_message(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            # Filter by a program that matches no row
            event = _make_event(flag_program="PROGRAM TIDAK ADA")
            resp = lambda_handler(event, None)

        assert resp["statusCode"] == 200
        body = _parse_body(resp)
        assert body["message"] == "Data regional tidak tersedia untuk campaign ini"
        assert body["regions"] == []


# ---------------------------------------------------------------------------
# Tests: sorting (Requirement 4.2)
# ---------------------------------------------------------------------------


class TestSorting:
    """Tests for descending take_up_rate ordering (Requirement 4.2)."""

    def test_regions_sorted_descending_by_take_up_rate(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        assert resp["statusCode"] == 200
        body = _parse_body(resp)
        rates = [r["take_up_rate"] for r in body["regions"]]
        assert rates == sorted(rates, reverse=True), (
            "Regions must be sorted by take_up_rate descending"
        )

    def test_first_region_has_highest_take_up_rate(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        body = _parse_body(resp)
        # From _SAMPLE_ROWS: region "2" has rate 30.0 — highest
        assert body["regions"][0]["take_up_rate"] == 30.0


# ---------------------------------------------------------------------------
# Tests: product filter (Requirement 4.4)
# ---------------------------------------------------------------------------


class TestProductFilter:
    """Tests for flag_program filtering (Requirement 4.4)."""

    def test_flag_program_filter_applied(self) -> None:
        rows_with_product = [
            {**row, "product": "PROGRAM QRIS"} for row in _SAMPLE_ROWS[:2]
        ] + [
            {**_SAMPLE_ROWS[2], "product": "PROGRAM BIAYA ADMIN"},
        ]

        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = rows_with_product
            mock_cls.return_value = mock_instance

            event = _make_event(flag_program="PROGRAM QRIS")
            resp = lambda_handler(event, None)

        assert resp["statusCode"] == 200
        body = _parse_body(resp)
        # Only rows with product == "PROGRAM QRIS" should remain (2 rows)
        assert len(body["regions"]) == 2

    def test_flag_program_filter_preserved_in_response(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            event = _make_event(flag_program="PROGRAM QRIS")
            resp = lambda_handler(event, None)

        body = _parse_body(resp)
        assert body["flag_program_filter"] == "PROGRAM QRIS"

    def test_no_filter_returns_all_regions(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        body = _parse_body(resp)
        assert len(body["regions"]) == len(_SAMPLE_ROWS)


# ---------------------------------------------------------------------------
# Tests: region dict structure (Requirement 4.1)
# ---------------------------------------------------------------------------


class TestRegionDict:
    """Tests that each region dict contains the required fields (Req 4.1)."""

    def test_region_dict_has_required_keys(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        body = _parse_body(resp)
        required_keys = {
            "wilayah",
            "leads_count",
            "take_up_count",
            "take_up_rate",
            "avg_transaction_value",
        }
        for region in body["regions"]:
            assert required_keys.issubset(region.keys()), (
                f"Missing keys in region dict: {required_keys - region.keys()}"
            )

    def test_campaign_id_in_response(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event("CAMP_42"), None)

        body = _parse_body(resp)
        assert body["campaign_id"] == "CAMP_42"


# ---------------------------------------------------------------------------
# Tests: 8-week trend (Requirement 4.3)
# ---------------------------------------------------------------------------


class TestSelectedRegionTrend:
    """Tests for 8-week trend when selected_region is provided (Req 4.3)."""

    def _make_weekly_rows(self, region: int, weeks: int = 10) -> list[dict]:
        """Generate weekly rows for a region with ``week_start`` column."""
        return [
            {
                "campaign_id": "C001",
                "region": str(region),
                "week_start": f"2024-0{(i % 9) + 1}-01",
                "leads_count": str(100 + i * 10),
                "take_up_count": str(10 + i),
                "take_up_rate": str(10.0 + i),
                "avg_transaction_value": "500000",
            }
            for i in range(weeks)
        ]

    def test_no_selected_region_trend_is_none(self) -> None:
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        body = _parse_body(resp)
        assert body["selected_region_trend"] is None

    def test_selected_region_trend_max_8_weeks(self) -> None:
        weekly_rows = self._make_weekly_rows(region=1, weeks=10)

        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = weekly_rows
            mock_cls.return_value = mock_instance

            event = _make_event(selected_region="1")
            resp = lambda_handler(event, None)

        body = _parse_body(resp)
        trend = body["selected_region_trend"]
        assert trend is not None
        assert len(trend) <= 8

    def test_selected_region_trend_points_have_required_keys(self) -> None:
        weekly_rows = self._make_weekly_rows(region=2, weeks=5)

        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = weekly_rows
            mock_cls.return_value = mock_instance

            event = _make_event(selected_region="2")
            resp = lambda_handler(event, None)

        body = _parse_body(resp)
        trend = body["selected_region_trend"]
        assert trend is not None
        required = {"week_start", "leads_count", "take_up_count", "take_up_rate"}
        for point in trend:
            assert required.issubset(point.keys())

    def test_selected_region_with_no_weekly_data_returns_empty_trend(self) -> None:
        # Rows without week_start (aggregated — no trend available)
        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.return_value = _SAMPLE_ROWS
            mock_cls.return_value = mock_instance

            event = _make_event(selected_region="1")
            resp = lambda_handler(event, None)

        body = _parse_body(resp)
        # _SAMPLE_ROWS have no week_start → trend should be empty list
        assert body["selected_region_trend"] == []


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for timeout and query execution errors."""

    def test_query_timeout_returns_408(self) -> None:
        from shared.athena_client import QueryTimeoutError

        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.side_effect = QueryTimeoutError(
                "exec-id-123", 30
            )
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        assert resp["statusCode"] == 408
        body = _parse_body(resp)
        assert "timed out" in body["error"].lower()

    def test_query_execution_error_returns_500(self) -> None:
        from shared.athena_client import QueryExecutionError

        with patch(
            "lambdas.regional_performance.handler.AthenaClient"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute_query.side_effect = QueryExecutionError(
                "exec-id-456", "FAILED", "Table not found"
            )
            mock_cls.return_value = mock_instance

            resp = lambda_handler(_make_event(), None)

        assert resp["statusCode"] == 500
        body = _parse_body(resp)
        assert "failed" in body["error"].lower()


# ---------------------------------------------------------------------------
# Tests: private helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for _to_int and _to_float utility functions."""

    def test_to_int_valid_string(self) -> None:
        assert _to_int("42") == 42

    def test_to_int_invalid_string_returns_zero(self) -> None:
        assert _to_int("abc") == 0

    def test_to_int_none_returns_zero(self) -> None:
        assert _to_int(None) == 0

    def test_to_float_valid_string(self) -> None:
        assert _to_float("3.14") == pytest.approx(3.14)

    def test_to_float_invalid_string_returns_zero(self) -> None:
        assert _to_float("xyz") == 0.0

    def test_to_float_none_returns_zero(self) -> None:
        assert _to_float(None) == 0.0
