"""Descriptive peer context excludes incomplete/unknown and small groups."""
from src.analytics.comparable_groups import category_distributions

METRIC = "PRs merged · 28d"


def row(cat, val):
    return {"Category": cat, METRIC: val}


def test_category_median_iqr_is_computed_only_for_eligible_values():
    data = [
        row("Data & backend", 1), row("Data & backend", 2),
        row("Data & backend", 3), row("Data & backend", 40),
        row("Data & backend", None), row("Data & backend", -3),
        row("Cloud", 1), row("Cloud", None), row("Cloud", 7),
    ]
    result = category_distributions(data, METRIC)
    assert result == [{
        "Category": "Data & backend",
        "Eligible repositories": 4,
        "Repositories in category": 6,
        "Excluded / unknown": 2,
        "Median": 2.5,
        "25th percentile": 1.75,
        "75th percentile": 12.25,
    }]


def test_verified_zero_is_a_real_eligible_value_but_missing_is_not():
    rows = [row("Other", n) for n in (0, 0, 0, 0)]
    rows += [row("Other", None)]
    assert category_distributions(rows, METRIC) == [{
        "Category": "Other", "Eligible repositories": 4,
        "Repositories in category": 5, "Excluded / unknown": 1,
        "Median": 0.0, "25th percentile": 0.0,
        "75th percentile": 0.0,
    }]


def test_no_global_git_hub_benchmark_from_exploratory_or_missing():
    rows = [row("Cloud", None) for _ in range(6)]
    assert category_distributions(rows, METRIC) == []
    for field in ("Issue records retrieved · exploratory",
                  "PR records retrieved · exploratory"):
        try:
            category_distributions(rows, field)
        except ValueError:
            pass
        else:
            raise AssertionError("Exploratory totals are not peer performance")


def test_invalid_and_nonfinite_values_never_count_toward_denominator():
    data = [row("A", x) for x in (1, 2, 3, 4, True, float("nan"),
                                  float("inf"), "-1")]
    summary = category_distributions(data, METRIC)[0]
    assert summary["Eligible repositories"] == 4
    assert summary["Excluded / unknown"] == 4
    assert summary["Median"] == 2.5
    try:
        category_distributions(data, METRIC, min_group=1)
    except ValueError:
        pass
    else:
        raise AssertionError("Very small groups must be hidden")


def test_comparison_ui_explains_group_scope_without_rankings():
    from pathlib import Path
    code = (Path(__file__).resolve().parents[1] /
            "src/ui/pages.py").read_text(encoding="utf-8")
    assert "Within-category context · median and spread" in code
    assert "category_distributions(rows, metric, min_group=4)" in code
    assert "non-random sample" in code
    assert "No category has four eligible" in code
