"""Audit logging middleware."""
from __future__ import annotations
import functools, json, logging, os, time
from datetime import datetime
from typing import Any, Callable
import boto3

logger = logging.getLogger(__name__)
_AUDIT_LOG_TABLE: str = os.environ.get("AUDIT_LOG_TABLE", "AuditLog")
_TTL_DAYS: int = 90
_REQUEST_PARAMS_MAX_LEN: int = 1000

def log_access(user_id: str, page_accessed: str, action: str, request_params: dict | None = None, ip_address: str | None = None) -> None:
    try:
        item: dict[str, Any] = {"user_id": user_id, "timestamp": datetime.utcnow().isoformat() + "Z", "page_accessed": page_accessed, "action": action, "expiry_timestamp": int(time.time()) + _TTL_DAYS * 86400}
        if request_params:
            item["request_params"] = {k: str(v)[:_REQUEST_PARAMS_MAX_LEN] for k, v in request_params.items()}
        if ip_address:
            item["ip_address"] = ip_address
        boto3.resource("dynamodb").Table(_AUDIT_LOG_TABLE).put_item(Item=item)
    except Exception:
        logger.warning("audit: failed for user=%s page=%s", user_id, page_accessed, exc_info=True)

def audit_log(page: str, action: str = "view") -> Callable:
    def decorator(handler_func: Callable) -> Callable:
        @functools.wraps(handler_func)
        def wrapper(event: dict, context: Any) -> Any:
            user_id = "anonymous"
            try:
                rc = event.get("requestContext") or {}
                auth = rc.get("authorizer") or {}
                user_id = str(auth.get("claims", {}).get("sub") or auth.get("principalId") or "anonymous")
            except Exception:
                pass
            ip_address = None
            try:
                ip_address = ((event.get("requestContext") or {}).get("identity") or {}).get("sourceIp")
            except Exception:
                pass
            log_access(user_id=user_id, page_accessed=page, action=action, ip_address=ip_address)
            return handler_func(event, context)
        return wrapper
    return decorator
