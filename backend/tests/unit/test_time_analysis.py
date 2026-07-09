"""Unit tests for the time_analysis Lambda handler.

Tests cover path parameter extraction, optional query filters,
histogram binning, statistics, and empty-state responses.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lambdas.time_analysis.handler import _build_histogram, lambda_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    campaign_id: str | None = "C001",
    channel: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Build a minimal API Gateway proxy event."""
    path_params: dict[str, str] | None = (
        {"campaign_id": campaign_id} if campaign_id is not None else None
    )
    query_params: dict[str, str] = {}
    if channel is not None:
        query_params["channel"] = channel
    if region is not None:
        query_params["region"] = region

    return {
        "pathParameters": path_params,
        "queryStringParameters": query_params or None,
    }


def _body(response: dict[str, Any]) -> dict[str, Any]:
    return json.loads(response["body"])


# ---------------------------------------------------------------------------
# _build_histogram unit tests
# ---------------------------------------------------------------------------


class TestBuildHistogram:
    """Tests for the internal _build_histogram helper."""

    def test_all_bins_present(self):
        """Histogram always returns exactly 7 bins regardless of input."""
        hist = _build_histogram([1, 10, 20, 35, 50, 75, 100])
        assert len(hist) == 7

    def test_bin_ranges(self):
        """Bin boundaries match the specification."""
        hist = _build_histogram([0])
        edges = [(b["range_start"], b["range_end"]) for b in hist]
        assert edges == [
            (0, 7),
            (7, 14),
            (14, 21),
            (21, 30),
            (30, 60),
            (60, 90),
            (90, None),
        ]

    def test_last_bin_open_ended(self):
        """Values >= 90 fall into the last open-ended bin."""
        hist = _build_histogram([90, 100, 200])
        last_bin = hist[-1]
        assert last_bin["count"] == 3
        assert last_bin["range_end"] is None

    def test_value_at_boundary_goes_to_upper_bin(self):
        """A value exactly at a boundary goes into the UPPER bin (range_start <= x < range_end)."""
        hist = _build_histogram([7])
        # 7 should be in [7, 14), not [0, 7)
        assert hist[0]["count"] == 0  # [0, 7)
        assert hist[1]["count"] == 1  # [7, 14)

    def test_percentage_sums_to_100(self):
        """Percentages across all bins sum to 100 (may have float rounding)."""
        hist = _build_histogram(list(range(1, 101)))
        total_pct = sum(b["percentage"] for b in hist)
        assert abs(total_pct - 100.0) < 0.1

    def test_single_value(self):
        """Single-item list produces 100% in the appropriate bin."""
        hist = _build_histogram([5])
        assert hist[0]["count"] == 1
        assert hist[0]["percentage"] == 100.0
        for b in hist[1:]:
            assert b["count"] == 0
            assert b["percentage"] == 0.0

    def test_counts_are_correct(self):
        """Counts correctly reflect how many values fall in each bin."""
        # 3 values in [0,7), 2 in [7,14), 1 in [90, ∞)
        days = [0, 1, 6, 7, 13, 95]
        hist = _build_histogram(days)
        assert hist[0]["count"] == 3
        assert hist[1]["count"] == 2
        assert hist[-1]["count"] == 1


# ---------------------------------------------------------------------------
# lambda_handler: input validation
# ---------------------------------------------------------------------------


class TestLambdaHandlerValidation:
    """Tests for path parameter and input validation."""

    def test_missing_campaign_id_returns_400(self):
        event = _make_event(campaign_id=None)
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        assert "campaign_id" in _body(response)["error"]

    def test_empty_path_parameters_returns_400(self):
        event = {"pathParameters": {}, "queryStringParameters": None}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_null_path_parameters_returns_400(self):
        event = {"pathParameters": None, "queryStringParameters": None}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400


# ---------------------------------------------------------------------------
# lambda_handler: Athena error handling
# ---------------------------------------------------------------------------


class TestLambdaHandlerAthenaErrors:
    """Tests for Athena timeout and execution error handling."""

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_query_timeout_returns_408(self, mock_client_cls):
        from shared.athena_client import QueryTimeoutError

        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.side_effect = QueryTimeoutError("qid-1", 30)

        response = lambda_handler(_make_event(), None)
        assert response["statusCode"] == 408

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_query_execution_error_returns_500(self, mock_client_cls):
        from shared.athena_client import QueryExecutionError

        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.side_effect = QueryExecutionError(
            "qid-2", "FAILED", "Syntax error"
        )

        response = lambda_handler(_make_event(), None)
        assert response["statusCode"] == 500


# ---------------------------------------------------------------------------
# lambda_handler: empty states
# ---------------------------------------------------------------------------


class TestLambdaHandlerEmptyStates:
    """Tests for empty-data responses (requirement 3.5, 3.6)."""

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_no_rows_returns_200_with_empty_message(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = []

        response = lambda_handler(_make_event("C001"), None)
        assert response["statusCode"] == 200
        body = _body(response)
        assert "message" in body
        assert body["campaign_id"] == "C001"
        assert "histogram" not in body

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_channel_filter_no_match_returns_empty_message(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = [
            {
                "channel": "sms",
                "region": "1",
                "time_to_take_up_days": "10",
            }
        ]

        response = lambda_handler(_make_event("C001", channel="email"), None)
        assert response["statusCode"] == 200
        assert "message" in _body(response)

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_all_null_days_returns_empty_message(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = [
            {"channel": "sms", "region": "1", "time_to_take_up_days": None},
            {"channel": "sms", "region": "1", "time_to_take_up_days": ""},
        ]

        response = lambda_handler(_make_event("C001"), None)
        assert response["statusCode"] == 200
        assert "message" in _body(response)


# ---------------------------------------------------------------------------
# lambda_handler: successful response
# ---------------------------------------------------------------------------


class TestLambdaHandlerSuccess:
    """Tests for successful histogram + stats responses (requirements 3.1, 3.2)."""

    _ROWS = [
        {"channel": "sms", "region": "1", "time_to_take_up_days": "3"},
        {"channel": "sms", "region": "1", "time_to_take_up_days": "10"},
        {"channel": "sms", "region": "2", "time_to_take_up_days": "25"},
        {"channel": "email", "region": "1", "time_to_take_up_days": "5"},
        {"channel": "sms", "region": "1", "time_to_take_up_days": "100"},
    ]

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_response_structure(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = self._ROWS

        response = lambda_handler(_make_event("C001"), None)
        assert response["statusCode"] == 200
        body = _body(response)

        assert body["campaign_id"] == "C001"
        assert "histogram" in body
        assert "stats" in body
        assert body["channel_filter"] is None
        assert body["region_filter"] is None

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_histogram_has_7_bins(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = self._ROWS

        body = _body(lambda_handler(_make_event("C001"), None))
        assert len(body["histogram"]) == 7

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_stats_keys_present(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = self._ROWS

        body = _body(lambda_handler(_make_event("C001"), None))
        stats = body["stats"]
        assert "min_days" in stats
        assert "max_days" in stats
        assert "mean_days" in stats
        assert "median_days" in stats
        assert "total_take_up" in stats

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_stats_values_correct(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        # days: [3, 10, 25, 5, 100]
        instance.execute_query.return_value = self._ROWS

        body = _body(lambda_handler(_make_event("C001"), None))
        stats = body["stats"]
        assert stats["min_days"] == 3
        assert stats["max_days"] == 100
        assert stats["total_take_up"] == 5

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_channel_filter_applied(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = self._ROWS

        # Only 1 row has channel == "email" (day=5)
        body = _body(lambda_handler(_make_event("C001", channel="email"), None))
        assert body["stats"]["total_take_up"] == 1
        assert body["stats"]["min_days"] == 5
        assert body["channel_filter"] == "email"

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_region_filter_applied(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = self._ROWS

        # Rows with region "2": day=25
        body = _body(lambda_handler(_make_event("C001", region="2"), None))
        assert body["stats"]["total_take_up"] == 1
        assert body["stats"]["min_days"] == 25
        assert body["region_filter"] == "2"

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_null_days_are_skipped(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = [
            {"channel": "sms", "region": "1", "time_to_take_up_days": "5"},
            {"channel": "sms", "region": "1", "time_to_take_up_days": None},
            {"channel": "sms", "region": "1", "time_to_take_up_days": ""},
        ]

        body = _body(lambda_handler(_make_event("C001"), None))
        # Only the valid "5" row is counted
        assert body["stats"]["total_take_up"] == 1
        assert body["stats"]["min_days"] == 5

    @patch.dict(
        "os.environ",
        {
            "ATHENA_DATABASE": "testdb",
            "ATHENA_OUTPUT_LOCATION": "s3://bucket/results/",
        },
    )
    @patch("lambdas.time_analysis.handler.AthenaClient")
    def test_campaign_id_echoed_in_response(self, mock_client_cls):
        instance = mock_client_cls.return_value
        instance.build_time_analysis_query.return_value = "SELECT ..."
        instance.execute_query.return_value = [
            {"channel": "sms", "region": "1", "time_to_take_up_days": "7"}
        ]

        body = _body(lambda_handler(_make_event("CAMP-XYZ"), None))
        assert body["campaign_id"] == "CAMP-XYZ"
