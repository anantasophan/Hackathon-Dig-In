"""JWT authentication middleware for Campaign Insight Generator.

Provides helpers to extract and validate JWT tokens from Lambda events,
enforce role-based access control, and check session expiry. The system
trusts API Gateway's built-in Cognito authorizer for cryptographic token
verification; this module decodes claims without re-verifying the
signature.

Requirements: 7.1, 7.2, 7.3
"""

from __future__ import annotations

import base64
import json
import time

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# 8-hour session limit in seconds (Requirement 7.2).
_SESSION_MAX_SECONDS: int = 28_800

_CORS_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

VALID_ROLES: frozenset[str] = frozenset({"divisi_bisnis", "divisi_data"})


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _build_401(message: str) -> dict:
    """Return a Lambda-compatible 401 response dict.

    Args:
        message: Human-readable explanation for the auth failure.

    Returns:
        A dict with ``statusCode``, ``headers``, and ``body`` ready to be
        returned directly from a Lambda handler.
    """
    return {
        "statusCode": 401,
        "headers": _CORS_HEADERS,
        "body": json.dumps({"message": message, "redirect": "/login"}),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_token(event: dict) -> str | None:
    """Extract the JWT Bearer token from a Lambda API Gateway event.

    Looks up ``event["headers"]["Authorization"]`` (case-sensitive) and
    strips the ``"Bearer "`` prefix.  Also handles lower-case
    ``"authorization"`` as a fallback to accommodate API Gateway's header
    normalisation behaviour.

    Args:
        event: The raw Lambda event dict forwarded by API Gateway.

    Returns:
        The raw JWT string, or ``None`` when the header is absent or
        does not contain a Bearer token.

    Examples:
        >>> extract_token({"headers": {"Authorization": "Bearer abc.def.ghi"}})
        'abc.def.ghi'

        >>> extract_token({"headers": {}}) is None
        True
    """
    headers: dict = event.get("headers") or {}

    # API Gateway v2 normalises headers to lower-case; v1 preserves case.
    auth_header: str | None = headers.get("Authorization") or headers.get(
        "authorization"
    )

    if not auth_header:
        return None

    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]

    return None


def decode_token_claims(token: str) -> dict | None:
    """Decode the claims payload of a JWT without signature verification.

    The JWT is split on ``"."`` and the second segment (index 1) is
    base64url-decoded.  Padding is added as required by the base64
    specification before decoding.

    This function deliberately does **not** verify the JWT signature
    because API Gateway's Cognito authorizer already validates the token
    before invoking the Lambda.  Re-verifying here would require network
    access to fetch Cognito's JWKS and is therefore unnecessary overhead.

    Args:
        token: A compact-serialisation JWT string (``header.payload.sig``).

    Returns:
        A dict containing the decoded claims, or ``None`` if the token is
        malformed or the payload is not valid JSON.

    Examples:
        >>> import base64, json
        >>> payload = base64.urlsafe_b64encode(
        ...     json.dumps({"sub": "u1", "custom:role": "divisi_bisnis"}).encode()
        ... ).rstrip(b"=").decode()
        >>> token = f"header.{payload}.sig"
        >>> claims = decode_token_claims(token)
        >>> claims["custom:role"]
        'divisi_bisnis'
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        payload_b64 = parts[1]
        # Restore base64 padding (required by the standard decoder).
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def extract_user_role(claims: dict) -> str | None:
    """Extract the user's role from Cognito JWT claims.

    Reads the ``custom:role`` claim, which is populated by the Cognito
    user pool's custom attribute.  Only the two known role values are
    returned; anything else is treated as absent.

    Args:
        claims: Decoded JWT claims dict.

    Returns:
        ``"divisi_bisnis"``, ``"divisi_data"``, or ``None`` when the claim
        is missing or contains an unrecognised value.

    Examples:
        >>> extract_user_role({"custom:role": "divisi_bisnis"})
        'divisi_bisnis'

        >>> extract_user_role({"custom:role": "admin"}) is None
        True
    """
    role: str | None = claims.get("custom:role")
    if role in VALID_ROLES:
        return role
    return None


def extract_user_id(claims: dict) -> str | None:
    """Extract the user identifier from Cognito JWT claims.

    Prefers the ``sub`` claim (the Cognito-assigned UUID), falling back to
    ``cognito:username`` when ``sub`` is absent.

    Args:
        claims: Decoded JWT claims dict.

    Returns:
        The user identifier string, or ``None`` if neither claim is present.

    Examples:
        >>> extract_user_id({"sub": "abc-123"})
        'abc-123'

        >>> extract_user_id({"cognito:username": "jdoe"})
        'jdoe'

        >>> extract_user_id({}) is None
        True
    """
    return claims.get("sub") or claims.get("cognito:username") or None


def is_session_expired(claims: dict) -> bool:
    """Check whether the user's session has exceeded the 8-hour limit.

    Reads the ``auth_time`` claim (Unix epoch seconds), which Cognito sets
    at the moment the user authenticates.  The session is considered expired
    when more than :data:`_SESSION_MAX_SECONDS` (28,800) seconds have
    elapsed since that timestamp.

    If ``auth_time`` is absent the function returns ``False`` (cannot
    determine expiry, so the session is assumed valid — API Gateway's
    token expiry check acts as the safety net).

    Args:
        claims: Decoded JWT claims dict.

    Returns:
        ``True`` when the session is expired, ``False`` otherwise.

    Examples:
        >>> import time
        >>> is_session_expired({"auth_time": time.time() - 30000})
        True

        >>> is_session_expired({"auth_time": time.time() - 100})
        False

        >>> is_session_expired({})
        False
    """
    auth_time = claims.get("auth_time")
    if auth_time is None:
        return False
    return (time.time() - float(auth_time)) > _SESSION_MAX_SECONDS


def require_auth(event: dict) -> tuple[dict | None, dict | None]:
    """Validate the request's JWT and enforce session expiry.

    This is the primary middleware entry point for Lambda handlers.  It:

    1. Extracts the Bearer token from the event headers.
    2. Decodes the JWT payload.
    3. Verifies the session has not exceeded 8 hours.

    Args:
        event: The raw Lambda event dict forwarded by API Gateway.

    Returns:
        A 2-tuple ``(claims, error_response)``:

        - On success: ``(claims_dict, None)`` where ``claims_dict`` holds
          the decoded JWT claims.
        - On failure: ``(None, error_response_dict)`` where
          ``error_response_dict`` is a 401 Lambda response ready to be
          returned directly.

    Examples:
        >>> claims, err = require_auth({"headers": {}})
        >>> err["statusCode"]
        401
    """
    token = extract_token(event)
    if token is None:
        return None, _build_401("Authentication required. Please log in.")

    claims = decode_token_claims(token)
    if claims is None:
        return None, _build_401("Invalid authentication token.")

    if is_session_expired(claims):
        return None, _build_401(
            "Your session has expired after 8 hours. Please log in again."
        )

    return claims, None


def get_user_context(event: dict) -> dict:
    """Return a safe user-context dict derived from the event's JWT.

    Convenience wrapper consumed by Lambda handlers that need user identity
    and role without needing to handle auth errors themselves.  Never raises
    — any failure results in safe defaults (``is_authenticated: False``).

    Args:
        event: The raw Lambda event dict forwarded by API Gateway.

    Returns:
        A dict with the following keys:

        - ``user_id`` (``str | None``): The authenticated user's identifier.
        - ``role`` (``str | None``): ``"divisi_bisnis"`` or
          ``"divisi_data"``, or ``None`` when the role is absent/invalid.
        - ``is_authenticated`` (``bool``): ``True`` only when a valid,
          non-expired token was found.

    Examples:
        >>> ctx = get_user_context({"headers": {}})
        >>> ctx["is_authenticated"]
        False
        >>> ctx["user_id"] is None
        True
    """
    try:
        claims, error = require_auth(event)
        if error is not None or claims is None:
            return {"user_id": None, "role": None, "is_authenticated": False}

        return {
            "user_id": extract_user_id(claims),
            "role": extract_user_role(claims),
            "is_authenticated": True,
        }
    except Exception:  # noqa: BLE001
        return {"user_id": None, "role": None, "is_authenticated": False}
