"""Property-based tests for the Local Development Server.

Tests 10 structural and behavioural properties of the FastAPI routes and
shared calculation/sorting helpers using the Hypothesis framework.

Each test is annotated with the requirement(s) it validates and the
property number from the spec.

Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 4.3, 4.4, 5.3, 6.3,
              6.4, 6.7, 7.5, 7.6, 9.3
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from local_server.main import app
from local_server.routers.campaigns import _build_histogram
from shared.calculations import compute_distribution_percentages, compute_statistics
from shared.models import SimilarCampaignResult
from shared.sorting import sort_regional_performance, sort_similar_campaigns

# ---------------------------------------------------------------------------
# Module-level TestClient (shared across HTTP tests)
# ---------------------------------------------------------------------------

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

_VALID_FLAG_PROGRAMS: list[str] = ["PROGRAM QRIS", "PROGRAM BIAYA ADMIN"]
_VALID_MEDIA_BLASTING: list[str] = [
    "wa", "digisales", "telesales", "email", "push notif", "sms"
]
_CAMPAIGN_IDS: list[str] = ["C001", "C002", "C003", "C004", "C005"]
_VALID_DIMENSIONS: list[str] = ["media_blasting", "jenis_leads", "flag_program"]

_INVALID_DATES: list[str] = [
    "not-a-date",
    "2024/08/01",
    "20240801",
    "32-01-2024",
    "",
    "abc",
    "2024-13-01",
    "2024-01-32",
    "hello world",
    "99-99-9999",
    "2024-1-1",
    "01-01-2024",
]


def _keys_recursive(obj: Any) -> list[str]:
    """Collect all dict keys recursively from a nested structure.

    Args:
        obj: Any JSON-decoded value (dict, list, scalar, or None).

    Returns:
        Flat list of every string key found at any nesting depth.
    """
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(k)
            keys.extend(_keys_recursive(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_keys_recursive(item))
    return keys


# ---------------------------------------------------------------------------
# Property 3 — Invalid date parameters always return 400
# Feature: local-dev-server, Property 3: Invalid date parameters always return 400
# Validates: Requirements 2.2
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(invalid_date=st.sampled_from(_INVALID_DATES))
def test_property_3_invalid_date_returns_400(invalid_date: str) -> None:
    """Invalid start_date query parameter must always produce an HTTP 400 response.

    **Validates: Requirements 2.2**

    Args:
        invalid_date: A date string that does not conform to ``yyyy-mm-dd``.
    """
    # Feature: local-dev-server, Property 3: Invalid date parameters always return 400
    response = client.get(
        "/api/campaigns/overview",
        params={"start_date": invalid_date},
    )
    assert response.status_code == 400, (
        f"Expected 400 for invalid start_date={invalid_date!r}, "
        f"got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Property 4 — Filter predicates respect AND semantics
# Feature: local-dev-server, Property 4: Filter predicates are respected
# Validates: Requirements 2.3, 2.4, 2.5, 2.6
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    flag_programs=st.lists(
        st.sampled_from(_VALID_FLAG_PROGRAMS),
        min_size=1,
        max_size=2,
        unique=True,
    ),
    media_blastings=st.lists(
        st.sampled_from(_VALID_MEDIA_BLASTING),
        min_size=1,
        max_size=3,
        unique=True,
    ),
)
def test_property_4_filter_and_semantics(
    flag_programs: list[str],
    media_blastings: list[str],
) -> None:
    """Active filters must appear in the ``filters`` list when results are non-empty.

    When the response is non-empty (``total_leads > 0``), every supplied
    filter value must be reflected back in the response ``filters`` array,
    confirming the server registered the AND-combined predicate.

    **Validates: Requirements 2.3, 2.4, 2.5, 2.6**

    Args:
        flag_programs: Random non-empty subset of valid flag_program values.
        media_blastings: Random non-empty subset of valid media_blasting values.
    """
    # Feature: local-dev-server, Property 4: Filter predicates are respected
    params: dict[str, str] = {
        "flag_program": ",".join(flag_programs),
        "media_blasting": ",".join(media_blastings),
    }
    response = client.get("/api/campaigns/overview", params=params)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )

    data = response.json()

    # If the response carries an empty-data message there's nothing to assert
    if "message" in data:
        return

    # For non-empty results the active filters must be echoed back
    assert "total_leads" in data and data["total_leads"] > 0
    filters_list: list[dict[str, Any]] = data.get("filters", [])
    filter_fields = {f["field"] for f in filters_list}

    assert "flag_program" in filter_fields, (
        f"Expected 'flag_program' in filters, got {filter_fields}"
    )
    assert "media_blasting" in filter_fields, (
        f"Expected 'media_blasting' in filters, got {filter_fields}"
    )


# ---------------------------------------------------------------------------
# Property 5 — Trend array is chronologically ordered
# Feature: local-dev-server, Property 5: Trend array is chronologically ordered
# Validates: Requirements 2.8
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(st.none())  # deterministic — no random inputs needed
def test_property_5_trend_chronological_order(_: None) -> None:
    """The trend array returned by the overview endpoint must be sorted
    chronologically (ascending by ``period_start``) and contain at least 4
    data points when called without filters.

    **Validates: Requirements 2.8**

    Args:
        _: Unused placeholder to satisfy the ``@given`` decorator signature.
    """
    # Feature: local-dev-server, Property 5: Trend array is chronologically ordered
    response = client.get("/api/campaigns/overview")
    assert response.status_code == 200

    data = response.json()
    assert "trend" in data, f"Expected 'trend' key in response: {data}"

    trend: list[dict[str, Any]] = data["trend"]
    assert len(trend) >= 4, (
        f"Expected at least 4 trend entries, got {len(trend)}"
    )

    for i in range(len(trend) - 1):
        assert trend[i]["period_start"] <= trend[i + 1]["period_start"], (
            f"Trend not sorted at index {i}: "
            f"{trend[i]['period_start']} > {trend[i + 1]['period_start']}"
        )


# ---------------------------------------------------------------------------
# Property 6 — No cif in any response
# Feature: local-dev-server, Property 6: No cif or PII in any response
# Validates: Requirements 2.9, 6.7, 9.3
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    campaign_id=st.sampled_from(_CAMPAIGN_IDS),
    dimensions=st.lists(
        st.sampled_from(_VALID_DIMENSIONS),
        min_size=1,
        max_size=3,
        unique=True,
    ),
)
def test_property_6_no_cif_in_any_response(
    campaign_id: str,
    dimensions: list[str],
) -> None:
    """No response body from any endpoint must contain the key ``"cif"``.

    PII removal is a hard requirement.  This test probes five endpoints
    and asserts recursively that ``"cif"`` does not appear as a key at
    any nesting level.

    **Validates: Requirements 2.9, 6.7, 9.3**

    Args:
        campaign_id: A valid campaign ID to use in path and body params.
        dimensions: A non-empty list of valid similarity dimensions.
    """
    # Feature: local-dev-server, Property 6: No cif or PII in any response

    endpoints_responses: list[Any] = [
        client.get("/api/campaigns/overview").json(),
        client.get(f"/api/campaigns/time-analysis/{campaign_id}").json(),
        client.get(f"/api/campaigns/regional/{campaign_id}").json(),
        client.get(f"/api/campaigns/customer-criteria/{campaign_id}").json(),
        client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": campaign_id,
                "dimensions": dimensions,
            },
        ).json(),
    ]

    for body in endpoints_responses:
        all_keys = _keys_recursive(body)
        assert "cif" not in all_keys, (
            f"PII field 'cif' found in response body: {body}"
        )


# ---------------------------------------------------------------------------
# Property 10 — Histogram always has exactly 7 bins
# Feature: local-dev-server, Property 10: Histogram always has exactly 7 bins
# Validates: Requirements 4.3
# ---------------------------------------------------------------------------

_HISTOGRAM_EXPECTED_STARTS: list[int] = [0, 7, 14, 21, 30, 60, 90]


@settings(max_examples=100)
@given(
    values=st.lists(
        st.integers(min_value=0, max_value=365),
        min_size=1,
        max_size=500,
    )
)
def test_property_10_histogram_7_bins(values: list[int]) -> None:
    """_build_histogram must always return exactly 7 bins with fixed range
    boundaries, and the total bin count must equal the input length.

    **Validates: Requirements 4.3**

    Args:
        values: A non-empty list of non-negative integer day counts.
    """
    # Feature: local-dev-server, Property 10: Histogram always has exactly 7 bins
    result = _build_histogram(values)

    assert len(result) == 7, (
        f"Expected 7 bins, got {len(result)}"
    )

    actual_starts = [bin_["range_start"] for bin_ in result]
    assert actual_starts == _HISTOGRAM_EXPECTED_STARTS, (
        f"Unexpected range_start values: {actual_starts}"
    )

    total_count = sum(bin_["count"] for bin_ in result)
    assert total_count == len(values), (
        f"Bin counts sum to {total_count}, expected {len(values)}"
    )


# ---------------------------------------------------------------------------
# Property 11 — Statistics invariant: max >= min >= 0
# Feature: local-dev-server, Property 11: Statistics invariant max >= min >= 0
# Validates: Requirements 4.4
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    values=st.lists(
        st.integers(min_value=0, max_value=10_000),
        min_size=1,
        max_size=300,
    )
)
def test_property_11_statistics_invariants(values: list[int]) -> None:
    """compute_statistics must satisfy max >= min >= 0 and both mean and median
    must be non-negative for any non-empty list of non-negative integers.

    **Validates: Requirements 4.4**

    Args:
        values: A non-empty list of non-negative integers.
    """
    # Feature: local-dev-server, Property 11: Statistics invariant max >= min >= 0
    result = compute_statistics(values)

    assert result["min"] >= 0, (
        f"min={result['min']} is negative for values={values}"
    )
    assert result["max"] >= result["min"], (
        f"max={result['max']} < min={result['min']}"
    )
    assert result["mean"] >= 0, (
        f"mean={result['mean']} is negative"
    )
    assert result["median"] >= 0, (
        f"median={result['median']} is negative"
    )


# ---------------------------------------------------------------------------
# Property 12 — Regions sorted descending by take_up_rate
# Feature: local-dev-server, Property 12: Regions sorted descending by take_up_rate
# Validates: Requirements 5.3
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    regions=st.lists(
        st.fixed_dictionaries(
            {
                "region": st.text(min_size=1, max_size=10),
                "take_up_rate": st.floats(
                    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
                ),
            }
        ),
        min_size=0,
        max_size=20,
    )
)
def test_property_12_regions_sorted_descending(
    regions: list[dict[str, Any]],
) -> None:
    """sort_regional_performance must produce a list where each element's
    ``take_up_rate`` is >= the next element's ``take_up_rate`` (descending).

    **Validates: Requirements 5.3**

    Args:
        regions: A list of region dicts each containing a ``take_up_rate`` float.
    """
    # Feature: local-dev-server, Property 12: Regions sorted descending by take_up_rate
    result = sort_regional_performance(regions)

    for i in range(len(result) - 1):
        assert result[i]["take_up_rate"] >= result[i + 1]["take_up_rate"], (
            f"Sort violation at index {i}: "
            f"{result[i]['take_up_rate']} < {result[i + 1]['take_up_rate']}"
        )


# ---------------------------------------------------------------------------
# Property 14 — Distribution percentages sum to 100
# Feature: local-dev-server, Property 14: Distribution items contain required fields and sum to 100%
# Validates: Requirements 6.3, 6.4
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    groups=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.integers(min_value=1, max_value=10_000),
        min_size=1,
        max_size=15,
    )
)
def test_property_14_distribution_sums_to_100(
    groups: dict[str, int],
) -> None:
    """compute_distribution_percentages must return percentages that sum to
    exactly 100.0 (within floating-point tolerance of 0.01) and each
    individual percentage must be in [0, 100].

    **Validates: Requirements 6.3, 6.4**

    Args:
        groups: A non-empty dict mapping group label to positive integer count.
    """
    # Feature: local-dev-server, Property 14: Distribution items contain required fields and sum to 100%
    result = compute_distribution_percentages(groups)

    total = sum(result.values())
    assert abs(total - 100.0) <= 0.01, (
        f"Percentages sum to {total}, expected ~100.0 (groups={groups})"
    )

    for label, pct in result.items():
        assert 0.0 <= pct <= 100.0, (
            f"Percentage for '{label}' is {pct}, expected 0–100"
        )


# ---------------------------------------------------------------------------
# Property 16 — Similar campaigns sorted by dimension_count desc then take_up_rate desc
# Feature: local-dev-server, Property 16: similar_campaigns sorted by dimension_count desc then take_up_rate desc
# Validates: Requirements 7.5
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    campaigns=st.lists(
        st.builds(
            SimilarCampaignResult,
            campaign_id=st.text(min_size=1, max_size=10),
            campaign_name=st.text(min_size=1, max_size=30),
            matching_dimensions=st.lists(
                st.sampled_from(_VALID_DIMENSIONS),
                min_size=0,
                max_size=3,
                unique=True,
            ),
            dimension_count=st.integers(min_value=0, max_value=3),
            similarity_score=st.floats(
                min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
            take_up_rate=st.floats(
                min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
            ),
            total_leads=st.integers(min_value=1, max_value=10_000),
            total_take_up=st.integers(min_value=0, max_value=10_000),
        ),
        min_size=0,
        max_size=20,
    )
)
def test_property_16_similar_campaigns_sort_order(
    campaigns: list[SimilarCampaignResult],
) -> None:
    """sort_similar_campaigns must produce a list sorted first by
    ``dimension_count`` descending and then by ``take_up_rate`` descending
    as a tiebreaker.

    **Validates: Requirements 7.5**

    Args:
        campaigns: A list of SimilarCampaignResult objects with arbitrary
            dimension_count and take_up_rate values.
    """
    # Feature: local-dev-server, Property 16: similar_campaigns sorted by dimension_count desc then take_up_rate desc
    result = sort_similar_campaigns(campaigns)

    for i in range(len(result) - 1):
        curr = result[i]
        nxt = result[i + 1]
        assert curr.dimension_count >= nxt.dimension_count, (
            f"dimension_count violation at index {i}: "
            f"{curr.dimension_count} < {nxt.dimension_count}"
        )
        if curr.dimension_count == nxt.dimension_count:
            assert curr.take_up_rate >= nxt.take_up_rate, (
                f"take_up_rate tiebreaker violation at index {i}: "
                f"{curr.take_up_rate} < {nxt.take_up_rate} "
                f"(dimension_count both = {curr.dimension_count})"
            )


# ---------------------------------------------------------------------------
# Property 17 — similar_campaigns length bounded by min(limit, 20)
# Feature: local-dev-server, Property 17: similar_campaigns length bounded by min(limit, 20)
# Validates: Requirements 7.6
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    reference_id=st.sampled_from(_CAMPAIGN_IDS),
    limit=st.integers(min_value=1, max_value=100),
    dimensions=st.lists(
        st.sampled_from(_VALID_DIMENSIONS),
        min_size=1,
        max_size=3,
        unique=True,
    ),
)
def test_property_17_similar_campaigns_bounded_by_limit(
    reference_id: str,
    limit: int,
    dimensions: list[str],
) -> None:
    """The similar_campaigns list must never exceed min(limit, 20) items,
    regardless of the requested limit value.

    **Validates: Requirements 7.6**

    Args:
        reference_id: A valid campaign ID to use as the reference.
        limit: A requested limit between 1 and 100 (may exceed the hard cap
            of 20 — the server must still honour the cap).
        dimensions: A non-empty list of valid matching dimensions.
    """
    # Feature: local-dev-server, Property 17: similar_campaigns length bounded by min(limit, 20)
    response = client.post(
        "/api/campaigns/similar",
        json={
            "reference_campaign_id": reference_id,
            "dimensions": dimensions,
            "limit": limit,
        },
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )

    data = response.json()
    similar: list[Any] = data.get("similar_campaigns", [])
    expected_max = min(limit, 20)
    assert len(similar) <= expected_max, (
        f"Got {len(similar)} results, expected <= {expected_max} "
        f"(limit={limit}, reference={reference_id}, dimensions={dimensions})"
    )
