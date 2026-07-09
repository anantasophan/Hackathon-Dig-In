"""Unit tests for the Similar Campaign Lambda handler.

Tests cover request parsing, dimension validation, DynamoDB result filtering,
sorting, limit enforcement, learning summary formatting, and empty-result
handling.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lambdas.similar_campaign.handler import (
    _build_learning_summary,
    _to_float,
    _to_int,
    lambda_handler,
)
from shared.models import SimilarCampaignResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_event(body: Any) -> dict:
    """Build a minimal API Gateway proxy event with a JSON body."""
    return {"body": json.dumps(body) if body is not None else None}


def _make_item(
    similar_campaign_id: str,
    matching_dimensions: list[str],
    dimension_count: int = None,
    take_up_rate: float = 10.0,
    similarity_score: float = 0.8,
    total_leads: int = 100,
    total_take_up: int = 10,
    campaign_name: str = "Test Campaign",
) -> dict[str, Any]:
    """Build a mock DynamoDB item dict (using Decimal for numbers)."""
    return {
        "similar_campaign_id": similar_campaign_id,
        "campaign_name": campaign_name,
        "matching_dimensions": matching_dimensions,
        "dimension_count": Decimal(
            str(dimension_count if dimension_count is not None else len(matching_dimensions))
        ),
        "similarity_score": Decimal(str(similarity_score)),
        "take_up_rate": Decimal(str(take_up_rate)),
        "total_leads": Decimal(str(total_leads)),
        "total_take_up": Decimal(str(total_take_up)),
    }


def _patch_dynamo(items: list[dict]) -> MagicMock:
    """Return a mock DynamoDB Table whose query() returns *items*."""
    mock_table = MagicMock()
    mock_table.query.return_value = {"Items": items}
    return mock_table


# ---------------------------------------------------------------------------
# _to_float / _to_int helpers
# ---------------------------------------------------------------------------


class TestConversionHelpers:
    def test_to_float_decimal(self):
        assert _to_float(Decimal("18.75")) == pytest.approx(18.75)

    def test_to_float_int(self):
        assert _to_float(100) == pytest.approx(100.0)

    def test_to_float_string(self):
        assert _to_float("12.5") == pytest.approx(12.5)

    def test_to_float_none(self):
        assert _to_float(None) == pytest.approx(0.0)

    def test_to_int_decimal(self):
        assert _to_int(Decimal("3")) == 3

    def test_to_int_string(self):
        assert _to_int("7") == 7

    def test_to_int_none(self):
        assert _to_int(None) == 0


# ---------------------------------------------------------------------------
# _build_learning_summary
# ---------------------------------------------------------------------------


class TestBuildLearningSummary:
    def test_formats_take_up_rate_two_decimals(self):
        result = SimilarCampaignResult(
            campaign_id="c1",
            campaign_name="Camp",
            matching_dimensions=["media_blasting"],
            dimension_count=1,
            similarity_score=0.9,
            take_up_rate=18.75,
            total_leads=100,
            total_take_up=18,
        )
        summary = _build_learning_summary(result)
        assert summary["take_up_rate_formatted"] == "18.75%"

    def test_rounds_take_up_rate(self):
        result = SimilarCampaignResult(
            campaign_id="c1",
            campaign_name="Camp",
            matching_dimensions=["flag_program"],
            dimension_count=1,
            similarity_score=0.8,
            take_up_rate=5.123456,
            total_leads=100,
            total_take_up=5,
        )
        summary = _build_learning_summary(result)
        assert summary["take_up_rate_formatted"] == "5.12%"

    def test_top_segment_is_na(self):
        result = SimilarCampaignResult("c1", "Camp", [], 0, 0.0, 0.0, 0, 0)
        summary = _build_learning_summary(result)
        assert summary["top_segment"] == "N/A"

    def test_top_region_is_na(self):
        result = SimilarCampaignResult("c1", "Camp", [], 0, 0.0, 0.0, 0, 0)
        summary = _build_learning_summary(result)
        assert summary["top_region"] == "N/A"


# ---------------------------------------------------------------------------
# lambda_handler — input validation
# ---------------------------------------------------------------------------


class TestLambdaHandlerInputValidation:
    def test_missing_body_returns_400(self):
        resp = lambda_handler({"body": None}, None)
        assert resp["statusCode"] == 400
        assert "required" in json.loads(resp["body"])["error"].lower()

    def test_invalid_json_returns_400(self):
        resp = lambda_handler({"body": "not json"}, None)
        assert resp["statusCode"] == 400

    def test_missing_reference_campaign_id_returns_400(self):
        resp = lambda_handler(_make_event({"dimensions": ["media_blasting"]}), None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "reference_campaign_id" in body["error"]

    def test_empty_reference_campaign_id_returns_400(self):
        resp = lambda_handler(
            _make_event({"reference_campaign_id": "  ", "dimensions": ["media_blasting"]}),
            None,
        )
        assert resp["statusCode"] == 400

    def test_missing_dimensions_returns_400(self):
        resp = lambda_handler(
            _make_event({"reference_campaign_id": "C001"}), None
        )
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "dimensions" in body["error"]

    def test_empty_dimensions_returns_400(self):
        resp = lambda_handler(
            _make_event({"reference_campaign_id": "C001", "dimensions": []}), None
        )
        assert resp["statusCode"] == 400

    def test_invalid_dimension_returns_400(self):
        resp = lambda_handler(
            _make_event({
                "reference_campaign_id": "C001",
                "dimensions": ["invalid_dim"],
            }),
            None,
        )
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "invalid_dim" in body["error"]

    def test_partially_invalid_dimensions_returns_400(self):
        resp = lambda_handler(
            _make_event({
                "reference_campaign_id": "C001",
                "dimensions": ["media_blasting", "bad_dimension"],
            }),
            None,
        )
        assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# lambda_handler — successful responses
# ---------------------------------------------------------------------------


class TestLambdaHandlerSuccess:
    def test_no_similar_campaigns_returns_200_with_message(self):
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo([])

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting"],
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["similar_campaigns"] == []
        assert "Tidak ada campaign serupa ditemukan" in body["message"]
        assert "perluas dimensi" in body["message"]

    def test_returns_matching_campaigns_sorted(self):
        """Results should be sorted dimension_count desc, take_up_rate desc."""
        items = [
            _make_item("C002", ["media_blasting"], take_up_rate=10.0),
            _make_item("C003", ["media_blasting", "flag_program"], take_up_rate=5.0),
            _make_item("C004", ["media_blasting"], take_up_rate=20.0),
        ]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting"],
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        ids = [c["campaign_id"] for c in body["similar_campaigns"]]
        # C003 has 2 dimensions → first; then C004 (rate 20) > C002 (rate 10)
        assert ids == ["C003", "C004", "C002"]

    def test_dimension_filter_excludes_non_matching(self):
        """Items that don't include ALL requested dimensions are excluded."""
        items = [
            _make_item("C002", ["media_blasting"]),
            _make_item("C003", ["media_blasting", "flag_program"]),
        ]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting", "flag_program"],
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        ids = [c["campaign_id"] for c in body["similar_campaigns"]]
        # Only C003 has BOTH media_blasting AND flag_program
        assert ids == ["C003"]

    def test_limit_applied_max_20(self):
        """More than 20 results must be capped at 20."""
        items = [
            _make_item(f"C{i:03d}", ["media_blasting"], take_up_rate=float(i))
            for i in range(30)
        ]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting"],
                    "limit": 30,  # requesting 30 but max is 20
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert len(body["similar_campaigns"]) == 20

    def test_limit_below_20_is_respected(self):
        """A limit of 5 should return at most 5 results."""
        items = [
            _make_item(f"C{i:03d}", ["media_blasting"])
            for i in range(10)
        ]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting"],
                    "limit": 5,
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert len(body["similar_campaigns"]) <= 5

    def test_learning_summary_present_when_results_found(self):
        """Response includes learning_summary when there is at least one result."""
        items = [_make_item("C002", ["flag_program"], take_up_rate=15.5)]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["flag_program"],
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "learning_summary" in body
        assert body["learning_summary"]["take_up_rate_formatted"] == "15.50%"
        assert body["learning_summary"]["top_segment"] == "N/A"
        assert body["learning_summary"]["top_region"] == "N/A"

    def test_no_learning_summary_when_empty(self):
        """Empty result returns message but no learning_summary key."""
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo([])

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["jenis_leads"],
                }),
                None,
            )

        body = json.loads(resp["body"])
        assert "learning_summary" not in body

    def test_valid_all_three_dimensions(self):
        """All three valid dimensions are accepted without a 400 error."""
        items = [
            _make_item(
                "C002",
                ["media_blasting", "jenis_leads", "flag_program"],
                dimension_count=3,
            )
        ]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting", "jenis_leads", "flag_program"],
                }),
                None,
            )

        assert resp["statusCode"] == 200

    def test_pagination_collects_all_items(self):
        """Handler should follow LastEvaluatedKey to collect all DynamoDB pages."""
        page1_items = [_make_item("C002", ["media_blasting"])]
        page2_items = [_make_item("C003", ["media_blasting"])]

        mock_table = MagicMock()
        mock_table.query.side_effect = [
            {"Items": page1_items, "LastEvaluatedKey": {"campaign_id": "C001", "similar_campaign_id": "C002"}},
            {"Items": page2_items},
        ]

        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = mock_table

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting"],
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert len(body["similar_campaigns"]) == 2

    def test_response_structure(self):
        """Response body must contain similar_campaigns list and learning_summary."""
        items = [_make_item("C002", ["media_blasting", "jenis_leads"], take_up_rate=8.33)]
        with patch("lambdas.similar_campaign.handler.boto3") as mock_boto3:
            mock_resource = MagicMock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = _patch_dynamo(items)

            resp = lambda_handler(
                _make_event({
                    "reference_campaign_id": "C001",
                    "dimensions": ["media_blasting"],
                }),
                None,
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "similar_campaigns" in body
        assert isinstance(body["similar_campaigns"], list)
        campaign = body["similar_campaigns"][0]
        for field in (
            "campaign_id",
            "campaign_name",
            "matching_dimensions",
            "dimension_count",
            "similarity_score",
            "take_up_rate",
            "total_leads",
            "total_take_up",
        ):
            assert field in campaign, f"Missing field: {field}"
