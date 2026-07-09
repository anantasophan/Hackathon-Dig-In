"""PII filter module."""
from __future__ import annotations
from typing import Any

PII_FIELDS: frozenset[str] = frozenset({"nama_lengkap", "nomor_rekening", "nomor_identitas", "alamat_lengkap"})

def strip_pii(data: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    if isinstance(data, list):
        return [strip_pii(item) for item in data]
    if isinstance(data, dict):
        return {k: strip_pii(v) for k, v in data.items() if k not in PII_FIELDS}
    return data

def has_pii(data: dict[str, Any] | list[Any]) -> bool:
    if isinstance(data, list):
        return any(has_pii(item) for item in data)
    if isinstance(data, dict):
        for key, value in data.items():
            if key in PII_FIELDS:
                return True
            if isinstance(value, (dict, list)) and has_pii(value):
                return True
    return False
