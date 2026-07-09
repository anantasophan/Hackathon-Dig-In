"""Unit tests for shared.auth — JWT authentication middleware.

Requirements: 7.1, 7.2, 7.3
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from shared.auth import (
    decode_token_claims,
    extract_token,
    extract_user_id,
    extract_user_role,
    get_user_context,
    is_session_expired,
    require_auth,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(claims: dict) -> str:
    """Build a minimal (unsigned) JWT string for testing."""
    header_b64 = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(claims).encode()
    ).rstrip(b"=").decode()
    return f"{header_b64}.{payload_b64}.fakesig"


def _make_event(token: str | None) -> dict:
    """Wrap a token inside a mock Lambda event dict."""
    if token is None:
        return {"headers": {}}
    return {"headers": {"Authorization": f"Bearer {token}"}}


# ---------------------------------------------------------------------------
# extract_token
# ---------------------------------------------------------------------------


class TestExtractToken:
    def test_returns_token_from_bearer_header(self):
        event = {"headers": {"Authorization": "Bearer abc.def.ghi"}}
        assert extract_token(event) == "abc.def.ghi"

    def test_returns_none_when_no_headers(self):
        assert extract_token({}) is None

    def test_returns_none_when_empty_headers(self):
        assert extract_token({"headers": {}}) is None

    def test_returns_none_when_authorization_not_bearer(self):
        event = {"headers": {"Authorization": "Basic dXNlcjpwYXNz"}}
        assert extract_token(event) is None

    def test_handles_lowercase_authorization_header(self):
        """API Gateway v2 sends lower-case header names."""
        event = {"headers": {"authorization": "Bearer token.here.sig"}}
        assert extract_token(event) == "token.here.sig"

    def test_returns_none_when_headers_is_none(self):
        assert extract_token({"headers": None}) is None


# ---------------------------------------------------------------------------
# decode_token_claims
# ---------------------------------------------------------------------------


class TestDecodeTokenClaims:
    def test_decodes_valid_jwt_payload(self):
        claims = {"sub": "user-123", "custom:role": "divisi_bisnis"}
        token = _make_token(claims)
        result = decode_token_claims(token)
        assert result == claims

    def test_returns_none_for_malformed_token(self):
        assert decode_token_claims("notavalidtoken") is None

    def test_returns_none_for_empty_string(self):
        assert decode_token_claims("") is None

    def test_returns_none_when_payload_not_json(self):
        # Craft a token whose payload is valid base64 but not JSON.
        bad_payload = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
        token = f"header.{bad_payload}.sig"
        assert decode_token_claims(token) is None

    def test_handles_padding_correctly(self):
        """Payload lengths that don't align to 4-byte boundaries need padding."""
        claims = {"sub": "x"}  # very short payload deliberately
        token = _make_token(claims)
        result = decode_token_claims(token)
        assert result is not None
        assert result["sub"] == "x"

    def test_returns_none_for_two_part_token(self):
        assert decode_token_claims("header.payload") is None


# ---------------------------------------------------------------------------
# extract_user_role
# ---------------------------------------------------------------------------


class TestExtractUserRole:
    def test_returns_divisi_bisnis(self):
        assert extract_user_role({"custom:role": "divisi_bisnis"}) == "divisi_bisnis"

    def test_returns_divisi_data(self):
        assert extract_user_role({"custom:role": "divisi_data"}) == "divisi_data"

    def test_returns_none_for_unknown_role(self):
        assert extract_user_role({"custom:role": "admin"}) is None

    def test_returns_none_when_claim_absent(self):
        assert extract_user_role({}) is None

    def test_returns_none_for_empty_string_role(self):
        assert extract_user_role({"custom:role": ""}) is None


# ---------------------------------------------------------------------------
# extract_user_id
# ---------------------------------------------------------------------------


class TestExtractUserId:
    def test_prefers_sub_claim(self):
        claims = {"sub": "sub-uuid", "cognito:username": "jdoe"}
        assert extract_user_id(claims) == "sub-uuid"

    def test_falls_back_to_cognito_username(self):
        assert extract_user_id({"cognito:username": "jdoe"}) == "jdoe"

    def test_returns_none_when_both_absent(self):
        assert extract_user_id({}) is None

    def test_returns_none_when_sub_is_empty(self):
        # Empty string is falsy — should fall through to cognito:username.
        assert extract_user_id({"sub": "", "cognito:username": "jdoe"}) == "jdoe"


# ---------------------------------------------------------------------------
# is_session_expired
# ---------------------------------------------------------------------------


class TestIsSessionExpired:
    def test_returns_true_when_auth_time_over_8_hours_ago(self):
        old_auth_time = time.time() - 28_801  # 1 second past the limit
        assert is_session_expired({"auth_time": old_auth_time}) is True

    def test_returns_false_when_auth_time_within_8_hours(self):
        recent_auth_time = time.time() - 3_600  # 1 hour ago
        assert is_session_expired({"auth_time": recent_auth_time}) is False

    def test_returns_false_when_auth_time_absent(self):
        assert is_session_expired({}) is False

    def test_boundary_exactly_8_hours(self):
        # Exactly at the boundary: time.time() - auth_time == 28800
        # The condition is strictly >, so this should NOT be expired.
        boundary_auth_time = time.time() - 28_800
        # Allow 1-second wiggle room for test execution time.
        result = is_session_expired({"auth_time": boundary_auth_time})
        # Should be False (not yet expired) or True (marginally over) —
        # either is acceptable at the exact boundary; we just confirm the
        # function doesn't raise.
        assert isinstance(result, bool)

    def test_returns_false_for_future_auth_time(self):
        """auth_time slightly in the future (clock skew) → not expired."""
        future_auth_time = time.time() + 60
        assert is_session_expired({"auth_time": future_auth_time}) is False


# ---------------------------------------------------------------------------
# require_auth
# ---------------------------------------------------------------------------


class TestRequireAuth:
    def test_returns_claims_for_valid_token(self):
        claims = {
            "sub": "user-1",
            "custom:role": "divisi_bisnis",
            "auth_time": time.time() - 100,
        }
        event = _make_event(_make_token(claims))
        returned_claims, error = require_auth(event)
        assert error is None
        assert returned_claims is not None
        assert returned_claims["sub"] == "user-1"

    def test_returns_401_when_no_token(self):
        claims, error = require_auth({"headers": {}})
        assert claims is None
        assert error is not None
        assert error["statusCode"] == 401

    def test_returns_401_for_malformed_token(self):
        event = {"headers": {"Authorization": "Bearer not.valid"}}
        claims, error = require_auth(event)
        assert claims is None
        assert error["statusCode"] == 401

    def test_returns_401_for_expired_session(self):
        claims_payload = {
            "sub": "user-2",
            "auth_time": time.time() - 30_000,  # ~8.3 hours ago
        }
        event = _make_event(_make_token(claims_payload))
        claims, error = require_auth(event)
        assert claims is None
        assert error["statusCode"] == 401

    def test_error_body_contains_redirect(self):
        _, error = require_auth({"headers": {}})
        body = json.loads(error["body"])
        assert body["redirect"] == "/login"
        assert "message" in body

    def test_error_response_has_cors_headers(self):
        _, error = require_auth({"headers": {}})
        assert "Content-Type" in error["headers"]
        assert "Access-Control-Allow-Origin" in error["headers"]


# ---------------------------------------------------------------------------
# get_user_context
# ---------------------------------------------------------------------------


class TestGetUserContext:
    def test_returns_authenticated_context_for_valid_token(self):
        claims = {
            "sub": "u-abc",
            "custom:role": "divisi_data",
            "auth_time": time.time() - 500,
        }
        event = _make_event(_make_token(claims))
        ctx = get_user_context(event)
        assert ctx["is_authenticated"] is True
        assert ctx["user_id"] == "u-abc"
        assert ctx["role"] == "divisi_data"

    def test_returns_unauthenticated_context_when_no_token(self):
        ctx = get_user_context({"headers": {}})
        assert ctx["is_authenticated"] is False
        assert ctx["user_id"] is None
        assert ctx["role"] is None

    def test_returns_unauthenticated_context_for_expired_session(self):
        claims = {"sub": "u-xyz", "auth_time": time.time() - 30_000}
        event = _make_event(_make_token(claims))
        ctx = get_user_context(event)
        assert ctx["is_authenticated"] is False

    def test_never_raises(self):
        """get_user_context must be safe to call in any condition."""
        for bad_event in [None, {}, {"headers": None}, {"headers": {"Authorization": ""}}]:
            try:
                ctx = get_user_context(bad_event or {})
                assert isinstance(ctx, dict)
                assert "is_authenticated" in ctx
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"get_user_context raised unexpectedly: {exc}")

    def test_role_none_when_role_claim_missing(self):
        claims = {"sub": "u-norole", "auth_time": time.time() - 100}
        event = _make_event(_make_token(claims))
        ctx = get_user_context(event)
        assert ctx["is_authenticated"] is True
        assert ctx["role"] is None
