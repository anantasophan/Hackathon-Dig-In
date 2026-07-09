"""Unit tests for backend/lambdas/campaign_overview/handler.py.

Tests cover request parsing, aggregation helpers, active-filter building,
and the full lambda_handler response for the main branches:
  - valid request with data
  - empty results (200 + message)
  - query timeout (408)
  - query execution error (500)
  - invalid date format (400)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from lambdas.campaign_overview.handler import (
    _aggregate_rows,
    _build_active_filters,
    _build_trend,
    _parse_request,
    lambda_handler,
)
from shared.models import ActiveFilter, CampaignOverviewRequest


# ---------------------------------------------------------------------------
# _parse_request
# ---------------------------------------------------------------------------


class TestParseRequest:
    """Tests for _parse_request()."""

    def test_defaults_when_no_params(self) -> None:
        """Empty params produce today and 90 days ago as defaults."""
        req = _parse_request({})
        today = date.today()
        expected_start = (today - timedelta(days=90)).isoformat()
        assert req.end_date == today.isoformat()
        assert req.start_date == expected_start

    def test_explicit_dates_accepted(self) -> None:
        req = _parse_request({"start_date": "2024-01-01", "end_date": "2024-03-31"})
        assert req.start_date == "2024-01-01"
        assert req.end_date == "2024-03-31"

    def test_invalid_date_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _parse_request({"start_date": "01-01-2024"})

    def test_comma_separated_flag_program(self) -> None:
        req = _parse_request({"flag_program": "PROGRAM QRIS,PROGRAM BIAYA ADMIN"})
        assert req.flag_program == ["PROGRAM QRIS", "PROGRAM BIAYA ADMIN"]

    def test_comma_separated_wilayah_as_ints(self) -> None:
        req = _parse_request({"wilayah": "1,3,7"})
        assert req.wilayah == [1, 3, 7]

    def test_wilayah_non_integer_tokens_skipped(self) -> None:
        req = _parse_request({"wilayah": "1,abc,5"})
        assert req.wilayah == [1, 5]

    def test_missing_optional_params_are_none(self) -> None:
        req = _parse_request({})
        assert req.flag_program is None
        assert req.media_blasting is None
        assert req.wilayah is None
        assert req.jenis_leads is None

    def test_empty_string_param_treated_as_none(self) -> None:
        req = _parse_request({"flag_program": ""})
        assert req.flag_program is None

    def test_jenis_leads_and_media_blasting_parsed(self) -> None:
        req = _parse_request({"media_blasting": "wa,sms", "jenis_leads": "Migrasi"})
        assert req.media_blasting == ["wa", "sms"]
        assert req.jenis_leads == ["Migrasi"]


# ---------------------------------------------------------------------------
# _build_active_filters
# ---------------------------------------------------------------------------


class TestBuildActiveFilters:
    """Tests for _build_active_filters()."""

    def _make_request(self, **kwargs) -> CampaignOverviewRequest:
        defaults = {
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "flag_program": None,
            "media_blasting": None,
            "wilayah": None,
            "jenis_leads": None,
        }
        defaults.update(kwargs)
        return CampaignOverviewRequest(**defaults)

    def test_period_filter_always_present(self) -> None:
        req = self._make_request()
        filters = _build_active_filters(req)
        fields = [f.field for f in filters]
        assert "period" in fields

    def test_no_optional_filters_when_none(self) -> None:
        req = self._make_request()
        filters = _build_active_filters(req)
        fields = [f.field for f in filters]
        assert "flag_program" not in fields
        assert "media_blasting" not in fields
        assert "wilayah" not in fields
        assert "jenis_leads" not in fields

    def test_flag_program_filter_added(self) -> None:
        req = self._make_request(flag_program=["PROGRAM QRIS"])
        filters = _build_active_filters(req)
        fp = next(f for f in filters if f.field == "flag_program")
        assert fp.values == ["PROGRAM QRIS"]

    def test_wilayah_values_serialised_as_strings(self) -> None:
        req = self._make_request(wilayah=[1, 5, 12])
        filters = _build_active_filters(req)
        wf = next(f for f in filters if f.field == "wilayah")
        assert wf.values == ["1", "5", "12"]

    def test_all_optional_filters_added(self) -> None:
        req = self._make_request(
            flag_program=["PROGRAM QRIS"],
            media_blasting=["wa"],
            wilayah=[3],
            jenis_leads=["Migrasi"],
        )
        filters = _build_active_filters(req)
        fields = {f.field for f in filters}
        assert {"period", "flag_program", "media_blasting", "wilayah", "jenis_leads"} == fields


# ---------------------------------------------------------------------------
# _aggregate_rows
# ---------------------------------------------------------------------------


class TestAggregateRows:
    """Tests for _aggregate_rows()."""

    def test_sums_correctly(self) -> None:
        rows = [
            {"total_leads": "100", "total_take_up": "10", "campaign_count": "2"},
            {"total_leads": "200", "total_take_up": "30", "campaign_count": "3"},
        ]
        leads, take_up, campaigns = _aggregate_rows(rows)
        assert leads == 300
        assert take_up == 40
        assert campaigns == 5

    def test_empty_rows_returns_zeros(self) -> None:
        assert _aggregate_rows([]) == (0, 0, 0)

    def test_missing_fields_treated_as_zero(self) -> None:
        rows = [{"total_leads": "50"}]
        leads, take_up, campaigns = _aggregate_rows(rows)
        assert leads == 50
        assert take_up == 0
        assert campaigns == 0

    def test_none_values_treated_as_zero(self) -> None:
        rows = [{"total_leads": None, "total_take_up": None, "campaign_count": None}]
        leads, take_up, campaigns = _aggregate_rows(rows)
        assert leads == 0
        assert take_up == 0
        assert campaigns == 0

    def test_unparseable_row_skipped(self) -> None:
        rows = [
            {"total_leads": "bad", "total_take_up": "bad", "campaign_count": "bad"},
            {"total_leads": "50", "total_take_up": "5", "campaign_count": "1"},
        ]
        leads, take_up, campaigns = _aggregate_rows(rows)
        assert leads == 50
        assert take_up == 5
        assert campaigns == 1


# ---------------------------------------------------------------------------
# _build_trend
# ---------------------------------------------------------------------------


class TestBuildTrend:
    """Tests for _build_trend()."""

    def test_converts_rows_to_trend_points(self) -> None:
        rows = [
            {
                "period_start": "2024-01-01",
                "period_end": "2024-01-07",
                "total_leads": "100",
                "total_take_up": "10",
                "take_up_rate": "10.0",
            }
        ]
        trend = _build_trend(rows)
        assert len(trend) == 1
        pt = trend[0]
        assert pt.period_start == "2024-01-01"
        assert pt.period_end == "2024-01-07"
        assert pt.total_leads == 100
        assert pt.total_take_up == 10
        assert pt.take_up_rate == 10.0

    def test_empty_rows_returns_empty_list(self) -> None:
        assert _build_trend([]) == []

    def test_falls_back_to_calculated_rate_when_missing(self) -> None:
        rows = [
            {
                "period_start": "2024-01-01",
                "period_end": "2024-01-07",
                "total_leads": "200",
                "total_take_up": "50",
                "take_up_rate": None,
            }
        ]
        trend = _build_trend(rows)
        assert trend[0].take_up_rate == 25.0

    def test_zero_leads_period_gets_zero_rate(self) -> None:
        rows = [
            {
                "period_start": "2024-02-01",
                "period_end": "2024-02-07",
                "total_leads": "0",
                "total_take_up": "0",
                "take_up_rate": None,
            }
        ]
        trend = _build_trend(rows)
        assert trend[0].take_up_rate == 0.0

    def test_preserves_order(self) -> None:
        rows = [
            {
                "period_start": "2024-01-01",
                "period_end": "2024-01-07",
                "total_leads": "10",
                "total_take_up": "1",
                "take_up_rate": "10.0",
            },
            {
                "period_start": "2024-01-08",
                "period_end": "2024-01-14",
                "total_leads": "20",
                "total_take_up": "4",
                "take_up_rate": "20.0",
            },
        ]
        trend = _build_trend(rows)
        assert trend[0].period_start == "2024-01-01"
        assert trend[1].period_start == "2024-01-08"


# ---------------------------------------------------------------------------
# lambda_handler integration tests (mocked Athena)
# ---------------------------------------------------------------------------


_SAMPLE_ROWS = [
    {
        "period_start": "2024-01-01",
        "period_end": "2024-01-07",
        "granularity": "weekly",
        "product": "PROGRAM QRIS",
        "channel": "wa",
        "region": "1",
        "total_leads": "200",
        "total_take_up": "20",
        "take_up_rate": "10.0",
        "total_transaction_value": "500000",
        "campaign_count": "3",
    },
    {
        "period_start": "2024-01-08",
        "period_end": "2024-01-14",
        "granularity": "weekly",
        "product": "PROGRAM QRIS",
        "channel": "wa",
        "region": "1",
        "total_leads": "300",
        "total_take_up": "45",
        "take_up_rate": "15.0",
        "total_transaction_value": "750000",
        "campaign_count": "2",
    },
]


@pytest.fixture()
def mock_athena_rows(monkeypatch) -> None:
    """Monkeypatch AthenaClient.execute_query to return _SAMPLE_ROWS."""
    monkeypatch.setenv("ATHENA_DATABASE", "test_db")
    monkeypatch.setenv("ATHENA_S3_OUTPUT", "s3://bucket/output")
    monkeypatch.setenv("ATHENA_WORKGROUP", "primary")

    with patch(
        "lambdas.campaign_overview.handler.AthenaClient"
    ) as MockClient:
        instance = MockClient.return_value
        instance.build_campaign_overview_query.return_value = "SELECT ..."
        instance.execute_query.return_value = _SAMPLE_ROWS
        yield instance


class TestLambdaHandler:
    """End-to-end tests for lambda_handler()."""

    def _event(self, params: dict | None = None) -> dict:
        return {"queryStringParameters": params or {}}

    def test_200_with_valid_data(self, mock_athena_rows) -> None:
        resp = lambda_handler(self._event({"start_date": "2024-01-01", "end_date": "2024-01-31"}), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["total_leads"] == 500
        assert body["total_take_up"] == 65
        assert body["total_campaigns"] == 5
        assert "trend" in body
        assert len(body["trend"]) == 2

    def test_take_up_rate_calculated_correctly(self, mock_athena_rows) -> None:
        resp = lambda_handler(self._event({"start_date": "2024-01-01", "end_date": "2024-01-31"}), None)
        body = json.loads(resp["body"])
        # 65 / 500 * 100 = 13.0
        assert body["take_up_rate"] == 13.0

    def test_filters_present_in_response(self, mock_athena_rows) -> None:
        resp = lambda_handler(
            self._event({"start_date": "2024-01-01", "end_date": "2024-01-31", "media_blasting": "wa"}),
            None,
        )
        body = json.loads(resp["body"])
        filter_fields = {f["field"] for f in body["filters"]}
        assert "media_blasting" in filter_fields

    def test_cors_header_present(self, mock_athena_rows) -> None:
        resp = lambda_handler(self._event(), None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_none_query_params_uses_defaults(self, mock_athena_rows) -> None:
        resp = lambda_handler({"queryStringParameters": None}, None)
        assert resp["statusCode"] == 200

    def test_missing_query_params_key_uses_defaults(self, mock_athena_rows) -> None:
        resp = lambda_handler({}, None)
        assert resp["statusCode"] == 200

    def test_400_on_invalid_date(self, monkeypatch) -> None:
        monkeypatch.setenv("ATHENA_DATABASE", "test_db")
        monkeypatch.setenv("ATHENA_S3_OUTPUT", "s3://bucket/output")
        resp = lambda_handler(self._event({"start_date": "31-01-2024"}), None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "tanggal" in body["message"]

    def test_408_on_query_timeout(self, monkeypatch) -> None:
        from shared.athena_client import QueryTimeoutError

        monkeypatch.setenv("ATHENA_DATABASE", "test_db")
        monkeypatch.setenv("ATHENA_S3_OUTPUT", "s3://bucket/output")

        with patch("lambdas.campaign_overview.handler.AthenaClient") as MockClient:
            instance = MockClient.return_value
            instance.build_campaign_overview_query.return_value = "SELECT ..."
            instance.execute_query.side_effect = QueryTimeoutError("exec-123", 30)

            resp = lambda_handler(
                self._event({"start_date": "2024-01-01", "end_date": "2024-01-31"}), None
            )

        assert resp["statusCode"] == 408
        body = json.loads(resp["body"])
        assert "filters" in body

    def test_500_on_query_execution_error(self, monkeypatch) -> None:
        from shared.athena_client import QueryExecutionError

        monkeypatch.setenv("ATHENA_DATABASE", "test_db")
        monkeypatch.setenv("ATHENA_S3_OUTPUT", "s3://bucket/output")

        with patch("lambdas.campaign_overview.handler.AthenaClient") as MockClient:
            instance = MockClient.return_value
            instance.build_campaign_overview_query.return_value = "SELECT ..."
            instance.execute_query.side_effect = QueryExecutionError("exec-456", "FAILED", "syntax error")

            resp = lambda_handler(
                self._event({"start_date": "2024-01-01", "end_date": "2024-01-31"}), None
            )

        assert resp["statusCode"] == 500

    def test_200_empty_data_returns_message(self, monkeypatch) -> None:
        monkeypatch.setenv("ATHENA_DATABASE", "test_db")
        monkeypatch.setenv("ATHENA_S3_OUTPUT", "s3://bucket/output")

        with patch("lambdas.campaign_overview.handler.AthenaClient") as MockClient:
            instance = MockClient.return_value
            instance.build_campaign_overview_query.return_value = "SELECT ..."
            instance.execute_query.return_value = []

            resp = lambda_handler(
                self._event({"start_date": "2024-01-01", "end_date": "2024-01-31"}), None
            )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "message" in body
        assert "Tidak ada data" in body["message"]
        assert "filters" in body

    def test_pii_stripped_from_response(self, mock_athena_rows) -> None:
        """PII fields must not appear anywhere in the response body."""
        resp = lambda_handler(self._event({"start_date": "2024-01-01", "end_date": "2024-01-31"}), None)
        body_str = resp["body"]
        # None of the PII field names should appear as keys
        for pii_field in ("cif", "nama_lengkap", "nomor_rekening", "nomor_identitas", "alamat_lengkap"):
            assert f'"{pii_field}"' not in body_str
