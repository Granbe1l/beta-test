"""Static contract for honest GitHub-only portfolio freshness, not uptime proof."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_primary_collector_remains_manually_dispatchable_and_source_audited():
    workflow = (ROOT / ".github/workflows/public-snapshot.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "cron: '23 1,5,9,13,17,21 * * *'" in workflow
    assert "group: public-snapshot-main" in workflow
    assert "--max-requests 850" in workflow
    for receipt in ("snapshot-audit.json", "coverage-readiness.json",
                    "open-inventory-triage.json"):
        assert receipt in workflow


def test_github_only_watchdog_does_not_pretend_to_be_external_scheduler():
    workflow = (ROOT / ".github/workflows/snapshot-watchdog.yml").read_text()
    script = (ROOT / "scripts/snapshot_watchdog.py").read_text()
    assert "cron: '47 * * * *'" in workflow
    assert "workflow_dispatch:" in workflow
    assert "not independent" not in workflow.lower() or "NOT independent" in workflow
    assert "MAX_AGE_HOURS = 6" in script
    assert "BACKOFF_MINUTES = 90" in script
    assert 'run.get("status") in ("queued", "in_progress", "waiting", "requested", "pending")' in script


def test_public_dashboard_keeps_utc_demo_proof_and_wib_reader_context():
    source = (ROOT / "streamlit_app.py").read_text()
    # Exact UTC formatting remains required by verify_public_demo.py.
    assert 'strftime("%d %b %Y · %H:%M UTC")' in source
    assert 'strftime("%d %b %Y · %H:%M WIB")' in source
    assert "PUBLIC GITHUB SNAPSHOT" in source
    assert "settings.stale_hours" in source
    assert "Full open-Issue inventory" in source
    assert "it does not collect from GitHub" in source
