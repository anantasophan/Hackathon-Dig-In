"""Unit tests for backend/local_server/mock_store.py — MockDataStore.

Covers:
- Each individual filter type on get_leads()
- Combinations of 2+ filters (AND logic)
- Date range filtering (start_date / end_date)
- get_campaign(), get_all_campaigns()
- get_similarity_index(), get_trend_data(), get_regional_weekly()

Requirements: 2.3, 2.4, 2.5, 2.6
"""

from __future__ import annotations

import pytest

from local_server.mock_store import MockDataStore


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def store() -> MockDataStore:
    """Return a single MockDataStore instance shared across all tests.

    Module-scope means the JSON files are loaded only once per test run.
    """
    return MockDataStore()


# ---------------------------------------------------------------------------
# get_leads — no filters (sanity)
# ---------------------------------------------------------------------------


class TestGetLeadsNoFilter:
    def test_returns_list(self, store: MockDataStore) -> None:
        result = store.get_leads()
        assert isinstance(result, list)

    def test_returns_all_records_when_no_filter(self, store: MockDataStore) -> None:
        result = store.get_leads()
        # leads.json has ~150 records
        assert len(result) > 0

    def test_result_contains_dicts(self, store: MockDataStore) -> None:
        result = store.get_leads()
        assert all(isinstance(r, dict) for r in result)

    def test_no_cif_field_in_any_lead(self, store: MockDataStore) -> None:
        """Requirement 9.3: mock data must not contain PII field ``cif``."""
        result = store.get_leads()
        for lead in result:
            assert "cif" not in lead


# ---------------------------------------------------------------------------
# get_leads — campaign_id filter
# ---------------------------------------------------------------------------


class TestGetLeadsByCampaignId:
    def test_filter_c001(self, store: MockDataStore) -> None:
        result = store.get_leads(campaign_id="C001")
        assert len(result) > 0
        assert all(r["campaign_id"] == "C001" for r in result)

    def test_filter_c002(self, store: MockDataStore) -> None:
        result = store.get_leads(campaign_id="C002")
        assert len(result) > 0
        assert all(r["campaign_id"] == "C002" for r in result)

    def test_unknown_campaign_returns_empty(self, store: MockDataStore) -> None:
        result = store.get_leads(campaign_id="DOES_NOT_EXIST")
        assert result == []

    def test_campaigns_are_disjoint(self, store: MockDataStore) -> None:
        c001 = store.get_leads(campaign_id="C001")
        c002 = store.get_leads(campaign_id="C002")
        ids_c001 = {id(r) for r in c001}
        ids_c002 = {id(r) for r in c002}
        assert ids_c001.isdisjoint(ids_c002)

    def test_total_across_campaigns_equals_all_leads(
        self, store: MockDataStore
    ) -> None:
        all_leads = store.get_leads()
        totals = sum(
            len(store.get_leads(campaign_id=cid))
            for cid in ["C001", "C002", "C003", "C004", "C005"]
        )
        assert totals == len(all_leads)


# ---------------------------------------------------------------------------
# get_leads — flag_program filter
# ---------------------------------------------------------------------------


class TestGetLeadsByFlagProgram:
    def test_filter_qris(self, store: MockDataStore) -> None:
        result = store.get_leads(flag_program=["PROGRAM QRIS"])
        assert len(result) > 0
        assert all(r["flag_program"] == "PROGRAM QRIS" for r in result)

    def test_filter_biaya_admin(self, store: MockDataStore) -> None:
        result = store.get_leads(flag_program=["PROGRAM BIAYA ADMIN"])
        assert len(result) > 0
        assert all(r["flag_program"] == "PROGRAM BIAYA ADMIN" for r in result)

    def test_filter_both_returns_all(self, store: MockDataStore) -> None:
        all_leads = store.get_leads()
        both = store.get_leads(
            flag_program=["PROGRAM QRIS", "PROGRAM BIAYA ADMIN"]
        )
        assert len(both) == len(all_leads)

    def test_empty_list_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(flag_program=[])
        assert result == []

    def test_invalid_value_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(flag_program=["INVALID_PROGRAM"])
        assert result == []


# ---------------------------------------------------------------------------
# get_leads — media_blasting filter
# ---------------------------------------------------------------------------


class TestGetLeadsByMediaBlasting:
    def test_filter_wa(self, store: MockDataStore) -> None:
        result = store.get_leads(media_blasting=["wa"])
        assert len(result) > 0
        assert all(r["media_blasting"] == "wa" for r in result)

    def test_filter_telesales(self, store: MockDataStore) -> None:
        result = store.get_leads(media_blasting=["telesales"])
        assert len(result) > 0
        assert all(r["media_blasting"] == "telesales" for r in result)

    def test_filter_multiple_channels(self, store: MockDataStore) -> None:
        channels = ["wa", "digisales"]
        result = store.get_leads(media_blasting=channels)
        assert all(r["media_blasting"] in channels for r in result)

    def test_empty_list_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(media_blasting=[])
        assert result == []

    def test_unknown_channel_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(media_blasting=["carrier_pigeon"])
        assert result == []


# ---------------------------------------------------------------------------
# get_leads — wilayah filter (int)
# ---------------------------------------------------------------------------


class TestGetLeadsByWilayah:
    def test_filter_single_wilayah(self, store: MockDataStore) -> None:
        result = store.get_leads(wilayah=[1])
        assert len(result) > 0
        assert all(r["wilayah"] == 1 for r in result)

    def test_filter_multiple_wilayah(self, store: MockDataStore) -> None:
        result = store.get_leads(wilayah=[1, 3])
        assert all(r["wilayah"] in [1, 3] for r in result)

    def test_wilayah_is_integer(self, store: MockDataStore) -> None:
        """wilayah values stored in JSON must be integers, not strings."""
        result = store.get_leads(wilayah=[1])
        for lead in result:
            assert isinstance(lead["wilayah"], int)

    def test_empty_list_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(wilayah=[])
        assert result == []

    def test_nonexistent_wilayah_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(wilayah=[99])
        assert result == []


# ---------------------------------------------------------------------------
# get_leads — jenis_leads filter
# ---------------------------------------------------------------------------


class TestGetLeadsByJenisLeads:
    def test_filter_akuisisi(self, store: MockDataStore) -> None:
        result = store.get_leads(jenis_leads=["Akuisisi"])
        assert len(result) > 0
        assert all(r["jenis_leads"] == "Akuisisi" for r in result)

    def test_filter_migrasi(self, store: MockDataStore) -> None:
        result = store.get_leads(jenis_leads=["Migrasi"])
        assert len(result) > 0
        assert all(r["jenis_leads"] == "Migrasi" for r in result)

    def test_filter_multiple_jenis(self, store: MockDataStore) -> None:
        jenis = ["Akuisisi", "Migrasi"]
        result = store.get_leads(jenis_leads=jenis)
        assert all(r["jenis_leads"] in jenis for r in result)

    def test_empty_list_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(jenis_leads=[])
        assert result == []

    def test_invalid_value_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(jenis_leads=["INVALID"])
        assert result == []


# ---------------------------------------------------------------------------
# get_leads — date range filtering
# ---------------------------------------------------------------------------


class TestGetLeadsDateRange:
    def test_start_date_inclusive(self, store: MockDataStore) -> None:
        # All C001 leads have periode_start = "2024-08-01"
        result = store.get_leads(campaign_id="C001", start_date="2024-08-01")
        assert len(result) > 0
        assert all(r["periode_start"] >= "2024-08-01" for r in result)

    def test_end_date_inclusive(self, store: MockDataStore) -> None:
        result = store.get_leads(campaign_id="C001", end_date="2024-08-31")
        assert len(result) > 0
        assert all(r["periode_start"] <= "2024-08-31" for r in result)

    def test_exact_date_range_c001(self, store: MockDataStore) -> None:
        # C001 periode_start = "2024-08-01" — should pass [2024-08-01, 2024-08-31]
        result = store.get_leads(
            campaign_id="C001",
            start_date="2024-08-01",
            end_date="2024-08-31",
        )
        assert len(result) > 0

    def test_date_range_excludes_later_campaign(self, store: MockDataStore) -> None:
        # C005 starts 2024-11-01, should be excluded by end_date of 2024-10-31
        result = store.get_leads(end_date="2024-10-31")
        c005_records = [r for r in result if r["campaign_id"] == "C005"]
        assert c005_records == []

    def test_date_range_excludes_earlier_campaign(self, store: MockDataStore) -> None:
        # C002 starts 2024-07-01, should be excluded by start_date 2024-08-01
        result = store.get_leads(start_date="2024-08-01")
        c002_records = [r for r in result if r["campaign_id"] == "C002"]
        assert c002_records == []

    def test_date_range_no_matches(self, store: MockDataStore) -> None:
        # Date range in the far future — nothing matches
        result = store.get_leads(start_date="2030-01-01", end_date="2030-12-31")
        assert result == []

    def test_start_after_end_returns_nothing(self, store: MockDataStore) -> None:
        result = store.get_leads(start_date="2024-12-01", end_date="2024-01-01")
        assert result == []


# ---------------------------------------------------------------------------
# get_leads — AND logic with combined filters
# ---------------------------------------------------------------------------


class TestGetLeadsAndLogic:
    def test_campaign_id_and_flag_program(self, store: MockDataStore) -> None:
        result = store.get_leads(
            campaign_id="C001",
            flag_program=["PROGRAM QRIS"],
        )
        assert len(result) > 0
        for r in result:
            assert r["campaign_id"] == "C001"
            assert r["flag_program"] == "PROGRAM QRIS"

    def test_flag_program_and_media_blasting(self, store: MockDataStore) -> None:
        result = store.get_leads(
            flag_program=["PROGRAM QRIS"],
            media_blasting=["wa"],
        )
        for r in result:
            assert r["flag_program"] == "PROGRAM QRIS"
            assert r["media_blasting"] == "wa"

    def test_three_filters_simultaneously(self, store: MockDataStore) -> None:
        result = store.get_leads(
            campaign_id="C001",
            flag_program=["PROGRAM QRIS"],
            wilayah=[1, 3, 5],
        )
        for r in result:
            assert r["campaign_id"] == "C001"
            assert r["flag_program"] == "PROGRAM QRIS"
            assert r["wilayah"] in [1, 3, 5]

    def test_conflicting_filters_return_empty(self, store: MockDataStore) -> None:
        # C001 is PROGRAM QRIS — asking for C001 + BIAYA ADMIN should return nothing
        result = store.get_leads(
            campaign_id="C001",
            flag_program=["PROGRAM BIAYA ADMIN"],
        )
        assert result == []

    def test_campaign_and_date_range(self, store: MockDataStore) -> None:
        result = store.get_leads(
            campaign_id="C002",
            start_date="2024-07-01",
            end_date="2024-09-30",
        )
        assert len(result) > 0
        for r in result:
            assert r["campaign_id"] == "C002"
            assert "2024-07-01" <= r["periode_start"] <= "2024-09-30"

    def test_all_filters_combined(self, store: MockDataStore) -> None:
        result = store.get_leads(
            campaign_id="C001",
            flag_program=["PROGRAM QRIS"],
            media_blasting=["wa"],
            wilayah=[1],
            jenis_leads=["Akuisisi"],
            start_date="2024-08-01",
            end_date="2024-08-31",
        )
        for r in result:
            assert r["campaign_id"] == "C001"
            assert r["flag_program"] == "PROGRAM QRIS"
            assert r["media_blasting"] == "wa"
            assert r["wilayah"] == 1
            assert r["jenis_leads"] == "Akuisisi"
            assert "2024-08-01" <= r["periode_start"] <= "2024-08-31"


# ---------------------------------------------------------------------------
# get_leads — non-mutating
# ---------------------------------------------------------------------------


class TestGetLeadsNonMutating:
    def test_returns_new_list_each_call(self, store: MockDataStore) -> None:
        result1 = store.get_leads()
        result2 = store.get_leads()
        assert result1 is not result2

    def test_modifying_result_does_not_affect_store(
        self, store: MockDataStore
    ) -> None:
        result1 = store.get_leads(campaign_id="C001")
        original_length = len(store.get_leads(campaign_id="C001"))
        result1.clear()
        assert len(store.get_leads(campaign_id="C001")) == original_length


# ---------------------------------------------------------------------------
# get_campaign
# ---------------------------------------------------------------------------


class TestGetCampaign:
    def test_known_id_returns_dict(self, store: MockDataStore) -> None:
        campaign = store.get_campaign("C001")
        assert campaign is not None
        assert isinstance(campaign, dict)

    def test_returned_dict_has_campaign_id(self, store: MockDataStore) -> None:
        campaign = store.get_campaign("C001")
        assert campaign is not None
        assert campaign["campaign_id"] == "C001"

    def test_returned_dict_has_expected_fields(self, store: MockDataStore) -> None:
        campaign = store.get_campaign("C002")
        assert campaign is not None
        for field in (
            "campaign_id",
            "nama_program",
            "flag_program",
            "jenis_leads",
            "media_blasting",
            "periode_start",
            "periode_end",
            "duration_days",
        ):
            assert field in campaign

    def test_unknown_id_returns_none(self, store: MockDataStore) -> None:
        assert store.get_campaign("C999") is None

    def test_all_five_campaigns_accessible(self, store: MockDataStore) -> None:
        for cid in ["C001", "C002", "C003", "C004", "C005"]:
            camp = store.get_campaign(cid)
            assert camp is not None, f"Expected campaign {cid} to exist"


# ---------------------------------------------------------------------------
# get_all_campaigns
# ---------------------------------------------------------------------------


class TestGetAllCampaigns:
    def test_returns_five_records(self, store: MockDataStore) -> None:
        campaigns = store.get_all_campaigns()
        assert len(campaigns) == 5

    def test_returns_list_of_dicts(self, store: MockDataStore) -> None:
        campaigns = store.get_all_campaigns()
        assert all(isinstance(c, dict) for c in campaigns)

    def test_contains_all_campaign_ids(self, store: MockDataStore) -> None:
        campaigns = store.get_all_campaigns()
        ids = {c["campaign_id"] for c in campaigns}
        assert ids == {"C001", "C002", "C003", "C004", "C005"}

    def test_returns_new_list_each_call(self, store: MockDataStore) -> None:
        first = store.get_all_campaigns()
        second = store.get_all_campaigns()
        assert first is not second

    def test_modifying_result_does_not_affect_store(
        self, store: MockDataStore
    ) -> None:
        first = store.get_all_campaigns()
        first.clear()
        assert len(store.get_all_campaigns()) == 5


# ---------------------------------------------------------------------------
# get_similarity_index
# ---------------------------------------------------------------------------


class TestGetSimilarityIndex:
    def test_known_reference_returns_entries(self, store: MockDataStore) -> None:
        pairs = store.get_similarity_index("C001")
        assert len(pairs) > 0

    def test_all_entries_have_matching_campaign_id(
        self, store: MockDataStore
    ) -> None:
        pairs = store.get_similarity_index("C001")
        assert all(p["campaign_id"] == "C001" for p in pairs)

    def test_unknown_reference_returns_empty(self, store: MockDataStore) -> None:
        assert store.get_similarity_index("UNKNOWN") == []

    def test_entries_have_required_fields(self, store: MockDataStore) -> None:
        pairs = store.get_similarity_index("C002")
        for pair in pairs:
            for field in (
                "campaign_id",
                "similar_campaign_id",
                "campaign_name",
                "matching_dimensions",
                "dimension_count",
                "similarity_score",
                "take_up_rate",
                "total_leads",
                "total_take_up",
            ):
                assert field in pair, f"Missing field '{field}' in similarity pair"

    def test_returns_new_list_each_call(self, store: MockDataStore) -> None:
        first = store.get_similarity_index("C001")
        second = store.get_similarity_index("C001")
        assert first is not second


# ---------------------------------------------------------------------------
# get_trend_data
# ---------------------------------------------------------------------------


class TestGetTrendData:
    def test_known_campaign_returns_entries(self, store: MockDataStore) -> None:
        trend = store.get_trend_data("C001")
        assert len(trend) > 0

    def test_at_least_four_entries_per_campaign(self, store: MockDataStore) -> None:
        """Requirement 2.8: each campaign has at least 4 trend entries."""
        for cid in ["C001", "C002", "C003", "C004", "C005"]:
            trend = store.get_trend_data(cid)
            assert len(trend) >= 4, f"Campaign {cid} has fewer than 4 trend entries"

    def test_unknown_campaign_returns_empty(self, store: MockDataStore) -> None:
        assert store.get_trend_data("UNKNOWN") == []

    def test_entries_have_required_fields(self, store: MockDataStore) -> None:
        trend = store.get_trend_data("C001")
        for entry in trend:
            for field in (
                "period_start",
                "period_end",
                "total_leads",
                "total_take_up",
                "take_up_rate",
            ):
                assert field in entry, f"Missing field '{field}' in trend entry"

    def test_chronological_order(self, store: MockDataStore) -> None:
        """period_start values should be in non-decreasing order."""
        trend = store.get_trend_data("C001")
        for i in range(len(trend) - 1):
            assert trend[i]["period_start"] <= trend[i + 1]["period_start"]

    def test_returns_new_list_each_call(self, store: MockDataStore) -> None:
        first = store.get_trend_data("C001")
        second = store.get_trend_data("C001")
        assert first is not second


# ---------------------------------------------------------------------------
# get_regional_weekly
# ---------------------------------------------------------------------------


class TestGetRegionalWeekly:
    def test_known_campaign_returns_entries(self, store: MockDataStore) -> None:
        entries = store.get_regional_weekly("C001")
        assert len(entries) > 0

    def test_unknown_campaign_returns_empty(self, store: MockDataStore) -> None:
        assert store.get_regional_weekly("UNKNOWN") == []

    def test_entries_have_required_fields(self, store: MockDataStore) -> None:
        entries = store.get_regional_weekly("C001")
        for entry in entries:
            for field in (
                "wilayah",
                "week_start",
                "leads_count",
                "take_up_count",
                "take_up_rate",
            ):
                assert field in entry, f"Missing field '{field}' in regional entry"

    def test_wilayah_values_are_integers(self, store: MockDataStore) -> None:
        entries = store.get_regional_weekly("C001")
        assert all(isinstance(e["wilayah"], int) for e in entries)

    def test_returns_new_list_each_call(self, store: MockDataStore) -> None:
        first = store.get_regional_weekly("C001")
        second = store.get_regional_weekly("C001")
        assert first is not second

    def test_all_campaigns_have_regional_data(self, store: MockDataStore) -> None:
        for cid in ["C001", "C002", "C003", "C004", "C005"]:
            entries = store.get_regional_weekly(cid)
            assert len(entries) > 0, f"Campaign {cid} has no regional weekly data"
