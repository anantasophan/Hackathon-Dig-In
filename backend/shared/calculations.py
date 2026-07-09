"""Shared calculations module for Campaign Insight Generator.

Contains core metric calculation functions used across Lambda handlers.
No imports from shared/models.py to keep this module self-contained.
"""

from __future__ import annotations

from datetime import date


def calculate_take_up_rate(total_leads: int, total_take_up: int) -> float:
    """Calculate the take-up rate as a percentage.

    Args:
        total_leads: Total number of leads distributed.
        total_take_up: Number of leads that converted (took up the offer).

    Returns:
        Take-up rate as a percentage in the range [0.0, 100.0].

    Raises:
        ValueError: If total_leads is <= 0.
    """
    if total_leads <= 0:
        raise ValueError(
            f"total_leads must be greater than 0, got {total_leads}"
        )
    if total_take_up == 0:
        return 0.0
    return (total_take_up / total_leads) * 100


def compute_time_to_take_up(distribution_date: date, take_up_date: date) -> int:
    """Compute the number of calendar days from distribution to take-up.

    Args:
        distribution_date: The date leads were distributed.
        take_up_date: The date the lead took up the offer.

    Returns:
        Number of calendar days between the two dates (>= 0).

    Raises:
        ValueError: If take_up_date is earlier than distribution_date.
    """
    if take_up_date < distribution_date:
        raise ValueError(
            f"take_up_date ({take_up_date}) must not be before "
            f"distribution_date ({distribution_date})"
        )
    return (take_up_date - distribution_date).days


def compute_statistics(values: list[int]) -> dict[str, float]:
    """Compute basic descriptive statistics for a list of integer values.

    Args:
        values: Non-empty list of integer values.

    Returns:
        Dictionary with keys 'min', 'max', 'mean', and 'median'.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("values must not be empty")

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    minimum = float(sorted_vals[0])
    maximum = float(sorted_vals[-1])
    mean = sum(sorted_vals) / n

    mid = n // 2
    if n % 2 == 1:
        median = float(sorted_vals[mid])
    else:
        median = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

    return {
        "min": minimum,
        "max": maximum,
        "mean": mean,
        "median": median,
    }


def compute_distribution_percentages(
    groups: dict[str, int]
) -> dict[str, float]:
    """Compute percentage share for each group relative to the total count.

    Percentages are rounded to 4 decimal places and the last group is
    adjusted so that all percentages sum to exactly 100.0.

    Args:
        groups: Mapping of group name to its count (must be >= 0).

    Returns:
        Mapping of group name to percentage (0–100), summing to 100.0.

    Raises:
        ValueError: If the total count across all groups is 0.
    """
    total = sum(groups.values())
    if total == 0:
        raise ValueError("Total count across all groups must be greater than 0")

    keys = list(groups.keys())
    result: dict[str, float] = {}

    running_sum = 0.0
    for key in keys[:-1]:
        pct = round((groups[key] / total) * 100, 4)
        result[key] = pct
        running_sum += pct

    # Adjust the last group to ensure the sum is exactly 100.0
    last_key = keys[-1]
    result[last_key] = round(100.0 - running_sum, 4)

    return result


def select_granularity(start_date: date, end_date: date) -> str:
    """Select an appropriate time granularity for a date range.

    Returns 'weekly' for ranges up to 90 days, 'monthly' for longer ranges.

    Args:
        start_date: Start of the date range (inclusive).
        end_date: End of the date range (inclusive).

    Returns:
        'weekly' if the range spans <= 90 days, 'monthly' otherwise.

    Raises:
        ValueError: If end_date is earlier than start_date.
    """
    if end_date < start_date:
        raise ValueError(
            f"end_date ({end_date}) must not be before start_date ({start_date})"
        )
    delta_days = (end_date - start_date).days
    return "weekly" if delta_days <= 90 else "monthly"
