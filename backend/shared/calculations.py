"""Shared calculations module."""
from __future__ import annotations
from datetime import date

def calculate_take_up_rate(total_leads: int, total_take_up: int) -> float:
    if total_leads <= 0:
        raise ValueError(f"total_leads must be > 0, got {total_leads}")
    if total_take_up == 0:
        return 0.0
    return (total_take_up / total_leads) * 100

def compute_time_to_take_up(distribution_date: date, take_up_date: date) -> int:
    if take_up_date < distribution_date:
        raise ValueError(f"take_up_date must not be before distribution_date")
    return (take_up_date - distribution_date).days

def compute_statistics(values: list[int]) -> dict[str, float]:
    if not values:
        raise ValueError("values must not be empty")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    median = float(sorted_vals[mid]) if n % 2 == 1 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return {"min": float(sorted_vals[0]), "max": float(sorted_vals[-1]), "mean": sum(sorted_vals) / n, "median": median}

def compute_distribution_percentages(groups: dict[str, int]) -> dict[str, float]:
    total = sum(groups.values())
    if total == 0:
        raise ValueError("Total count must be > 0")
    keys = list(groups.keys())
    result: dict[str, float] = {}
    running_sum = 0.0
    for key in keys[:-1]:
        pct = round((groups[key] / total) * 100, 4)
        result[key] = pct
        running_sum += pct
    result[keys[-1]] = round(100.0 - running_sum, 4)
    return result

def select_granularity(start_date: date, end_date: date) -> str:
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")
    return "weekly" if (end_date - start_date).days <= 90 else "monthly"
