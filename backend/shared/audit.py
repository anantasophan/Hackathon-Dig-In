"""Audit logging middleware for Campaign Insight Generator.

Records user access events to the DynamoDB AuditLog table for security
and compliance purposes.  Every Lambda handler should be wrapped with the
:func:`audit_log` decorator so that each request is automatically logged.

DynamoDB table schema (``AuditLog``):
    - PK  ``user_id``         (String)
    - SK  ``timestamp``       (String, ISO 8601)
    - Attributes: ``page_accessed``, ``action``, ``request_params`` (Map),
      ``ip_address``, ``expiry_timestamp`` (Number, Unix epoch for TTL).

Requirements: 7.4
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Callable

import boto3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUDIT_LOG_TABLE: str = os.environ.get("AUDIT_LOG_TABLE", "AuditLog")
"""DynamoDB table name for audit log entries (overridable via environment)."""

_TTL_DAYS: int = 90
"""Number of days before an audit log item expires (DynamoDB TTL)."""

_REQUEST_PARAMS_MAX_LEN: int = 1000
"""Maximum length (chars) for serialised request parameters stored in DynamoDB.

DynamoDB items have a 400 KB size limit; truncating params prevents accidental
oversized items while still preserving enough context for auditing.
"""


# ---------------------------------------------------------------------------
# Core write function
# ---------------------------------------------------------------------------


def log_access(
    user_id: str,
    page_accessed: str,
    action: str,
    request_params: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Write a single audit log entry to DynamoDB.

    This function is *best-effort*: all exceptions are caught and silently
    swallowed so that a DynamoDB unavailability (or misconfiguration) never
    crashes a Lambda handler.

    The item uses DynamoDB's TTL feature: ``expiry_timestamp`` is set to 90
    days in the future (Unix epoch seconds) so that old entries are
    automatically deleted.

    Args:
        user_id: Cognito subject (``sub``) claim or ``"anonymous"`` if the
            request is unauthenticated.
        page_accessed: The dashboard page or API endpoint that was accessed
            (e.g. ``"campaign_overview"``, ``"regional_performance"``).
        action: The action performed (e.g. ``"view"``, ``"export"``).
        request_params: Optional dict of query/body parameters associated with
            the request.  Serialised and truncated to
            :data:`_REQUEST_PARAMS_MAX_LEN` characters.
        ip_address: Optional source IP address extracted from the API Gateway
            request context.

    Returns:
        None.  Errors are logged at WARNING level but never re-raised.
    """
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        expiry_timestamp = int(time.time()) + _TTL_DAYS * 24 * 3600

        item: dict[str, Any] = {
            "user_id": user_id,
            "timestamp": timestamp,
            "page_accessed": page_accessed,
            "action": action,
            "expiry_timestamp": expiry_timestamp,
        }

        if request_params is not None:
            item["request_params"] = _sanitise_params(request_params)

        if ip_address is not None:
            item["ip_address"] = ip_address

        table = boto3.resource("dynamodb").Table(_AUDIT_LOG_TABLE)
        table.put_item(Item=item)

    except Exception:  # noqa: BLE001
        logger.warning(
            "audit: failed to write log entry for user=%s page=%s",
            user_id,
            page_accessed,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Request-parameter extraction helpers
# ---------------------------------------------------------------------------


def extract_request_params(event: dict[str, Any]) -> dict[str, Any]:
    """Extract a safe, truncated representation of request parameters from an
    API Gateway Lambda proxy *event*.

    Query-string parameters and body content (up to
    :data:`_REQUEST_PARAMS_MAX_LEN` characters) are merged into a single
    dict.  If the body is a valid JSON object its keys are merged directly;
    otherwise it is stored as a ``"body"`` string key.

    This function never raises — any exception results in an empty dict being
    returned so that audit logging cannot crash a handler.

    Args:
        event: API Gateway Lambda proxy event dict.

    Returns:
        A plain ``dict[str, Any]`` containing query-string parameters and
        (optionally) body content, with all values truncated to prevent
        oversized DynamoDB items.  Returns ``{}`` on any error.
    """
    try:
        params: dict[str, Any] = {}

        # Query string parameters
        qs = event.get("queryStringParameters") or {}
        if isinstance(qs, dict):
            params.update(qs)

        # Body — attempt JSON parse; fall back to raw string
        raw_body = event.get("body")
        if raw_body:
            if isinstance(raw_body, str):
                truncated_body = raw_body[:_REQUEST_PARAMS_MAX_LEN]
                try:
                    parsed = json.loads(truncated_body)
                    if isinstance(parsed, dict):
                        params.update(parsed)
                    else:
                        params["body"] = truncated_body
                except (json.JSONDecodeError, ValueError):
                    params["body"] = truncated_body
            elif isinstance(raw_body, dict):
                params.update(raw_body)

        return params

    except Exception:  # noqa: BLE001
        return {}


def _sanitise_params(params: dict[str, Any]) -> dict[str, Any]:
    """Return a DynamoDB-safe copy of *params* with oversized string values
    truncated.

    All values are converted to strings and capped at
    :data:`_REQUEST_PARAMS_MAX_LEN` characters to stay within DynamoDB's
    400 KB item size limit.

    Args:
        params: Raw request parameters dict.

    Returns:
        A new dict with the same keys but truncated string values.
    """
    safe: dict[str, Any] = {}
    for key, value in params.items():
        str_value = str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
        if isinstance(str_value, str) and len(str_value) > _REQUEST_PARAMS_MAX_LEN:
            safe[key] = str_value[:_REQUEST_PARAMS_MAX_LEN]
        else:
            safe[key] = str_value
    return safe


# ---------------------------------------------------------------------------
# Decorator factory
# ---------------------------------------------------------------------------


def audit_log(page: str, action: str = "view") -> Callable:
    """Decorator factory that wraps a Lambda handler with audit logging.

    The decorator extracts user identity and request context from the API
    Gateway Lambda proxy *event*, calls :func:`log_access`, and then
    delegates to the original handler.  Audit logging failures are silently
    swallowed — the handler is always called regardless.

    Usage::

        from shared.audit import audit_log

        @audit_log(page="campaign_overview", action="view")
        def lambda_handler(event, context):
            ...

    User identity is resolved in the following order:

    1. ``event["requestContext"]["authorizer"]["claims"]["sub"]`` — standard
       Cognito JWT authorizer claim.
    2. ``event["requestContext"]["authorizer"]["principalId"]`` — custom
       Lambda authorizer principal.
    3. ``"anonymous"`` — fallback when neither is present (unauthenticated or
       missing authorizer context).

    IP address is extracted from
    ``event["requestContext"]["identity"]["sourceIp"]`` when available.

    Args:
        page: Name of the dashboard page or API endpoint being accessed.
            This value is stored as ``page_accessed`` in the audit log entry.
        action: The type of action (default ``"view"``).  Common values:
            ``"view"``, ``"export"``, ``"compare"``.

    Returns:
        Decorator that wraps a ``(event, context) -> Any`` Lambda handler.
    """

    def decorator(handler_func: Callable) -> Callable:
        @functools.wraps(handler_func)
        def wrapper(event: dict[str, Any], context: Any) -> Any:
            # ----------------------------------------------------------
            # Extract user identity
            # ----------------------------------------------------------
            user_id = "anonymous"
            try:
                request_ctx = event.get("requestContext") or {}
                authorizer = request_ctx.get("authorizer") or {}

                # Cognito User Pools authorizer provides JWT claims
                claims = authorizer.get("claims") or {}
                if claims.get("sub"):
                    user_id = str(claims["sub"])
                # Custom Lambda authorizer uses principalId
                elif authorizer.get("principalId"):
                    user_id = str(authorizer["principalId"])
            except Exception:  # noqa: BLE001
                pass  # keep user_id = "anonymous"

            # ----------------------------------------------------------
            # Extract source IP address
            # ----------------------------------------------------------
            ip_address: str | None = None
            try:
                request_ctx = event.get("requestContext") or {}
                identity = request_ctx.get("identity") or {}
                raw_ip = identity.get("sourceIp")
                if raw_ip:
                    ip_address = str(raw_ip)
            except Exception:  # noqa: BLE001
                pass

            # ----------------------------------------------------------
            # Extract request parameters
            # ----------------------------------------------------------
            request_params = extract_request_params(event)

            # ----------------------------------------------------------
            # Write audit log entry (best-effort, never raises)
            # ----------------------------------------------------------
            log_access(
                user_id=user_id,
                page_accessed=page,
                action=action,
                request_params=request_params or None,
                ip_address=ip_address,
            )

            # ----------------------------------------------------------
            # Invoke the original handler
            # ----------------------------------------------------------
            return handler_func(event, context)

        return wrapper

    return decorator
