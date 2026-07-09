"""Rate-limiter response helpers for Lambda handlers.

Provides a consistent factory for constructing HTTP 429 (Too Many Requests)
Lambda proxy responses, including the ``Retry-After`` header that informs
callers how long to wait before retrying.

In normal production operation, API Gateway itself enforces the configured
throttling limits (100 req/s rate, 50 req burst — see ``api_stack.py``) and
returns 429 automatically without involving Lambda.  This module is provided
so that Lambda handlers that implement *application-level* rate limiting (e.g.
per-user quota checks against DynamoDB) can return a correctly-formatted 429
response with the same shape as the rest of the API.

Requirements: 8.4
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_RETRY_AFTER_SECONDS: int = 60
"""Default ``Retry-After`` delay in seconds when no specific wait time is
known."""

_HEADERS_BASE: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def rate_limit_response(
    retry_after_seconds: int = _DEFAULT_RETRY_AFTER_SECONDS,
    message: str = "Terlalu banyak permintaan — harap tunggu sebelum mencoba lagi.",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a 429 Lambda proxy response with a ``Retry-After`` header.

    Args:
        retry_after_seconds: Number of seconds the client should wait before
            retrying.  Must be a positive integer; defaults to 60.
        message: Human-readable Indonesian-language error description to
            include in the response body.
        extra: Optional additional key–value pairs to merge into the JSON body
            (e.g. ``{"quota_resets_at": "2025-07-15T03:00:00Z"}``).

    Returns:
        API Gateway Lambda proxy response dict with:
        - ``statusCode``: 429
        - ``headers``: ``Content-Type``, ``Access-Control-Allow-Origin``,
          and ``Retry-After`` set to *retry_after_seconds*.
        - ``body``: JSON-encoded ``{"message": ..., "retry_after": ...}``
          plus any *extra* fields.

    Examples:
        >>> resp = rate_limit_response(retry_after_seconds=30)
        >>> resp["statusCode"]
        429
        >>> resp["headers"]["Retry-After"]
        '30'
        >>> import json; json.loads(resp["body"])["retry_after"]
        30
    """
    if retry_after_seconds < 1:
        retry_after_seconds = _DEFAULT_RETRY_AFTER_SECONDS

    body: dict[str, Any] = {
        "message": message,
        "retry_after": retry_after_seconds,
    }
    if extra:
        body.update(extra)

    headers = {
        **_HEADERS_BASE,
        # The ``Retry-After`` header value must be a string per RFC 7231.
        "Retry-After": str(retry_after_seconds),
    }

    return {
        "statusCode": 429,
        "headers": headers,
        "body": json.dumps(body),
    }
