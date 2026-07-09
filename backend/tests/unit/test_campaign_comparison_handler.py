"""Unit tests for the Campaign Comparison Lambda handler.

Tests cover: request validation, empty results, metric building,
group_by sorting, chart construction, and error responses.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

import json
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from lambdas.campaign_comparison.handler import lambda_handler, _build_chart, _response
from shared.models import CampaignMetric


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(body: object | None = None, raw: str | None = None) -> dict:
    """Build a minimal API Gateway proxy event."""
    if raw is not None:
        return {"body": raw}
    if body is None:
        return {}
    return {"body": json.dumps(body)}


_SAMPLE_ROWS = [
    {
        "campaign_id": "C001",
        "campaign_name": "QRIS Cashback",
        "total_leads": "200",
        "total_take_up": "40",
        "take_up_rate": "20.0",
        "total_transaction_value": "5000000.0",
        "duration_days": "30",
    },
    {
        "campaign_id": "C002",
        "campaign_name": "Admin Fee Promo",
        "total_leads": "100",
        "total_take_up": "15",
        "take_up_rate": "15.0",
        "total_transaction_value": "2500000.0",
        "duration_days": "14",
    },
]


# ---------------------------------------------------------------------------
# 1. Request parsing and validation
# ---------------------------------------------------------------------------


class TestRequestParsing:
    def test_missing_body_returns_400(self):
        resp = lambda_handler({}, None)
        assert resp["statusCode"] == 400
        assert "body" in json.loads(resp["body"])["error"].lower() or "required" in json.loads(resp["body"])["error"].lower()

    def test_invalid_json_body_returns_400(self):
        resp = lambda_handler(_make_event(raw="not-json"), None)
        assert resp["statusCode"] == 400
        assert "json" in json.loads(resp["body"])["error"].lower()

    def test_too_few_campaign_ids_returns_400(self):
        with patch("lambdas.campaign_comparison.handler.AthenaClient"):
            resp = lambda_handler(_make_event({"campaign_ids": ["C001"]}), None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "error" in body

    def test_too_many_campaign_ids_returns_400(self):
        with patch("lambdas.campaign_comparison.handler.AthenaClient"):
            resp = lambda_handler(
                _make_event({"campaign_ids": ["C1", "C2", "C3", "C4", "C5", "C6"]}),
                None,
            )
        assert resp["statusCode"] == 400

    def test_exactly_two_ids_is_valid(self):
        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.return_value = _SAMPLE_ROWS
            MockAthena.return_value = mock_client

            resp = lambda_handler(
                _make_event({"campaign_ids": ["C001", "C002"]}), None
            )
        assert resp["statusCode"] == 200

    def test_exactly_five_ids_is_valid(self):
        five_rows = [dict(r, campaign_id=f"C00{i}") for i, r in
                     enumerate(_SAMPLE_ROWS * 3, 1)][:5]
        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.return_value = five_rows
            MockAthena.return_value = mock_client

            resp = lambda_handler(
                _make_event({"campaign_ids": ["C1", "C2", "C3", "C4", "C5"]}), None
            )
        assert resp["statusCode"] == 200


# ---------------------------------------------------------------------------
# 2. Empty result handling
# ---------------------------------------------------------------------------


class TestEmptyResults:
    def test_empty_results_returns_200_with_message(self):
        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.return_value = []
            MockAthena.return_value = mock_client

            resp = lambda_handler(
                _make_event({"campaign_ids": ["C001", "C002"]}), None
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["campaigns"] == []
        assert "message" in body


# ---------------------------------------------------------------------------
# 3. Metric construction
# ---------------------------------------------------------------------------


class TestMetricConstruction:
    def _run(self, rows: list[dict], group_by: str | None = None) -> dict:
        payload: dict = {"campaign_ids": ["C001", "C002"]}
        if group_by:
            payload["group_by"] = group_by

        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.return_value = rows
            MockAthena.return_value = mock_client
            resp = lambda_handler(_make_event(payload), None)

        assert resp["statusCode"] == 200
        return json.loads(resp["body"])

    def test_campaign_count_matches_rows(self):
        body = self._run(_SAMPLE_ROWS)
        assert len(body["campaigns"]) == 2

    def test_take_up_rate_recalculated(self):
        """Handler must recalculate take_up_rate, not trust the query value."""
        body = self._run(_SAMPLE_ROWS)
        c001 = next(c for c in body["campaigns"] if c["campaign_id"] == "C001")
        # 40 / 200 * 100 = 20.0
        assert c001["take_up_rate"] == pytest.approx(20.0)

    def test_zero_leads_take_up_rate_is_zero(self):
        rows = [
            {
                "campaign_id": "C001",
                "campaign_name": "Camp A",
                "total_leads": "0",
                "total_take_up": "0",
                "take_up_rate": "0.0",
                "total_transaction_value": "0.0",
                "duration_days": "7",
            },
            {
                "campaign_id": "C002",
                "campaign_name": "Camp B",
                "total_leads": "50",
                "total_take_up": "5",
                "take_up_rate": "10.0",
                "total_transaction_value": "1000.0",
                "duration_days": "7",
            },
        ]
        body = self._run(rows)
        c001 = next(c for c in body["campaigns"] if c["campaign_id"] == "C001")
        assert c001["take_up_rate"] == 0.0

    def test_numeric_fields_are_correct_types(self):
        body = self._run(_SAMPLE_ROWS)
        campaign = body["campaigns"][0]
        assert isinstance(campaign["total_leads"], int)
        assert isinstance(campaign["total_take_up"], int)
        assert isinstance(campaign["duration_days"], int)
        assert isinstance(campaign["take_up_rate"], float)
        assert isinstance(campaign["total_transaction_value"], float)

    def test_duration_days_from_query(self):
        body = self._run(_SAMPLE_ROWS)
        c001 = next(c for c in body["campaigns"] if c["campaign_id"] == "C001")
        assert c001["duration_days"] == 30


# ---------------------------------------------------------------------------
# 4. group_by sorting
# ---------------------------------------------------------------------------


class TestGroupBySorting:
    _ROWS_WITH_FLAG = [
        {
            "campaign_id": "C002",
            "campaign_name": "Admin Fee",
            "flag_program": "PROGRAM BIAYA ADMIN",
            "total_leads": "100",
            "total_take_up": "10",
            "take_up_rate": "10.0",
            "total_transaction_value": "1000.0",
            "duration_days": "14",
        },
        {
            "campaign_id": "C001",
            "campaign_name": "QRIS Cashback",
            "flag_program": "PROGRAM QRIS",
            "total_leads": "200",
            "total_take_up": "40",
            "take_up_rate": "20.0",
            "total_transaction_value": "5000.0",
            "duration_days": "30",
        },
    ]

    def _run(self, rows: list[dict], group_by: str) -> dict:
        payload = {"campaign_ids": ["C001", "C002"], "group_by": group_by}
        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.return_value = rows
            MockAthena.return_value = mock_client
            resp = lambda_handler(_make_event(payload), None)
        assert resp["statusCode"] == 200
        return json.loads(resp["body"])

    def test_group_by_flag_program_sorts_ascending(self):
        body = self._run(self._ROWS_WITH_FLAG, "flag_program")
        names = [c["flag_program"] for c in body["campaigns"]]
        assert names == sorted(names)

    def test_group_by_none_preserves_query_order(self):
        """Without group_by, campaigns appear in the order returned by Athena."""
        payload = {"campaign_ids": ["C001", "C002"]}
        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.return_value = _SAMPLE_ROWS
            MockAthena.return_value = mock_client
            resp = lambda_handler(_make_event(payload), None)
        body = json.loads(resp["body"])
        assert body["campaigns"][0]["campaign_id"] == "C001"
        assert body["campaigns"][1]["campaign_id"] == "C002"


# ---------------------------------------------------------------------------
# 5. Chart construction
# ---------------------------------------------------------------------------


class TestBuildChart:
    _METRICS = [
        CampaignMetric("C001", "Camp A", "PROGRAM QRIS", 200, 40, 20.0, 5000.0, 30),
        CampaignMetric("C002", "Camp B", "PROGRAM BIAYA ADMIN", 100, 10, 10.0, 2000.0, 14),
    ]

    def test_labels_match_campaign_names(self):
        chart = _build_chart(self._METRICS)
        assert chart["labels"] == ["Camp A", "Camp B"]

    def test_five_datasets_present(self):
        chart = _build_chart(self._METRICS)
        assert len(chart["datasets"]) == 5

    def test_dataset_labels(self):
        chart = _build_chart(self._METRICS)
        dataset_labels = [d["label"] for d in chart["datasets"]]
        assert "Total Leads" in dataset_labels
        assert "Total Take Up" in dataset_labels
        assert "Take Up Rate (%)" in dataset_labels
        assert "Nilai Transaksi" in dataset_labels
        assert "Durasi (hari)" in dataset_labels

    def test_dataset_data_length_matches_campaigns(self):
        chart = _build_chart(self._METRICS)
        for dataset in chart["datasets"]:
            assert len(dataset["data"]) == len(self._METRICS)

    def test_total_leads_dataset_values(self):
        chart = _build_chart(self._METRICS)
        leads_data = next(d for d in chart["datasets"] if d["label"] == "Total Leads")
        assert leads_data["data"] == [200, 100]


# ---------------------------------------------------------------------------
# 6. Error response helpers
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_query_timeout_returns_408(self):
        from shared.athena_client import QueryTimeoutError

        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.side_effect = QueryTimeoutError("qid-1", 30)
            MockAthena.return_value = mock_client

            resp = lambda_handler(
                _make_event({"campaign_ids": ["C001", "C002"]}), None
            )

        assert resp["statusCode"] == 408
        body = json.loads(resp["body"])
        assert "error" in body

    def test_query_execution_error_returns_500(self):
        from shared.athena_client import QueryExecutionError

        with patch("lambdas.campaign_comparison.handler.AthenaClient") as MockAthena:
            mock_client = MagicMock()
            mock_client.build_comparison_query.return_value = "SELECT ..."
            mock_client.execute_query.side_effect = QueryExecutionError(
                "qid-2", "FAILED", "Syntax error"
            )
            MockAthena.return_value = mock_client

            resp = lambda_handler(
                _make_event({"campaign_ids": ["C001", "C002"]}), None
            )

        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert "error" in body

    def test_response_helper_structure(self):
        resp = _response(200, {"key": "value"})
        assert resp["statusCode"] == 200
        assert resp["headers"]["Content-Type"] == "application/json"
        assert json.loads(resp["body"]) == {"key": "value"}
