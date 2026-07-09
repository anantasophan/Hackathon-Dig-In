"""Rate-limiter response helpers."""
from __future__ import annotations
import json
from typing import Any

_DEFAULT_RETRY_AFTER_SECONDS: int = 60
_HEADERS_BASE: dict[str, str] = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}

def rate_limit_response(retry_after_seconds: int = _DEFAULT_RETRY_AFTER_SECONDS, message: str = "Terlalu banyak permintaan — harap tunggu sebelum mencoba lagi.", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if retry_after_seconds < 1:
        retry_after_seconds = _DEFAULT_RETRY_AFTER_SECONDS
    body: dict[str, Any] = {"message": message, "retry_after": retry_after_seconds}
    if extra:
        body.update(extra)
    return {"statusCode": 429, "headers": {**_HEADERS_BASE, "Retry-After": str(retry_after_seconds)}, "body": json.dumps(body)}
