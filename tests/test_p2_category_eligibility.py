"""P2: category denominators preserve actual unknowns and valid zero."""
from pathlib import Path

import pytest

from src.analytics.comparable_groups import category_eligibility

METRIC = "PRs merged · 28d"
ROOT = Path(__file__).resolve().parents[1]


def test_category_eligibility_tracks_missing_and_preserves_zero():
    rows = [
        {"Category": "Web", METRIC: 0},
        {"Category": "Web", METRIC: 3},
        {"Category": "Web", METRIC: 8},
        {"Category": "Web", METRIC: None},
        {"Category": "Cloud", METRIC: float("nan")},
        {"Category": "Cloud", METRIC: 0},
        {"Category": "Cloud", METRIC: 4},
        {"Category": "Cloud", METRIC: 5},
        {"Category": "Cloud", METRIC: 6},
    ]
    assert category_eligibility(rows, METRIC) == [
        {"Category": "Cloud", "Eligible values": 4,
         "Repositories in category": 5, "Missing / withheld": 1,
         "Median shown": "Yes"},
        {"Category": "Web", "Eligible values": 3,
         "Repositories in category": 4, "Missing / withheld": 1,
         "Median shown": "No (n < 4)"},
    ]


def test_ambiguous_or_invalid_source_values_never_qualify():
    rows = [{"Category": "Mobile", METRIC: value} for value in (
        -1, float("inf"), False, "0", None)]
    assert category_eligibility(rows, METRIC) == [
        {"Category": "Mobile", "Eligible values": 0,
         "Repositories in category": 5, "Missing / withheld": 5,
         "Median shown": "No (n < 4)"},
    ]
    with pytest.raises(ValueError):
        category_eligibility(rows, "CI records retrieved · exploratory")


def test_peer_ui_and_browser_show_eligibility_and_category_warning():
    ui = (ROOT / "src/ui/pages.py").read_text(encoding="utf-8")
    browser = (ROOT / "scripts/capture_ui.py").read_text(encoding="utf-8")
    assert "Data eligibility by category" in ui
    assert "category_eligibility(rows, metric, min_group=4)" in ui
    assert "Raw event counts are not normalized" in ui
    assert 'hover_data=["Category", "Event coverage", "Full open inventory"]' in ui
    assert "Verified real peer eligibility disclosure" in browser
