"""JWT authentication middleware."""
from __future__ import annotations
import base64, json, time

_SESSION_MAX_SECONDS: int = 28_800
_CORS_HEADERS: dict = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
VALID_ROLES: frozenset[str] = frozenset({"divisi_bisnis", "divisi_data"})

def extract_token(event: dict) -> str | None:
    headers = event.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization")
    return auth[len("Bearer "):] if auth and auth.startswith("Bearer ") else None

def decode_token_claims(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(b64).decode())
    except Exception:
        return None

def extract_user_role(claims: dict) -> str | None:
    role = claims.get("custom:role")
    return role if role in VALID_ROLES else None

def extract_user_id(claims: dict) -> str | None:
    return claims.get("sub") or claims.get("cognito:username") or None

def is_session_expired(claims: dict) -> bool:
    auth_time = claims.get("auth_time")
    return False if auth_time is None else (time.time() - float(auth_time)) > _SESSION_MAX_SECONDS

def require_auth(event: dict) -> tuple[dict | None, dict | None]:
    token = extract_token(event)
    if not token:
        return None, {"statusCode": 401, "headers": _CORS_HEADERS, "body": json.dumps({"message": "Authentication required."})}
    claims = decode_token_claims(token)
    if not claims:
        return None, {"statusCode": 401, "headers": _CORS_HEADERS, "body": json.dumps({"message": "Invalid token."})}
    if is_session_expired(claims):
        return None, {"statusCode": 401, "headers": _CORS_HEADERS, "body": json.dumps({"message": "Session expired."})}
    return claims, None

def get_user_context(event: dict) -> dict:
    try:
        claims, error = require_auth(event)
        if error or not claims:
            return {"user_id": None, "role": None, "is_authenticated": False}
        return {"user_id": extract_user_id(claims), "role": extract_user_role(claims), "is_authenticated": True}
    except Exception:
        return {"user_id": None, "role": None, "is_authenticated": False}
