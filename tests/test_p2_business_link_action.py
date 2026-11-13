"""P2.4: verify user-facing CTA points at actual source, not a generic label."""
from src.analytics.review_decisions import evidence_action, review_decision


def test_direct_record_url_is_primary_action_when_snapshot_has_example():
    finding = {
        "type": "ci",
        "url": "https://github.com/example/repo/actions",
        "metric_context": "2 failures of 13 known runs",
        "evidence_scope": "Verified run window",
        "examples": [
            {"url": "https://github.com/example/repo/actions/runs/123",
             "label": "Integration workflow", "reason": "Recorded failure"}
        ],
    }
    finding["review_plan"] = review_decision(finding)
    result = evidence_action(finding)
    assert result["url"] == finding["examples"][0]["url"]
    assert result["record_level"] is True
    assert result["button"] == "Open example GitHub record"
    assert "before drawing a conclusion" in result["disclosure"]


def test_listing_fallback_does_not_claim_record_level_evidence():
    finding = {
        "type": "issue-aging",
        "url": "https://github.com/example/repo/issues?q=is%3Aissue",
        "examples": [],
        "metric_context": "12 of 20 retrieved open issues",
        "evidence_scope": "Observed only",
    }
    finding["review_plan"] = review_decision(finding)
    result = evidence_action(finding)
    assert result["record_level"] is False
    assert result["url"] == finding["url"]
    assert result["button"] == "Open GitHub source listing"
    assert "only a starting point" in result["disclosure"]


def test_unavailable_source_shows_no_fake_action():
    result = evidence_action({"type": "ci", "examples": [], "url": None})
    assert result["url"] is None
    assert result["button"] is None
    assert result["record_level"] is False


def test_ui_uses_same_derived_source_action_as_review_csv():
    from pathlib import Path
    ui = (Path(__file__).resolve().parents[1] /
          "src/ui/dashboard_v2.py").read_text()
    assert 'action = evidence_action(f)' in ui
    assert 'st.link_button(action["button"], action["url"]' in ui
    assert 'st.caption(action["disclosure"])' in ui
    assert 'st.link_button("Inspect evidence on GitHub", f["url"]' not in ui
