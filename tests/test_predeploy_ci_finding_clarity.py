"""Predeploy medium: CI outcome provenance and honest finding sequence."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.analytics.comparisons import checks_in_period

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def test_ci_denominator_counts_skipped_and_other_but_not_unknown():
    kinds = ["success", "failure", "timed_out", "skipped", "cancelled", None]
    runs = [
        {"created_at": NOW-timedelta(hours=1), "status": "completed",
         "conclusion": conclusion}
        for conclusion in kinds
    ]
    info = checks_in_period(runs, days=28, now=NOW)
    assert info["total"] == 6
    assert info["known"] == 5
    assert info["success"] == 1
    assert info["failure"] == 2
    assert info["skipped"] == 1
    assert info["other"] == 1
    assert info["unknown"] == 1
    assert info["success_percent"] == 20


def test_ci_ui_explains_unknown_other_and_skipped_not_all_failures():
    ui = (ROOT/"src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert 'f\'Skipped {info["skipped"]:,}' in ui
    assert 'Other known {info["other"]:,}' in ui
    assert "they are not all software failures" in ui
    assert "not a quality score" in ui
    assert "Skipped/cancelled/other are not" in ui


def test_finding_cards_explicitly_call_order_not_severity():
    ui = (ROOT/"src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert "Inspection order is an evidence-review sequence" in ui
    assert "Multiple findings may meet the same" in ui
    assert "CHECK {idx + 1}/{len(findings)}" in ui
