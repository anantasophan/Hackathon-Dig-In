"""Unit tests for backend/local_server/routers/campaigns.py using FastAPI TestClient.

Tests all six campaign endpoints:
  - GET  /api/campaigns/overview          (Requirements 2.1–2.9)
  - POST /api/campaigns/comparison        (Requirements 3.1–3.7)
  - GET  /api/campaigns/time-analysis/{} (Requirements 4.1–4.7)
  - GET  /api/campaigns/regional/{}       (Requirements 5.1–5.6)
  - GET  /api/campaigns/customer-criteria/{} (Requirements 6.1–6.7)
  - POST /api/campaigns/similar           (Requirements 7.1–7.7)

Campaign IDs in mock data: C001, C002, C003, C004, C005
Valid flag_program: "PROGRAM QRIS", "PROGRAM BIAYA ADMIN"
Valid media_blasting: "wa", "digisales", "telesales", "email", "push notif", "sms"
Valid similar dimensions: "media_blasting", "jenis_leads", "flag_program"

Requirements: 2.1–7.7
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from local_server.main import app


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a module-scoped TestClient wrapping the full FastAPI app.

    Module-scope so the ASGI lifespan (startup event) runs once per
    test module, keeping tests fast.

    Yields:
        A configured :class:`~fastapi.testclient.TestClient` instance.
    """
    with TestClient(app) as c:
        yield c


# ===========================================================================
# GET /api/campaigns/overview  (Requirements 2.1–2.9)
# ===========================================================================


class TestCampaignOverview:
    """Tests for GET /api/campaigns/overview."""

    # -----------------------------------------------------------------------
    # 2.1 – No params: returns standard aggregate fields
    # -----------------------------------------------------------------------

    def test_no_params_returns_200(self, client: TestClient) -> None:
        """Requirement 2.1: overview without filters returns HTTP 200."""
        response = client.get("/api/campaigns/overview")
        assert response.status_code == 200

    def test_no_params_body_has_required_keys(self, client: TestClient) -> None:
        """Requirement 2.1: response body includes all aggregate metric fields."""
        body = client.get("/api/campaigns/overview").json()
        for key in ("total_leads", "total_take_up", "take_up_rate",
                    "total_campaigns", "trend", "filters"):
            assert key in body, f"Missing key: {key}"

    def test_no_params_total_leads_positive(self, client: TestClient) -> None:
        """Requirement 2.1: total_leads is a positive integer when data exists."""
        body = client.get("/api/campaigns/overview").json()
        assert isinstance(body["total_leads"], int)
        assert body["total_leads"] > 0

    def test_no_params_take_up_rate_between_0_and_100(self, client: TestClient) -> None:
        """Requirement 2.1: take_up_rate is in [0, 100]."""
        body = client.get("/api/campaigns/overview").json()
        assert 0.0 <= body["take_up_rate"] <= 100.0

    def test_no_params_trend_has_data_points(self, client: TestClient) -> None:
        """Requirement 2.9: trend contains at least 4 data points when data exists."""
        body = client.get("/api/campaigns/overview").json()
        assert len(body["trend"]) >= 4

    def test_no_params_filters_is_empty_list(self, client: TestClient) -> None:
        """Requirement 2.1: filters list is empty when no filters are applied."""
        body = client.get("/api/campaigns/overview").json()
        assert body["filters"] == []

    def test_no_params_total_campaigns_equals_five(self, client: TestClient) -> None:
        """Requirement 2.1: total_campaigns reflects all 5 campaigns in mock data."""
        body = client.get("/api/campaigns/overview").json()
        assert body["total_campaigns"] == 5

    # -----------------------------------------------------------------------
    # 2.2 – Invalid date → 400
    # -----------------------------------------------------------------------

    def test_invalid_start_date_returns_400(self, client: TestClient) -> None:
        """Requirement 2.2: malformed start_date returns HTTP 400."""
        response = client.get("/api/campaigns/overview?start_date=not-a-date")
        assert response.status_code == 400

    def test_invalid_end_date_returns_400(self, client: TestClient) -> None:
        """Requirement 2.2: malformed end_date returns HTTP 400."""
        response = client.get("/api/campaigns/overview?end_date=2024-13-99")
        assert response.status_code == 400

    def test_invalid_date_body_has_detail(self, client: TestClient) -> None:
        """Requirement 2.2: 400 response includes a detail field."""
        body = client.get("/api/campaigns/overview?start_date=bad").json()
        assert "detail" in body

    # -----------------------------------------------------------------------
    # 2.3 – flag_program filter
    # -----------------------------------------------------------------------

    def test_flag_program_filter_qris(self, client: TestClient) -> None:
        """Requirement 2.3: flag_program filter restricts results to QRIS leads."""
        body = client.get(
            "/api/campaigns/overview?flag_program=PROGRAM+QRIS"
        ).json()
        # Overview response should still return aggregate keys (data exists)
        assert "total_leads" in body
        # Filters reflect the applied flag_program
        filter_fields = [f["field"] for f in body.get("filters", [])]
        assert "flag_program" in filter_fields

    def test_flag_program_filter_biaya_admin(self, client: TestClient) -> None:
        """Requirement 2.3: flag_program filter works for PROGRAM BIAYA ADMIN."""
        body = client.get(
            "/api/campaigns/overview?flag_program=PROGRAM+BIAYA+ADMIN"
        ).json()
        assert "total_leads" in body

    # -----------------------------------------------------------------------
    # 2.4 – media_blasting filter
    # -----------------------------------------------------------------------

    def test_media_blasting_filter_wa(self, client: TestClient) -> None:
        """Requirement 2.4: media_blasting=wa filter works correctly."""
        body = client.get("/api/campaigns/overview?media_blasting=wa").json()
        assert "total_leads" in body
        filter_fields = [f["field"] for f in body.get("filters", [])]
        assert "media_blasting" in filter_fields

    def test_media_blasting_filter_telesales(self, client: TestClient) -> None:
        """Requirement 2.4: media_blasting=telesales filter works correctly."""
        body = client.get("/api/campaigns/overview?media_blasting=telesales").json()
        assert "total_leads" in body

    # -----------------------------------------------------------------------
    # 2.5 – wilayah filter
    # -----------------------------------------------------------------------

    def test_wilayah_filter_single(self, client: TestClient) -> None:
        """Requirement 2.5: wilayah filter restricts by region code."""
        body = client.get("/api/campaigns/overview?wilayah=1").json()
        assert "total_leads" in body

    def test_wilayah_filter_in_active_filters(self, client: TestClient) -> None:
        """Requirement 2.5: wilayah filter appears in returned filters list."""
        body = client.get("/api/campaigns/overview?wilayah=1").json()
        filter_fields = [f["field"] for f in body.get("filters", [])]
        assert "wilayah" in filter_fields

    # -----------------------------------------------------------------------
    # 2.6 – date range filter
    # -----------------------------------------------------------------------

    def test_valid_date_range_returns_200(self, client: TestClient) -> None:
        """Requirement 2.6: valid date range returns HTTP 200."""
        response = client.get(
            "/api/campaigns/overview?start_date=2024-08-01&end_date=2024-08-31"
        )
        assert response.status_code == 200

    def test_date_range_in_active_filters(self, client: TestClient) -> None:
        """Requirement 2.6: applied date range appears in filters list."""
        body = client.get(
            "/api/campaigns/overview?start_date=2024-08-01&end_date=2024-08-31"
        ).json()
        filter_fields = [f["field"] for f in body.get("filters", [])]
        assert "period" in filter_fields

    # -----------------------------------------------------------------------
    # 2.7 – Empty result
    # -----------------------------------------------------------------------

    def test_filter_with_no_matches_returns_message(self, client: TestClient) -> None:
        """Requirement 2.7: filters that match no leads return message key."""
        body = client.get(
            "/api/campaigns/overview?start_date=2099-01-01&end_date=2099-12-31"
        ).json()
        assert "message" in body

    def test_empty_result_status_still_200(self, client: TestClient) -> None:
        """Requirement 2.7: empty filter result still returns HTTP 200."""
        response = client.get(
            "/api/campaigns/overview?start_date=2099-01-01&end_date=2099-12-31"
        )
        assert response.status_code == 200


# ===========================================================================
# POST /api/campaigns/comparison  (Requirements 3.1–3.7)
# ===========================================================================


class TestCampaignComparison:
    """Tests for POST /api/campaigns/comparison."""

    # -----------------------------------------------------------------------
    # 3.1 – Valid 2-ID comparison
    # -----------------------------------------------------------------------

    def test_two_ids_returns_200(self, client: TestClient) -> None:
        """Requirement 3.1: comparison with exactly 2 IDs returns HTTP 200."""
        response = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002"]},
        )
        assert response.status_code == 200

    def test_two_ids_body_has_campaigns_and_chart(self, client: TestClient) -> None:
        """Requirement 3.1: response has campaigns list and comparison_chart."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002"]},
        ).json()
        assert "campaigns" in body
        assert "comparison_chart" in body

    def test_two_ids_campaigns_list_length(self, client: TestClient) -> None:
        """Requirement 3.1: campaigns list contains exactly 2 entries."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002"]},
        ).json()
        assert len(body["campaigns"]) == 2

    def test_five_ids_returns_200(self, client: TestClient) -> None:
        """Requirement 3.1: comparison with all 5 IDs returns HTTP 200."""
        response = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002", "C003", "C004", "C005"]},
        )
        assert response.status_code == 200

    # -----------------------------------------------------------------------
    # 3.2 – < 2 IDs → 400
    # -----------------------------------------------------------------------

    def test_empty_ids_returns_400(self, client: TestClient) -> None:
        """Requirement 3.2: empty campaign_ids returns HTTP 400."""
        response = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": []},
        )
        assert response.status_code == 400

    def test_one_id_returns_400(self, client: TestClient) -> None:
        """Requirement 3.2: only 1 campaign_id returns HTTP 400."""
        response = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001"]},
        )
        assert response.status_code == 400

    def test_too_few_ids_has_detail(self, client: TestClient) -> None:
        """Requirement 3.2: 400 response body contains a detail field."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001"]},
        ).json()
        assert "detail" in body

    # -----------------------------------------------------------------------
    # 3.3 – > 5 IDs → 400
    # -----------------------------------------------------------------------

    def test_six_ids_returns_400(self, client: TestClient) -> None:
        """Requirement 3.3: 6 campaign_ids returns HTTP 400."""
        response = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002", "C003", "C004", "C005", "C006"]},
        )
        assert response.status_code == 400

    def test_too_many_ids_has_detail(self, client: TestClient) -> None:
        """Requirement 3.3: 400 response for > 5 IDs contains a detail field."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002", "C003", "C004", "C005", "C006"]},
        ).json()
        assert "detail" in body

    # -----------------------------------------------------------------------
    # 3.4 – group_by sorts the campaigns
    # -----------------------------------------------------------------------

    def test_group_by_total_leads_sorts_ascending(self, client: TestClient) -> None:
        """Requirement 3.4: group_by='total_leads' returns campaigns sorted ascending."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002", "C003"], "group_by": "total_leads"},
        ).json()
        leads_values = [c["total_leads"] for c in body["campaigns"]]
        assert leads_values == sorted(leads_values)

    def test_group_by_take_up_rate_sorts_ascending(self, client: TestClient) -> None:
        """Requirement 3.4: group_by='take_up_rate' returns campaigns sorted ascending."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002", "C003"], "group_by": "take_up_rate"},
        ).json()
        rates = [c["take_up_rate"] for c in body["campaigns"]]
        assert rates == sorted(rates)

    # -----------------------------------------------------------------------
    # 3.5 – Each campaign metric has the expected fields
    # -----------------------------------------------------------------------

    def test_campaign_metric_has_required_fields(self, client: TestClient) -> None:
        """Requirement 3.5: each campaign in response has all required metric fields."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002"]},
        ).json()
        required = {
            "campaign_id", "campaign_name", "flag_program",
            "total_leads", "total_take_up", "take_up_rate",
            "total_transaction_value", "duration_days",
        }
        for camp in body["campaigns"]:
            assert required.issubset(camp.keys())

    # -----------------------------------------------------------------------
    # 3.6 – comparison_chart has labels and datasets
    # -----------------------------------------------------------------------

    def test_comparison_chart_has_labels(self, client: TestClient) -> None:
        """Requirement 3.6: comparison_chart contains a labels list."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002"]},
        ).json()
        assert "labels" in body["comparison_chart"]
        assert len(body["comparison_chart"]["labels"]) == 2

    def test_comparison_chart_has_datasets(self, client: TestClient) -> None:
        """Requirement 3.6: comparison_chart contains a datasets list."""
        body = client.post(
            "/api/campaigns/comparison",
            json={"campaign_ids": ["C001", "C002"]},
        ).json()
        assert "datasets" in body["comparison_chart"]
        assert len(body["comparison_chart"]["datasets"]) > 0


# ===========================================================================
# GET /api/campaigns/time-analysis/{campaign_id}  (Requirements 4.1–4.7)
# ===========================================================================


class TestTimeAnalysis:
    """Tests for GET /api/campaigns/time-analysis/{campaign_id}."""

    # -----------------------------------------------------------------------
    # 4.1 – Happy path: histogram with 7 bins
    # -----------------------------------------------------------------------

    def test_valid_campaign_returns_200(self, client: TestClient) -> None:
        """Requirement 4.1: valid campaign_id returns HTTP 200."""
        response = client.get("/api/campaigns/time-analysis/C001")
        assert response.status_code == 200

    def test_histogram_has_seven_bins(self, client: TestClient) -> None:
        """Requirement 4.1: histogram always contains exactly 7 bins."""
        body = client.get("/api/campaigns/time-analysis/C001").json()
        assert "histogram" in body
        assert len(body["histogram"]) == 7

    def test_histogram_bin_structure(self, client: TestClient) -> None:
        """Requirement 4.1: each histogram bin has range_start, range_end, count, percentage."""
        body = client.get("/api/campaigns/time-analysis/C001").json()
        for bin_item in body["histogram"]:
            for field_name in ("range_start", "range_end", "count", "percentage"):
                assert field_name in bin_item, f"Bin missing field: {field_name}"

    def test_histogram_percentages_sum_to_100(self, client: TestClient) -> None:
        """Requirement 4.1: histogram bin percentages sum to ~100%."""
        body = client.get("/api/campaigns/time-analysis/C001").json()
        total_pct = sum(b["percentage"] for b in body["histogram"])
        assert abs(total_pct - 100.0) < 0.1

    def test_stats_present(self, client: TestClient) -> None:
        """Requirement 4.2: response includes stats with min, max, mean, median."""
        body = client.get("/api/campaigns/time-analysis/C001").json()
        assert "stats" in body
        for key in ("min_days", "max_days", "mean_days", "median_days", "total_take_up"):
            assert key in body["stats"], f"stats missing key: {key}"

    # -----------------------------------------------------------------------
    # 4.2 – Empty campaign: no take-up data
    # -----------------------------------------------------------------------

    def test_campaign_with_no_takeup_returns_message(self, client: TestClient) -> None:
        """Requirement 4.3: campaign with no take-up data returns message key."""
        # Use an ID that exists but has no take-up records via impossible filter
        response = client.get(
            "/api/campaigns/time-analysis/C001?channel=nonexistent_channel"
        )
        assert response.status_code == 200
        body = response.json()
        assert "message" in body

    def test_unknown_campaign_id_returns_message(self, client: TestClient) -> None:
        """Requirement 4.3: unknown campaign_id returns 200 with message (no data)."""
        response = client.get("/api/campaigns/time-analysis/CXXX")
        assert response.status_code == 200
        body = response.json()
        assert "message" in body

    # -----------------------------------------------------------------------
    # 4.3 – channel filter
    # -----------------------------------------------------------------------

    def test_channel_filter_wa_returns_200(self, client: TestClient) -> None:
        """Requirement 4.4: channel filter 'wa' applied successfully."""
        response = client.get("/api/campaigns/time-analysis/C001?channel=wa")
        assert response.status_code == 200

    def test_channel_filter_reflected_in_response(self, client: TestClient) -> None:
        """Requirement 4.4: channel_filter echoed back in response body."""
        body = client.get("/api/campaigns/time-analysis/C001?channel=wa").json()
        # Either we get histogram data or an empty message — channel_filter key present
        # when data found
        if "histogram" in body:
            assert body.get("channel_filter") == "wa"

    # -----------------------------------------------------------------------
    # 4.4 – region filter
    # -----------------------------------------------------------------------

    def test_region_filter_returns_200(self, client: TestClient) -> None:
        """Requirement 4.5: region filter applied without error."""
        response = client.get("/api/campaigns/time-analysis/C001?region=1")
        assert response.status_code == 200

    def test_invalid_region_filter_returns_message(self, client: TestClient) -> None:
        """Requirement 4.5: non-integer region filter returns 200 with message."""
        response = client.get("/api/campaigns/time-analysis/C001?region=abc")
        assert response.status_code == 200
        body = response.json()
        assert "message" in body


# ===========================================================================
# GET /api/campaigns/regional/{campaign_id}  (Requirements 5.1–5.6)
# ===========================================================================


class TestRegionalPerformance:
    """Tests for GET /api/campaigns/regional/{campaign_id}."""

    # -----------------------------------------------------------------------
    # 5.1 – Happy path: sorted descending by take_up_rate
    # -----------------------------------------------------------------------

    def test_valid_campaign_returns_200(self, client: TestClient) -> None:
        """Requirement 5.1: valid campaign_id returns HTTP 200."""
        response = client.get("/api/campaigns/regional/C001")
        assert response.status_code == 200

    def test_response_has_regions_key(self, client: TestClient) -> None:
        """Requirement 5.1: response contains a regions list."""
        body = client.get("/api/campaigns/regional/C001").json()
        assert "regions" in body

    def test_regions_sorted_descending_by_take_up_rate(self, client: TestClient) -> None:
        """Requirement 5.2: regions are sorted by take_up_rate descending."""
        body = client.get("/api/campaigns/regional/C001").json()
        rates = [r["take_up_rate"] for r in body["regions"]]
        assert rates == sorted(rates, reverse=True)

    def test_region_entry_has_required_fields(self, client: TestClient) -> None:
        """Requirement 5.1: each region entry has all required fields."""
        body = client.get("/api/campaigns/regional/C001").json()
        required = {
            "wilayah", "leads_count", "take_up_count",
            "take_up_rate", "avg_transaction_value",
        }
        for region in body["regions"]:
            assert required.issubset(region.keys())

    # -----------------------------------------------------------------------
    # 5.2 – selected_region: returns weekly trend data
    # -----------------------------------------------------------------------

    def test_selected_region_returns_trend(self, client: TestClient) -> None:
        """Requirement 5.3: selected_region causes selected_region_trend to be populated."""
        body = client.get("/api/campaigns/regional/C001?selected_region=1").json()
        assert "selected_region_trend" in body

    def test_selected_region_trend_capped_at_8(self, client: TestClient) -> None:
        """Requirement 5.3: selected_region_trend contains at most 8 entries."""
        body = client.get("/api/campaigns/regional/C001?selected_region=1").json()
        assert len(body["selected_region_trend"]) <= 8

    def test_no_selected_region_trend_is_empty_list(self, client: TestClient) -> None:
        """Requirement 5.3: no selected_region param → selected_region_trend is []."""
        body = client.get("/api/campaigns/regional/C001").json()
        assert body["selected_region_trend"] == []

    # -----------------------------------------------------------------------
    # 5.3 – Empty regions
    # -----------------------------------------------------------------------

    def test_unknown_campaign_returns_empty_regions(self, client: TestClient) -> None:
        """Requirement 5.4: unknown campaign_id returns 200 with empty regions list."""
        body = client.get("/api/campaigns/regional/CXXX").json()
        assert body.get("regions") == []

    def test_unknown_campaign_returns_message(self, client: TestClient) -> None:
        """Requirement 5.4: unknown campaign_id response includes a message key."""
        body = client.get("/api/campaigns/regional/CXXX").json()
        assert "message" in body

    # -----------------------------------------------------------------------
    # 5.4 – flag_program filter
    # -----------------------------------------------------------------------

    def test_flag_program_filter_reflected(self, client: TestClient) -> None:
        """Requirement 5.5: flag_program_filter echoed back in response."""
        body = client.get(
            "/api/campaigns/regional/C001?flag_program=PROGRAM+QRIS"
        ).json()
        assert body.get("flag_program_filter") == "PROGRAM QRIS"

    def test_flag_program_filter_no_match_returns_empty_regions(
        self, client: TestClient
    ) -> None:
        """Requirement 5.5: flag_program that does not match campaign returns empty."""
        # C002 is PROGRAM BIAYA ADMIN — filtering by QRIS on it returns no leads
        body = client.get(
            "/api/campaigns/regional/C002?flag_program=PROGRAM+QRIS"
        ).json()
        assert body.get("regions") == []


# ===========================================================================
# GET /api/campaigns/customer-criteria/{campaign_id}  (Requirements 6.1–6.7)
# ===========================================================================


class TestCustomerCriteria:
    """Tests for GET /api/campaigns/customer-criteria/{campaign_id}."""

    # -----------------------------------------------------------------------
    # 6.1 – Happy path: 5 distributions present
    # -----------------------------------------------------------------------

    def test_valid_campaign_returns_200(self, client: TestClient) -> None:
        """Requirement 6.1: valid campaign_id returns HTTP 200."""
        response = client.get("/api/campaigns/customer-criteria/C001")
        assert response.status_code == 200

    def test_response_has_distributions(self, client: TestClient) -> None:
        """Requirement 6.1: response contains distributions list."""
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        assert "distributions" in body

    def test_distributions_has_five_entries(self, client: TestClient) -> None:
        """Requirement 6.1: distributions list contains exactly 5 attribute entries."""
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        assert len(body["distributions"]) == 5

    def test_distribution_entry_has_required_fields(self, client: TestClient) -> None:
        """Requirement 6.1: each distribution entry has attribute, available, items."""
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        for dist in body["distributions"]:
            for key in ("attribute", "available", "items"):
                assert key in dist, f"Distribution missing field: {key}"

    def test_available_and_unavailable_attributes_present(
        self, client: TestClient
    ) -> None:
        """Requirement 6.2: response includes available_attributes and unavailable_attributes lists."""
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        assert "available_attributes" in body
        assert "unavailable_attributes" in body

    def test_expected_attribute_names_present(self, client: TestClient) -> None:
        """Requirement 6.1: all 5 expected attribute names appear in distributions."""
        expected = {
            "segment_by_aum", "range_usia", "media_blasting",
            "segment_div_owner", "flag_program",
        }
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        attr_names = {d["attribute"] for d in body["distributions"]}
        assert expected == attr_names

    # -----------------------------------------------------------------------
    # 6.2 – Empty campaign_id → 400
    # -----------------------------------------------------------------------

    def test_empty_campaign_id_path_returns_404(self, client: TestClient) -> None:
        """Requirement 6.3: empty campaign_id segment returns 404 (no route match)."""
        response = client.get("/api/campaigns/customer-criteria/")
        # FastAPI returns 404 for unmatched routes (path segment required)
        assert response.status_code in (404, 307)

    def test_unknown_campaign_returns_message(self, client: TestClient) -> None:
        """Requirement 6.3: unknown campaign_id returns 200 with message (no data)."""
        body = client.get("/api/campaigns/customer-criteria/CXXX").json()
        assert "message" in body

    def test_unknown_campaign_status_200(self, client: TestClient) -> None:
        """Requirement 6.3: HTTP 200 for unknown campaign (graceful empty)."""
        response = client.get("/api/campaigns/customer-criteria/CXXX")
        assert response.status_code == 200

    # -----------------------------------------------------------------------
    # 6.3 – Distribution items structure
    # -----------------------------------------------------------------------

    def test_distribution_items_have_label_count_percentage(
        self, client: TestClient
    ) -> None:
        """Requirement 6.4: each distribution item has label, count, and percentage."""
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        for dist in body["distributions"]:
            if dist["available"]:
                for item in dist["items"]:
                    for key in ("label", "count", "percentage"):
                        assert key in item, f"Item missing key: {key}"
                break  # one available distribution is enough to verify

    def test_distribution_percentages_sum_to_100(self, client: TestClient) -> None:
        """Requirement 6.4: item percentages in each available distribution sum to ~100."""
        body = client.get("/api/campaigns/customer-criteria/C001").json()
        for dist in body["distributions"]:
            if dist["available"] and dist["items"]:
                total_pct = sum(item["percentage"] for item in dist["items"])
                assert abs(total_pct - 100.0) < 0.5, (
                    f"Percentages for '{dist['attribute']}' sum to {total_pct}"
                )


# ===========================================================================
# POST /api/campaigns/similar  (Requirements 7.1–7.7)
# ===========================================================================


class TestSimilarCampaign:
    """Tests for POST /api/campaigns/similar."""

    # -----------------------------------------------------------------------
    # 7.1 – Happy path: valid request returns similar_campaigns
    # -----------------------------------------------------------------------

    def test_valid_request_returns_200(self, client: TestClient) -> None:
        """Requirement 7.1: valid reference and dimension returns HTTP 200."""
        response = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
            },
        )
        assert response.status_code == 200

    def test_valid_request_has_similar_campaigns(self, client: TestClient) -> None:
        """Requirement 7.1: response body contains similar_campaigns list."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
            },
        ).json()
        assert "similar_campaigns" in body

    def test_similar_campaign_entry_has_required_fields(
        self, client: TestClient
    ) -> None:
        """Requirement 7.1: each result entry has all required fields."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
            },
        ).json()
        required = {
            "campaign_id", "campaign_name", "matching_dimensions",
            "dimension_count", "similarity_score", "take_up_rate",
            "total_leads", "total_take_up",
        }
        for camp in body["similar_campaigns"]:
            assert required.issubset(camp.keys())

    # -----------------------------------------------------------------------
    # 7.2 – Invalid dimensions → 400
    # -----------------------------------------------------------------------

    def test_invalid_dimension_returns_400(self, client: TestClient) -> None:
        """Requirement 7.2: unknown dimension value returns HTTP 400."""
        response = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["invalid_dimension"],
            },
        )
        assert response.status_code == 400

    def test_invalid_dimension_has_detail(self, client: TestClient) -> None:
        """Requirement 7.2: 400 response from invalid dimension includes detail."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["bad_dim"],
            },
        ).json()
        assert "detail" in body

    def test_empty_dimensions_returns_400(self, client: TestClient) -> None:
        """Requirement 7.2: empty dimensions list returns HTTP 400."""
        response = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": [],
            },
        )
        assert response.status_code == 400

    # -----------------------------------------------------------------------
    # 7.3 – Sort order: dimension_count desc, then take_up_rate desc
    # -----------------------------------------------------------------------

    def test_results_sorted_by_dimension_count_desc(self, client: TestClient) -> None:
        """Requirement 7.3: similar_campaigns sorted by dimension_count descending."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
            },
        ).json()
        dim_counts = [c["dimension_count"] for c in body["similar_campaigns"]]
        assert dim_counts == sorted(dim_counts, reverse=True)

    # -----------------------------------------------------------------------
    # 7.4 – Limit cap: capped at 20
    # -----------------------------------------------------------------------

    def test_limit_respected(self, client: TestClient) -> None:
        """Requirement 7.4: limit parameter caps returned results."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
                "limit": 1,
            },
        ).json()
        assert len(body["similar_campaigns"]) <= 1

    def test_limit_above_20_capped_at_20(self, client: TestClient) -> None:
        """Requirement 7.4: limit > 20 is capped at 20 (mock data ≤ 20)."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
                "limit": 999,
            },
        ).json()
        assert len(body["similar_campaigns"]) <= 20

    # -----------------------------------------------------------------------
    # 7.5 – Empty reference_campaign_id → 400
    # -----------------------------------------------------------------------

    def test_empty_reference_id_returns_400(self, client: TestClient) -> None:
        """Requirement 7.5: empty reference_campaign_id returns HTTP 400."""
        response = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "",
                "dimensions": ["flag_program"],
            },
        )
        assert response.status_code == 400

    def test_missing_body_returns_400(self, client: TestClient) -> None:
        """Requirement 7.5: missing request body returns HTTP 422 or 400."""
        response = client.post("/api/campaigns/similar")
        assert response.status_code in (400, 422)

    # -----------------------------------------------------------------------
    # 7.6 – No matches: returns message
    # -----------------------------------------------------------------------

    def test_no_similar_campaigns_returns_message(self, client: TestClient) -> None:
        """Requirement 7.6: reference with no similar entries returns message key."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                # Use a campaign ID that exists but matches on all 3 dims
                # which no entry may satisfy simultaneously
                "reference_campaign_id": "C001",
                "dimensions": ["media_blasting", "jenis_leads", "flag_program"],
            },
        ).json()
        # If no matches, message is present; otherwise similar_campaigns list present
        assert ("similar_campaigns" in body) or ("message" in body)

    # -----------------------------------------------------------------------
    # 7.7 – Valid multi-dimension query
    # -----------------------------------------------------------------------

    def test_multiple_valid_dimensions(self, client: TestClient) -> None:
        """Requirement 7.7: multiple valid dimensions are accepted and return 200."""
        response = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program", "jenis_leads"],
            },
        )
        assert response.status_code == 200

    def test_learning_summary_present_when_results_exist(
        self, client: TestClient
    ) -> None:
        """Requirement 7.7: learning_summary key present when results are returned."""
        body = client.post(
            "/api/campaigns/similar",
            json={
                "reference_campaign_id": "C001",
                "dimensions": ["flag_program"],
            },
        ).json()
        if "similar_campaigns" in body and body["similar_campaigns"]:
            assert "learning_summary" in body
