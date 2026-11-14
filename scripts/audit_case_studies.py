"""Verify case-study claims and record-level source provenance using real snapshot."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.case_studies import build_case_studies
from src.analytics.snapshot import read_snapshot
from src.ui.observed import verified_joint_cohort

_SOURCE = {"issue-aging": "issue_rows", "ci": "ci_rows", "merge-duration": "pr_rows"}


def audit() -> dict:
    reports, _, meta = read_snapshot()
    eligible = verified_joint_cohort(reports, days=28)
    by_name = {r["repository"]["full_name"]: r for r in eligible}
    cases = build_case_studies(reports)
    types, names = set(), set()
    checks = []
    for case in cases:
        kind = case["kind"]
        name = case["repository"]
        report = by_name[name]
        row = next((r for r in report[_SOURCE[kind]]
                    if r.get("url") == case["record_url"]), None)
        assert kind in _SOURCE and row and name not in names and kind not in types
        assert case["record_url"].startswith(report["repository"]["url"] + "/")
        assert case["metric_label"] and case["metric_value"] and case["metric_context"]
        assert case["evidence_scope"] and case["trigger"] and case["not_proven"]
        assert "Only if" in case["conditional_decision"] or "only if" in case["conditional_decision"]
        if kind == "issue-aging":
            assert report.get("open_backlog_status") == "complete"
            assert row["state"] == "open"
        elif kind == "ci":
            assert row.get("conclusion") in ("failure", "timed_out")
        elif kind == "merge-duration":
            assert row.get("merged_at") is not None
        types.add(kind)
        names.add(name)
        checks.append({key: case[key] for key in (
            "kind", "repository", "metric_value", "metric_context",
            "evidence_scope", "record_url", "status")})
    assert len(cases) <= 3
    return {
        "status": "passed",
        "audit_kind": "Real public GitHub records, not verified business outcomes",
        "snapshot_generated_at": meta["generated_at"].isoformat(),
        "verified_28day_repositories": len(eligible),
        "real_record_backed_case_count": len(cases),
        "cases": checks,
        "note": "If a source/type has no qualifying evidence, fewer than three cases are shown; no dummy or inferred case is created.",
    }


if __name__ == "__main__":
    result = audit()
    Path("case-study-evidence-audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print("CASE STUDY SOURCE AUDIT:", json.dumps(result, sort_keys=True))
