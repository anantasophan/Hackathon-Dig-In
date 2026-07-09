"""Unit tests for backend/shared/calculations.py."""

import pytest
from datetime import date

from shared.calculations import (
    calculate_take_up_rate,
    compute_time_to_take_up,
    compute_statistics,
    compute_distribution_percentages,
    select_granularity,
)


# ---------------------------------------------------------------------------
# calculate_take_up_rate
# ---------------------------------------------------------------------------

class TestCalculateTakeUpRate:
    def test_typical_conversion(self):
        assert calculate_take_up_rate(200, 50) == pytest.approx(25.0)

    def test_full_conversion(self):
        assert calculate_take_up_rate(100, 100) == pytest.approx(100.0)

    def test_zero_take_up_returns_zero(self):
        assert calculate_take_up_rate(500, 0) == 0.0

    def test_single_lead_converted(self):
        assert calculate_take_up_rate(1, 1) == pytest.approx(100.0)

    def test_raises_if_total_leads_is_zero(self):
        with pytest.raises(ValueError):
            calculate_take_up_rate(0, 0)

    def test_raises_if_total_leads_is_negative(self):
        with pytest.raises(ValueError):
            calculate_take_up_rate(-10, 5)

    def test_fractional_percentage(self):
        result = calculate_take_up_rate(3, 1)
        assert result == pytest.approx(100 / 3)


# ---------------------------------------------------------------------------
# compute_time_to_take_up
# ---------------------------------------------------------------------------

class TestComputeTimeToTakeUp:
    def test_same_day(self):
        d = date(2024, 1, 15)
        assert compute_time_to_take_up(d, d) == 0

    def test_one_day_later(self):
        assert compute_time_to_take_up(date(2024, 1, 1), date(2024, 1, 2)) == 1

    def test_thirty_days_later(self):
        assert compute_time_to_take_up(date(2024, 1, 1), date(2024, 1, 31)) == 30

    def test_cross_month_boundary(self):
        assert compute_time_to_take_up(date(2024, 1, 31), date(2024, 2, 1)) == 1

    def test_cross_year_boundary(self):
        assert compute_time_to_take_up(date(2023, 12, 31), date(2024, 1, 1)) == 1

    def test_raises_if_take_up_before_distribution(self):
        with pytest.raises(ValueError):
            compute_time_to_take_up(date(2024, 6, 1), date(2024, 5, 31))


# ---------------------------------------------------------------------------
# compute_statistics
# ---------------------------------------------------------------------------

class TestComputeStatistics:
    def test_single_element(self):
        result = compute_statistics([42])
        assert result == {"min": 42.0, "max": 42.0, "mean": 42.0, "median": 42.0}

    def test_two_elements_median_is_average(self):
        result = compute_statistics([1, 3])
        assert result["median"] == pytest.approx(2.0)

    def test_odd_count_median_is_middle(self):
        result = compute_statistics([1, 2, 3, 4, 5])
        assert result["median"] == pytest.approx(3.0)

    def test_even_count_median(self):
        result = compute_statistics([1, 2, 3, 4])
        assert result["median"] == pytest.approx(2.5)

    def test_unsorted_input(self):
        result = compute_statistics([5, 1, 3])
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["mean"] == pytest.approx(3.0)
        assert result["median"] == pytest.approx(3.0)

    def test_all_same_values(self):
        result = compute_statistics([7, 7, 7, 7])
        assert result == {"min": 7.0, "max": 7.0, "mean": 7.0, "median": 7.0}

    def test_raises_if_empty(self):
        with pytest.raises(ValueError):
            compute_statistics([])

    def test_mean_calculation(self):
        result = compute_statistics([10, 20, 30])
        assert result["mean"] == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# compute_distribution_percentages
# ---------------------------------------------------------------------------

class TestComputeDistributionPercentages:
    def test_equal_groups(self):
        result = compute_distribution_percentages({"A": 1, "B": 1, "C": 1, "D": 1})
        assert result == pytest.approx({"A": 25.0, "B": 25.0, "C": 25.0, "D": 25.0})

    def test_sums_to_100(self):
        groups = {"X": 333, "Y": 333, "Z": 334}
        result = compute_distribution_percentages(groups)
        assert sum(result.values()) == pytest.approx(100.0, abs=1e-9)

    def test_single_group(self):
        result = compute_distribution_percentages({"only": 100})
        assert result == {"only": 100.0}

    def test_two_groups_uneven(self):
        result = compute_distribution_percentages({"A": 1, "B": 3})
        assert result["A"] == pytest.approx(25.0)
        assert result["B"] == pytest.approx(75.0)
        assert sum(result.values()) == pytest.approx(100.0)

    def test_raises_if_total_zero(self):
        with pytest.raises(ValueError):
            compute_distribution_percentages({"A": 0, "B": 0})

    def test_exact_100_sum_with_repeating_decimal(self):
        # 1/3 each produces repeating decimals; last group absorbs rounding
        groups = {"A": 1, "B": 1, "C": 1}
        result = compute_distribution_percentages(groups)
        assert sum(result.values()) == pytest.approx(100.0, abs=1e-9)

    def test_preserves_group_names(self):
        groups = {"north": 200, "south": 300, "east": 500}
        result = compute_distribution_percentages(groups)
        assert set(result.keys()) == {"north", "south", "east"}


# ---------------------------------------------------------------------------
# select_granularity
# ---------------------------------------------------------------------------

class TestSelectGranularity:
    def test_same_day_is_weekly(self):
        d = date(2024, 1, 1)
        assert select_granularity(d, d) == "weekly"

    def test_90_days_is_weekly(self):
        start = date(2024, 1, 1)
        end = date(2024, 4, 1)  # exactly 91 days — should be monthly
        # 90-day boundary
        end_90 = date(2024, 4, 1)
        # Let's compute manually: 2024-01-01 to 2024-04-01 = 91 days (monthly)
        # Use 2024-01-01 to 2024-03-31 = 90 days (weekly)
        end_90 = date(2024, 3, 31)
        assert select_granularity(start, end_90) == "weekly"

    def test_91_days_is_monthly(self):
        start = date(2024, 1, 1)
        end = date(2024, 4, 1)  # 91 days
        assert select_granularity(start, end) == "monthly"

    def test_one_day_is_weekly(self):
        assert select_granularity(date(2024, 6, 1), date(2024, 6, 2)) == "weekly"

    def test_one_year_is_monthly(self):
        assert select_granularity(date(2023, 1, 1), date(2024, 1, 1)) == "monthly"

    def test_raises_if_end_before_start(self):
        with pytest.raises(ValueError):
            select_granularity(date(2024, 6, 1), date(2024, 5, 31))
