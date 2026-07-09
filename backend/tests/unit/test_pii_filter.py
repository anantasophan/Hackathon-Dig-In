"""Unit tests for the PII filter module (backend/shared/pii_filter.py).

Tests cover strip_pii, has_pii, and the PII_FIELDS constant.
Requirements: 7.5, 7.6
"""

import pytest

from shared.pii_filter import PII_FIELDS, has_pii, strip_pii


# ---------------------------------------------------------------------------
# PII_FIELDS constant
# ---------------------------------------------------------------------------


def test_pii_fields_is_frozenset() -> None:
    assert isinstance(PII_FIELDS, frozenset)


def test_pii_fields_contains_all_four_fields() -> None:
    expected = {"nama_lengkap", "nomor_rekening", "nomor_identitas", "alamat_lengkap"}
    assert expected == set(PII_FIELDS)


# ---------------------------------------------------------------------------
# strip_pii — flat dicts
# ---------------------------------------------------------------------------


def test_strip_pii_removes_single_pii_field() -> None:
    data = {"nama_lengkap": "Alice", "product": "KPR"}
    result = strip_pii(data)
    assert result == {"product": "KPR"}


def test_strip_pii_removes_all_four_pii_fields() -> None:
    data = {
        "nama_lengkap": "Alice",
        "nomor_rekening": "001-123",
        "nomor_identitas": "3271234567890001",
        "alamat_lengkap": "Jl. Merdeka 1",
        "product": "KPR",
        "region": "JKT",
    }
    result = strip_pii(data)
    assert result == {"product": "KPR", "region": "JKT"}


def test_strip_pii_no_pii_returns_identical_content() -> None:
    data = {"product": "KPR", "region": "JKT", "take_up_rate": 42.5}
    result = strip_pii(data)
    assert result == data


def test_strip_pii_empty_dict_returns_empty_dict() -> None:
    assert strip_pii({}) == {}


# ---------------------------------------------------------------------------
# strip_pii — non-mutation guarantee
# ---------------------------------------------------------------------------


def test_strip_pii_does_not_mutate_input_dict() -> None:
    data = {"nama_lengkap": "Alice", "product": "KPR"}
    original_keys = set(data.keys())
    strip_pii(data)
    assert set(data.keys()) == original_keys


# ---------------------------------------------------------------------------
# strip_pii — nested dicts
# ---------------------------------------------------------------------------


def test_strip_pii_removes_pii_from_nested_dict() -> None:
    data = {
        "campaign_id": "C001",
        "lead": {
            "nomor_rekening": "001-123",
            "region": "JKT",
        },
    }
    result = strip_pii(data)
    assert result == {"campaign_id": "C001", "lead": {"region": "JKT"}}


def test_strip_pii_removes_pii_from_deeply_nested_dict() -> None:
    data = {
        "outer": {
            "middle": {
                "alamat_lengkap": "Jl. Merdeka 1",
                "safe": "value",
            }
        }
    }
    result = strip_pii(data)
    assert result == {"outer": {"middle": {"safe": "value"}}}


# ---------------------------------------------------------------------------
# strip_pii — lists
# ---------------------------------------------------------------------------


def test_strip_pii_on_list_of_dicts() -> None:
    data = [
        {"nama_lengkap": "Alice", "product": "KPR"},
        {"nomor_identitas": "1234", "region": "JKT"},
    ]
    result = strip_pii(data)
    assert result == [{"product": "KPR"}, {"region": "JKT"}]


def test_strip_pii_on_empty_list_returns_empty_list() -> None:
    assert strip_pii([]) == []


def test_strip_pii_on_list_nested_inside_dict() -> None:
    data = {
        "leads": [
            {"nama_lengkap": "Alice", "region": "JKT"},
            {"nomor_rekening": "001", "product": "KPR"},
        ]
    }
    result = strip_pii(data)
    assert result == {
        "leads": [
            {"region": "JKT"},
            {"product": "KPR"},
        ]
    }


def test_strip_pii_returns_new_list_not_same_reference() -> None:
    data = [{"nama_lengkap": "Alice"}]
    result = strip_pii(data)
    assert result is not data


# ---------------------------------------------------------------------------
# strip_pii — mixed / edge cases
# ---------------------------------------------------------------------------


def test_strip_pii_handles_none_values_in_dict() -> None:
    data = {"product": None, "nomor_rekening": "001"}
    result = strip_pii(data)
    assert result == {"product": None}


def test_strip_pii_handles_integer_values() -> None:
    data = {"total_leads": 1000, "nomor_identitas": "ID123"}
    result = strip_pii(data)
    assert result == {"total_leads": 1000}


def test_strip_pii_list_of_non_dict_scalars_unchanged() -> None:
    # Scalars inside a list should pass through untouched.
    data = [1, "hello", None]
    result = strip_pii(data)
    assert result == [1, "hello", None]


# ---------------------------------------------------------------------------
# has_pii — flat dicts
# ---------------------------------------------------------------------------


def test_has_pii_returns_true_for_single_pii_field() -> None:
    assert has_pii({"nama_lengkap": "Alice", "product": "KPR"}) is True


def test_has_pii_returns_true_for_every_pii_field() -> None:
    for field in PII_FIELDS:
        assert has_pii({field: "value"}) is True


def test_has_pii_returns_false_when_no_pii() -> None:
    assert has_pii({"product": "KPR", "region": "JKT"}) is False


def test_has_pii_returns_false_for_empty_dict() -> None:
    assert has_pii({}) is False


# ---------------------------------------------------------------------------
# has_pii — nested dicts
# ---------------------------------------------------------------------------


def test_has_pii_detects_pii_in_nested_dict() -> None:
    data = {"campaign_id": "C001", "lead": {"nomor_rekening": "001"}}
    assert has_pii(data) is True


def test_has_pii_returns_false_when_nested_has_no_pii() -> None:
    data = {"campaign_id": "C001", "lead": {"region": "JKT"}}
    assert has_pii(data) is False


def test_has_pii_detects_pii_deeply_nested() -> None:
    data = {"a": {"b": {"c": {"alamat_lengkap": "Jl. X"}}}}
    assert has_pii(data) is True


# ---------------------------------------------------------------------------
# has_pii — lists
# ---------------------------------------------------------------------------


def test_has_pii_detects_pii_in_list_of_dicts() -> None:
    data = [{"product": "KPR"}, {"nomor_identitas": "9999"}]
    assert has_pii(data) is True


def test_has_pii_returns_false_for_list_with_no_pii() -> None:
    data = [{"product": "KPR"}, {"region": "JKT"}]
    assert has_pii(data) is False


def test_has_pii_returns_false_for_empty_list() -> None:
    assert has_pii([]) is False


def test_has_pii_detects_pii_in_list_nested_inside_dict() -> None:
    data = {
        "leads": [
            {"region": "JKT"},
            {"nama_lengkap": "Bob"},
        ]
    }
    assert has_pii(data) is True


# ---------------------------------------------------------------------------
# round-trip: strip_pii → has_pii
# ---------------------------------------------------------------------------


def test_strip_pii_output_has_no_pii_flat() -> None:
    data = {
        "nama_lengkap": "Alice",
        "nomor_rekening": "001",
        "product": "KPR",
    }
    assert not has_pii(strip_pii(data))


def test_strip_pii_output_has_no_pii_nested() -> None:
    data = {
        "campaign": {
            "leads": [
                {"nomor_identitas": "1234", "region": "JKT"},
                {"alamat_lengkap": "Jl. X", "product": "KPR"},
            ]
        }
    }
    assert not has_pii(strip_pii(data))
