"""Descriptive within-category distributions from verified eligible metrics only.

Medians and quartiles contextualize uneven repository sizes without
ranking workers, treating missing data as zero, or generalizing the curated
non-random cohort to all GitHub projects.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite
from statistics import median


def _percentile(sorted_values: list[float], fraction: float) -> float:
    index = (len(sorted_values) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] -
                                  sorted_values[low]) * (index - low)


def category_eligibility(rows: list[dict], metric: str, *,
                         min_group: int = 4) -> list[dict]:
    """Every category's measured eligible count; never a productivity score.

    A verified zero is valid. A missing, withheld, invalid or non-finite value
    is not. Source-limited exploratory counts cannot be peer benchmarks.
    """
    if min_group < 3:
        raise ValueError("At least three eligible repositories per category")
    if "exploratory" in metric.lower():
        raise ValueError("Exploratory record totals cannot be peer benchmarks")
    totals = defaultdict(int)
    eligible = defaultdict(int)
    for row in rows:
        category = str(row.get("Category") or "Other")
        totals[category] += 1
        value = row.get(metric)
        if (isinstance(value, (int, float))
                and not isinstance(value, bool)
                and isfinite(float(value)) and value >= 0):
            eligible[category] += 1
    return [{
        "Category": category,
        "Eligible values": eligible[category],
        "Repositories in category": totals[category],
        "Missing / withheld": totals[category] - eligible[category],
        "Median shown": ("Yes" if eligible[category] >= min_group
                         else f"No (n < {min_group})"),
    } for category in sorted(totals)]


def category_distributions(rows: list[dict], metric: str, *,
                           min_group: int = 4) -> list[dict]:
    """Return eligible n/denominator, median and IQR for fixed-category peers.

    No calculation is permitted for incomplete exploratory record counts.
    The caller must pass rows produced by the source-gated comparison_rows.
    """
    if min_group < 3:
        raise ValueError("At least three eligible repositories per category")
    if "exploratory" in metric.lower():
        raise ValueError("Exploratory record totals cannot be peer benchmarks")
    eligible = defaultdict(list)
    totals = defaultdict(int)
    for row in rows:
        category = str(row.get("Category") or "Other")
        totals[category] += 1
        value = row.get(metric)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not isfinite(float(value)) or value < 0:
            continue
        eligible[category].append(float(value))
    output = []
    for category in sorted(totals):
        values = sorted(eligible[category])
        if len(values) < min_group:
            continue
        output.append({
            "Category": category,
            "Eligible repositories": len(values),
            "Repositories in category": totals[category],
            "Excluded / unknown": totals[category] - len(values),
            "Median": round(median(values), 2),
            "25th percentile": round(_percentile(values, 0.25), 2),
            "75th percentile": round(_percentile(values, 0.75), 2),
        })
    return output
