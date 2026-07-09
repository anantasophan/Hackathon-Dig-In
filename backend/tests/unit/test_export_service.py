"""Unit tests for the Export Service Lambda handler.

Tests cover request parsing, format validation, file generation helpers,
timeout detection, S3 upload/presigned-URL flow, and error paths.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from lambdas.export_service.handler import (
    _error,
    _filter_summary,
    _generate_csv,
    _ok,
    lambda_handler,
)
from shared.models import ActiveFilter, ExportRequest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_BASE_PAYLOAD: dict = {
    "page": "campaign_overview",
    "format": "csv",
    "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
    "time_range_start": "2024-01-01",
    "time_range_end": "2024-03-31",
}


def _event(payload: dict | None = None, body: str | None = None) -> dict:
    """Build a minimal API Gateway proxy event.

    Args:
        payload: Dict to be serialised as the JSON body.
        body: Raw body string (takes precedence over *payload*).

    Returns:
        API Gateway proxy event dict.
    """
    if body is not None:
        return {"body": body}
    return {"body": json.dumps(payload or _BASE_PAYLOAD)}


# ---------------------------------------------------------------------------
# _ok / _error helpers
# ---------------------------------------------------------------------------


class TestResponseHelpers:
    def test_ok_returns_200(self) -> None:
        resp = _ok({"foo": "bar"})
        assert resp["statusCode"] == 200

    def test_ok_body_is_json(self) -> None:
        resp = _ok({"key": "value"})
        body = json.loads(resp["body"])
        assert body == {"key": "value"}

    def test_error_status_code(self) -> None:
        resp = _error(400, "bad request")
        assert resp["statusCode"] == 400

    def test_error_body_contains_message(self) -> None:
        resp = _error(500, "something broke")
        body = json.loads(resp["body"])
        assert body["message"] == "something broke"

    def test_headers_present(self) -> None:
        resp = _ok({})
        assert resp["headers"]["Content-Type"] == "application/json"
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


# ---------------------------------------------------------------------------
# _filter_summary
# ---------------------------------------------------------------------------


class TestFilterSummary:
    def test_empty_filters(self) -> None:
        assert _filter_summary([]) == "none"

    def test_single_filter(self) -> None:
        f = ActiveFilter(field="flag_program", values=["PROGRAM QRIS"])
        result = _filter_summary([f])
        assert "flag_program=PROGRAM QRIS" in result

    def test_multiple_filters(self) -> None:
        filters = [
            ActiveFilter(field="flag_program", values=["PROGRAM QRIS"]),
            ActiveFilter(field="wilayah", values=["1", "2"]),
        ]
        result = _filter_summary(filters)
        assert "flag_program=PROGRAM QRIS" in result
        assert "wilayah=1,2" in result

    def test_multiple_values_joined_by_comma(self) -> None:
        f = ActiveFilter(field="media_blasting", values=["wa", "sms", "email"])
        result = _filter_summary([f])
        assert "wa,sms,email" in result


# ---------------------------------------------------------------------------
# _generate_csv
# ---------------------------------------------------------------------------


class TestGenerateCsv:
    def _make_request(self) -> ExportRequest:
        return ExportRequest(
            page="campaign_overview",
            format="csv",
            filters=[ActiveFilter(field="flag_program", values=["PROGRAM QRIS"])],
            time_range_start="2024-01-01",
            time_range_end="2024-03-31",
        )

    def test_returns_bytes(self) -> None:
        data = _generate_csv(self._make_request())
        assert isinstance(data, bytes)

    def test_metadata_comment_at_top(self) -> None:
        data = _generate_csv(self._make_request())
        text = data.decode("utf-8")
        first_line = text.splitlines()[0]
        assert first_line.startswith("#")
        assert "campaign_overview" in first_line
        assert "2024-01-01" in first_line
        assert "2024-03-31" in first_line

    def test_contains_filter_in_comment(self) -> None:
        data = _generate_csv(self._make_request())
        text = data.decode("utf-8")
        assert "flag_program" in text

    def test_header_row_present(self) -> None:
        data = _generate_csv(self._make_request())
        text = data.decode("utf-8")
        assert "nama_program" in text
        assert "take_up_rate" in text

    def test_no_filters(self) -> None:
        req = ExportRequest(
            page="regional",
            format="csv",
            filters=[],
            time_range_start="2024-01-01",
            time_range_end="2024-01-31",
        )
        data = _generate_csv(req)
        text = data.decode("utf-8")
        assert "Filters: none" in text


# ---------------------------------------------------------------------------
# lambda_handler — request validation
# ---------------------------------------------------------------------------


class TestLambdaHandlerValidation:
    def test_missing_body(self) -> None:
        resp = lambda_handler({"body": None}, None)
        assert resp["statusCode"] == 400
        assert "body" in json.loads(resp["body"])["message"].lower()

    def test_invalid_json(self) -> None:
        resp = lambda_handler({"body": "not-json"}, None)
        assert resp["statusCode"] == 400

    def test_missing_required_field(self) -> None:
        bad_payload = {
            "format": "csv",
            "filters": [],
            "time_range_start": "2024-01-01",
            "time_range_end": "2024-03-31",
            # "page" intentionally missing
        }
        resp = lambda_handler(_event(bad_payload), None)
        assert resp["statusCode"] == 400

    def test_invalid_format(self) -> None:
        payload = {**_BASE_PAYLOAD, "format": "docx"}
        resp = lambda_handler(_event(payload), None)
        assert resp["statusCode"] == 400
        assert "docx" in json.loads(resp["body"])["message"]

    def test_empty_body_string(self) -> None:
        resp = lambda_handler({"body": ""}, None)
        assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# lambda_handler — successful CSV export (mocked S3)
# ---------------------------------------------------------------------------


class TestLambdaHandlerCsvSuccess:
    def _make_mock_s3(self) -> MagicMock:
        s3_mock = MagicMock()
        s3_mock.put_object.return_value = {}
        s3_mock.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/campaign-exports/test.csv?presigned=1"
        )
        return s3_mock

    @patch("lambdas.export_service.handler.boto3")
    def test_returns_200_on_success(self, mock_boto3: MagicMock) -> None:
        mock_boto3.client.return_value = self._make_mock_s3()
        resp = lambda_handler(_event(), None)
        assert resp["statusCode"] == 200

    @patch("lambdas.export_service.handler.boto3")
    def test_response_contains_download_url(self, mock_boto3: MagicMock) -> None:
        mock_boto3.client.return_value = self._make_mock_s3()
        resp = lambda_handler(_event(), None)
        body = json.loads(resp["body"])
        assert "download_url" in body
        assert body["download_url"].startswith("https://")

    @patch("lambdas.export_service.handler.boto3")
    def test_response_status_completed(self, mock_boto3: MagicMock) -> None:
        mock_boto3.client.return_value = self._make_mock_s3()
        resp = lambda_handler(_event(), None)
        body = json.loads(resp["body"])
        assert body["status"] == "completed"

    @patch("lambdas.export_service.handler.boto3")
    def test_presigned_url_ttl_is_900(self, mock_boto3: MagicMock) -> None:
        """Presigned URL must be requested with 900-second TTL (15 minutes)."""
        s3_mock = self._make_mock_s3()
        mock_boto3.client.return_value = s3_mock
        lambda_handler(_event(), None)
        _, kwargs = s3_mock.generate_presigned_url.call_args
        assert kwargs.get("ExpiresIn") == 900

    @patch("lambdas.export_service.handler.boto3")
    def test_s3_key_uses_uuid_and_correct_ext(self, mock_boto3: MagicMock) -> None:
        s3_mock = self._make_mock_s3()
        mock_boto3.client.return_value = s3_mock
        lambda_handler(_event(), None)
        _, put_kwargs = s3_mock.put_object.call_args
        key: str = put_kwargs["Key"]
        assert key.endswith(".csv")
        # UUID part: 8-4-4-4-12 hex chars before extension
        uuid_part = key[: -len(".csv")]
        assert len(uuid_part) == 36  # standard UUID4 string length


# ---------------------------------------------------------------------------
# lambda_handler — Excel and PDF formats
# ---------------------------------------------------------------------------


class TestLambdaHandlerExcelPdf:
    def _make_mock_s3(self) -> MagicMock:
        s3_mock = MagicMock()
        s3_mock.put_object.return_value = {}
        s3_mock.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/campaign-exports/test.xlsx?presigned=1"
        )
        return s3_mock

    @patch("lambdas.export_service.handler.boto3")
    def test_excel_format_returns_200(self, mock_boto3: MagicMock) -> None:
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            pytest.skip("openpyxl not installed")
        mock_boto3.client.return_value = self._make_mock_s3()
        payload = {**_BASE_PAYLOAD, "format": "excel"}
        resp = lambda_handler(_event(payload), None)
        assert resp["statusCode"] == 200

    @patch("lambdas.export_service.handler.boto3")
    def test_excel_s3_key_has_xlsx_ext(self, mock_boto3: MagicMock) -> None:
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            pytest.skip("openpyxl not installed")
        s3_mock = self._make_mock_s3()
        mock_boto3.client.return_value = s3_mock
        payload = {**_BASE_PAYLOAD, "format": "excel"}
        lambda_handler(_event(payload), None)
        _, put_kwargs = s3_mock.put_object.call_args
        assert put_kwargs["Key"].endswith(".xlsx")

    @patch("lambdas.export_service.handler.boto3")
    def test_pdf_format_returns_200(self, mock_boto3: MagicMock) -> None:
        try:
            from reportlab.platypus import SimpleDocTemplate  # noqa: F401
        except ImportError:
            pytest.skip("reportlab not installed")
        mock_boto3.client.return_value = self._make_mock_s3()
        payload = {**_BASE_PAYLOAD, "format": "pdf"}
        resp = lambda_handler(_event(payload), None)
        assert resp["statusCode"] == 200

    @patch("lambdas.export_service.handler.boto3")
    def test_missing_openpyxl_returns_500(self, mock_boto3: MagicMock) -> None:
        mock_boto3.client.return_value = self._make_mock_s3()
        payload = {**_BASE_PAYLOAD, "format": "excel"}
        with patch(
            "lambdas.export_service.handler._generate_excel",
            side_effect=ImportError("Export format requires additional dependencies"),
        ):
            resp = lambda_handler(_event(payload), None)
        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert "additional dependencies" in body["message"]

    @patch("lambdas.export_service.handler.boto3")
    def test_missing_reportlab_returns_500(self, mock_boto3: MagicMock) -> None:
        mock_boto3.client.return_value = self._make_mock_s3()
        payload = {**_BASE_PAYLOAD, "format": "pdf"}
        with patch(
            "lambdas.export_service.handler._generate_pdf",
            side_effect=ImportError("Export format requires additional dependencies"),
        ):
            resp = lambda_handler(_event(payload), None)
        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert "additional dependencies" in body["message"]


# ---------------------------------------------------------------------------
# lambda_handler — S3 failure and cleanup (Req 8.5)
# ---------------------------------------------------------------------------


class TestLambdaHandlerS3Failure:
    @patch("lambdas.export_service.handler.boto3")
    def test_s3_put_failure_returns_500(self, mock_boto3: MagicMock) -> None:
        from botocore.exceptions import ClientError

        s3_mock = MagicMock()
        s3_mock.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "bucket not found"}},
            "PutObject",
        )
        mock_boto3.client.return_value = s3_mock
        resp = lambda_handler(_event(), None)
        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert "upload" in body["message"].lower() or "s3" in body["message"].lower()

    @patch("lambdas.export_service.handler.boto3")
    def test_presigned_url_failure_returns_500(self, mock_boto3: MagicMock) -> None:
        from botocore.exceptions import ClientError

        s3_mock = MagicMock()
        s3_mock.put_object.return_value = {}
        s3_mock.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "access denied"}},
            "GeneratePresignedUrl",
        )
        mock_boto3.client.return_value = s3_mock
        resp = lambda_handler(_event(), None)
        assert resp["statusCode"] == 500

    @patch("lambdas.export_service.handler.boto3")
    def test_presigned_url_failure_triggers_cleanup(self, mock_boto3: MagicMock) -> None:
        """S3 object must be deleted when presigned URL generation fails."""
        from botocore.exceptions import ClientError

        s3_mock = MagicMock()
        s3_mock.put_object.return_value = {}
        s3_mock.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "access denied"}},
            "GeneratePresignedUrl",
        )
        mock_boto3.client.return_value = s3_mock
        lambda_handler(_event(), None)
        s3_mock.delete_object.assert_called_once()


# ---------------------------------------------------------------------------
# lambda_handler — timeout (Req 8.4)
# ---------------------------------------------------------------------------


class TestLambdaHandlerTimeout:
    @patch("lambdas.export_service.handler.boto3")
    @patch("lambdas.export_service.handler.time")
    def test_timeout_after_generation_returns_408(
        self, mock_time: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """When generation takes >30 s, a 408 timeout should be returned."""
        # monotonic() returns 0 on first call, 31 on subsequent calls
        mock_time.monotonic.side_effect = [0.0, 31.0, 31.0, 31.0]
        mock_boto3.client.return_value = MagicMock()
        resp = lambda_handler(_event(), None)
        assert resp["statusCode"] == 408
        body = json.loads(resp["body"])
        assert body["status"] == "timeout"

    @patch("lambdas.export_service.handler.boto3")
    @patch("lambdas.export_service.handler.time")
    def test_timeout_after_upload_cleans_up_s3(
        self, mock_time: MagicMock, mock_boto3: MagicMock
    ) -> None:
        """When the timeout is detected after S3 upload, the object is deleted."""
        # First call: start_time; second call: post-generation check (ok);
        # third call: post-upload check (timed out)
        mock_time.monotonic.side_effect = [0.0, 1.0, 31.0, 31.0]
        s3_mock = MagicMock()
        s3_mock.put_object.return_value = {}
        mock_boto3.client.return_value = s3_mock
        resp = lambda_handler(_event(), None)
        assert resp["statusCode"] == 408
        s3_mock.delete_object.assert_called_once()
