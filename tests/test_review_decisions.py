"""P1 reviewer decisions are linked to measured source and falsifiable checks."""
from datetime import timedelta, datetime, timezone
from io import StringIO
import csv

from src.analytics.findings import findings_for_repo
from src.analytics.review_decisions import review_decision, review_csv

NOW = datetime(2026, 11, 13, 2, tzinfo=timezone.utc)
BASE = "https://github.com/sample/project"


def sample():
    return {
        "repository": {"full_name": "sample/project", "url": BASE},
        "open_backlog_status": "complete",
        "status": {"issues": "complete"},
        "coverage": {"issues": {"coverage_start": NOW-timedelta(days=65)}},
        "issue_rows": [
            {"number": 11, "url": BASE + "/issues/11",
             "title": "Unresolved upgrade discussion",
             "state": "open", "created_at": NOW-timedelta(days=80)},
            {"number": 12, "url": BASE + "/issues/12",
             "title": "Closed old report",
             "state": "closed", "created_at": NOW-timedelta(days=90),
             "closed_at": NOW-timedelta(days=2)},
        ],
        "pr_rows": [{
            "number": 24, "url": BASE + "/pull/24",
            "title": "Cache cleanup",
            "created_at": NOW-timedelta(days=14),
            "merged_at": NOW-timedelta(days=4),
        }],
        "ci_rows": [{
            "url": BASE + "/actions/runs/15", "workflow_name": "Build",
            "created_at": NOW-timedelta(days=3),
            "status": "completed", "conclusion": "failure",
        }],
        "issues": {"aged_denominator": 20, "aged_open": 12, "aged_percent": 60},
        "prs": {"median_merge_days": 10.0, "merge_duration_n": 8,
                "merged_evidence": [BASE + "/pull/24"]},
        "ci": {"known_conclusion_denominator": 20,
               "success_percent": 35, "success": 7},
        "closure": {"denominator": 12, "change_percent": -50,
                    "recent": 6, "previous": 12},
    }


def test_all_four_findings_have_real_traceable_review_actions():
    report = sample()
    # evidence_examples uses a current UTC interval, so test with relative
    # timestamps against the real clock when validating real-record links.
    now = datetime.now(timezone.utc)
    for key in ("issue_rows", "pr_rows", "ci_rows"):
        for record in report[key]:
            for field in ("created_at", "closed_at", "merged_at"):
                if record.get(field) is not None:
                    record[field] = record[field] + (now - NOW)
    report["coverage"]["issues"]["coverage_start"] = now-timedelta(days=65)
    findings = findings_for_repo(report)
    assert {x["type"] for x in findings} == {
        "issue-aging", "merge-duration", "closure-change", "ci"}
    for f in findings:
        plan = f["review_plan"]
        assert len(plan["steps"]) == 3
        assert "Check the measured scope" in plan["steps"][0]
        assert f["metric_context"] in plan["steps"][0]
        assert f["examples"][0]["label"] in plan["steps"][1]
        assert plan["first_record_url"] == f["examples"][0]["url"]
        assert plan["example_available"] is True
        assert "not" in plan["not_proven"].lower() or "cannot" in plan["not_proven"].lower()
        assert "score" not in plan


def test_empty_sources_never_fabricate_record_or_defect():
    item = {
        "type": "ci", "metric_context": "7 of 20 known completed checks",
        "evidence_scope": "Verified 90-day source",
        "url": BASE + "/actions", "examples": [],
    }
    plan = review_decision(item)
    assert not plan["example_available"]
    assert plan["first_record_url"] == BASE + "/actions"
    assert "no individual example available" in plan["steps"][1]
    assert "does not prove" in plan["not_proven"]


def test_review_csv_contains_exact_evidence_and_resists_spreadsheet_injection():
    report = sample()
    now = datetime.now(timezone.utc)
    for key in ("issue_rows", "pr_rows", "ci_rows"):
        for record in report[key]:
            for field in ("created_at", "closed_at", "merged_at"):
                if record.get(field) is not None:
                    record[field] += (now - NOW)
    report["coverage"]["issues"]["coverage_start"] = now-timedelta(days=65)
    rows = findings_for_repo(report)
    rows[0]["scope"] = "=HYPERLINK(\"https://malicious.example\")"
    output = review_csv(rows)
    data = list(csv.DictReader(StringIO(output.decode("utf-8-sig"))))
    assert len(data) == 4
    assert data[0]["Repository"].startswith("'=HYPERLINK(")
    assert "GitHub link (record or listing)" in data[0]
    assert data[0]["Record-level example available"] == "yes"
    assert all(len(row["Review step 3"]) > 25 for row in data)
    assert all(row["Verification scope"] and row["Reason to inspect"]
               for row in data)
