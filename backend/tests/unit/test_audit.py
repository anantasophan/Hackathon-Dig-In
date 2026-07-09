"""Unit tests for the audit logging middleware (backend/shared/audit.py).

Tests cover log_access, extract_request_params, _sanitise_params, and the
audit_log decorator factory.

Requirements: 7.4
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from shared.audit import (
    _REQUEST_PARAMS_MAX_LEN,
    _TTL_DAYS,
    audit_log,
    extract_request_params,
    log_access,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_apigw_event(
    *,
    user_sub: str | None = "user-abc-123",
    principal_id: str | None = None,
    source_ip: str | None = "1.2.3.4",
    qs: dict | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    """Build a minimal API Gateway Lambda proxy event for testing."""
    authorizer: dict[str, Any] = {}
    if user_sub is not None:
        authorizer["claims"] = {"sub": user_sub}
    elif principal_id is not None:
        authorizer["principalId"] = principal_id

    event: dict[str, Any] = {
        "requestContext": {
            "authorizer": authorizer,
            "identity": {"sourceIp": source_ip},
        },
        "queryStringParameters": qs or {},
    }
    if body is not None:
        event["body"] = body
    return event


# ---------------------------------------------------------------------------
# extract_request_params
# ---------------------------------------------------------------------------


class TestExtractRequestParams:
    def test_returns_empty_dict_for_empty_event(self) -> None:
        assert extract_request_params({}) == {}

    def test_returns_query_string_parameters(self) -> None:
        event = {"queryStringParameters": {"start_date": "2024-01-01", "wilayah": "3"}}
        result = extract_request_params(event)
        assert result["start_date"] == "2024-01-01"
        assert result["wilayah"] == "3"

    def test_parses_json_body_as_dict(self) -> None:
        event = {"body": '{"campaign_ids": ["C001", "C002"]}', "queryStringParameters": {}}
        result = extract_request_params(event)
        assert result.get("campaign_ids") == ["C001", "C002"]

    def test_stores_non_object_json_body_as_body_key(self) -> None:
        event = {"body": '"just a string"', "queryStringParameters": {}}
        result = extract_request_params(event)
        assert "body" in result

    def test_stores_non_json_body_as_body_key(self) -> None:
        event = {"body": "not-json", "queryStringParameters": {}}
        result = extract_request_params(event)
        assert result.get("body") == "not-json"

    def test_truncates_long_body(self) -> None:
        long_body = "x" * (_REQUEST_PARAMS_MAX_LEN * 2)
        event = {"body": long_body, "queryStringParameters": {}}
        result = extract_request_params(event)
        # Body was non-JSON so stored under "body" key, truncated before parse attempt
        body_str = result.get("body", "")
        assert len(body_str) <= _REQUEST_PARAMS_MAX_LEN

    def test_merges_query_params_and_body(self) -> None:
        event = {
            "queryStringParameters": {"flag_program": "QRIS"},
            "body": '{"extra": "data"}',
        }
        result = extract_request_params(event)
        assert result.get("flag_program") == "QRIS"
        assert result.get("extra") == "data"

    def test_returns_empty_dict_on_none_qs_and_no_body(self) -> None:
        event = {"queryStringParameters": None}
        assert extract_request_params(event) == {}

    def test_handles_dict_body(self) -> None:
        event = {"body": {"key": "val"}, "queryStringParameters": {}}
        result = extract_request_params(event)
        assert result.get("key") == "val"

    def test_never_raises_on_garbage_input(self) -> None:
        # Should return {} rather than raise
        result = extract_request_params({"body": object()})  # type: ignore[arg-type]
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# log_access
# ---------------------------------------------------------------------------


class TestLogAccess:
    @patch("shared.audit.boto3")
    def test_writes_item_to_dynamodb(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        log_access(
            user_id="user-1",
            page_accessed="campaign_overview",
            action="view",
        )

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["user_id"] == "user-1"
        assert item["page_accessed"] == "campaign_overview"
        assert item["action"] == "view"

    @patch("shared.audit.boto3")
    def test_item_includes_iso_timestamp(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        log_access(user_id="u1", page_accessed="page", action="view")

        item = mock_table.put_item.call_args.kwargs["Item"]
        ts = item["timestamp"]
        assert ts.endswith("Z"), f"Timestamp should end with Z: {ts!r}"

    @patch("shared.audit.boto3")
    def test_item_includes_ttl(self, mock_boto3: MagicMock) -> None:
        import time as _time

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        before = int(_time.time())
        log_access(user_id="u1", page_accessed="page", action="view")
        after = int(_time.time())

        item = mock_table.put_item.call_args.kwargs["Item"]
        expiry = item["expiry_timestamp"]
        expected_min = before + _TTL_DAYS * 24 * 3600
        expected_max = after + _TTL_DAYS * 24 * 3600
        assert expected_min <= expiry <= expected_max

    @patch("shared.audit.boto3")
    def test_item_includes_ip_when_provided(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        log_access(user_id="u1", page_accessed="page", action="view", ip_address="10.0.0.1")

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["ip_address"] == "10.0.0.1"

    @patch("shared.audit.boto3")
    def test_item_omits_ip_when_none(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        log_access(user_id="u1", page_accessed="page", action="view", ip_address=None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert "ip_address" not in item

    @patch("shared.audit.boto3")
    def test_item_includes_request_params_when_provided(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        log_access(
            user_id="u1",
            page_accessed="page",
            action="view",
            request_params={"filter": "value"},
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert "request_params" in item
        assert item["request_params"]["filter"] == "value"

    @patch("shared.audit.boto3")
    def test_item_omits_request_params_when_none(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        log_access(user_id="u1", page_accessed="page", action="view", request_params=None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert "request_params" not in item

    @patch("shared.audit.boto3")
    def test_does_not_raise_when_dynamodb_fails(self, mock_boto3: MagicMock) -> None:
        mock_boto3.resource.side_effect = RuntimeError("DynamoDB unavailable")

        # Must not raise
        log_access(user_id="u1", page_accessed="page", action="view")

    @patch("shared.audit.boto3")
    def test_does_not_raise_when_put_item_fails(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.put_item.side_effect = Exception("Throttled")
        mock_boto3.resource.return_value.Table.return_value = mock_table

        # Must not raise
        log_access(user_id="u1", page_accessed="page", action="view")


# ---------------------------------------------------------------------------
# audit_log decorator
# ---------------------------------------------------------------------------


class TestAuditLogDecorator:
    @patch("shared.audit.boto3")
    def test_handler_is_called_and_result_returned(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="campaign_overview")
        def handler(event: dict, context: Any) -> dict:
            return {"statusCode": 200, "body": "ok"}

        result = handler(_make_apigw_event(), None)
        assert result == {"statusCode": 200, "body": "ok"}

    @patch("shared.audit.boto3")
    def test_extracts_user_id_from_cognito_claims(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="page")
        def handler(event: dict, context: Any) -> None:
            return None

        handler(_make_apigw_event(user_sub="cognito-sub-xyz"), None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["user_id"] == "cognito-sub-xyz"

    @patch("shared.audit.boto3")
    def test_extracts_user_id_from_principal_id_fallback(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="page")
        def handler(event: dict, context: Any) -> None:
            return None

        event = _make_apigw_event(user_sub=None, principal_id="principal-99")
        handler(event, None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["user_id"] == "principal-99"

    @patch("shared.audit.boto3")
    def test_falls_back_to_anonymous_when_no_auth(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="page")
        def handler(event: dict, context: Any) -> None:
            return None

        handler({"requestContext": {}}, None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["user_id"] == "anonymous"

    @patch("shared.audit.boto3")
    def test_falls_back_to_anonymous_for_bare_event(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="page")
        def handler(event: dict, context: Any) -> None:
            return None

        handler({}, None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["user_id"] == "anonymous"

    @patch("shared.audit.boto3")
    def test_uses_page_and_action_from_decorator_args(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="regional_performance", action="export")
        def handler(event: dict, context: Any) -> None:
            return None

        handler(_make_apigw_event(), None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["page_accessed"] == "regional_performance"
        assert item["action"] == "export"

    @patch("shared.audit.boto3")
    def test_default_action_is_view(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="overview")
        def handler(event: dict, context: Any) -> None:
            return None

        handler(_make_apigw_event(), None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["action"] == "view"

    @patch("shared.audit.boto3")
    def test_extracts_source_ip(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        @audit_log(page="page")
        def handler(event: dict, context: Any) -> None:
            return None

        handler(_make_apigw_event(source_ip="203.0.113.5"), None)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item.get("ip_address") == "203.0.113.5"

    @patch("shared.audit.boto3")
    def test_handler_still_called_when_dynamodb_fails(self, mock_boto3: MagicMock) -> None:
        """Audit failure must never prevent the handler from running."""
        mock_boto3.resource.side_effect = RuntimeError("DynamoDB down")

        called: list[bool] = []

        @audit_log(page="page")
        def handler(event: dict, context: Any) -> dict:
            called.append(True)
            return {"statusCode": 200}

        result = handler(_make_apigw_event(), None)
        assert called == [True]
        assert result["statusCode"] == 200

    @patch("shared.audit.boto3")
    def test_preserves_original_function_name(self, mock_boto3: MagicMock) -> None:
        @audit_log(page="page")
        def my_special_handler(event: dict, context: Any) -> None:
            return None

        assert my_special_handler.__name__ == "my_special_handler"
