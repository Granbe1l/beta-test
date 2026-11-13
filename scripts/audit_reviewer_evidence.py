"""Audit actual reviewer findings against the committed real GitHub snapshot.

This is a deterministic evidence integrity and traceability audit. It does NOT
claim that any recruiter/user was observed or that API history is complete.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.executive import executive_brief
from src.analytics.findings import portfolio_findings
from src.analytics.snapshot import read_snapshot
from src.ui.observed import verified_joint_cohort


def audit() -> dict:
    reports, _, meta = read_snapshot()
    cohort = verified_joint_cohort(reports, days=28)
    if not reports or not cohort:
        raise AssertionError("No real 28-day verified cohort in the snapshot")

    by_name = {r["repository"]["full_name"]: r for r in cohort}
    findings = portfolio_findings(cohort, max_findings=10)
    types = {}
    verified_record_links = 0
    listing_fallbacks = 0
    for item in findings:
        name = item["scope"]
        report = by_name.get(name)
        if report is None:
            raise AssertionError(f"Finding refers to nonverified project: {name}")
        base = report["repository"]["url"].rstrip("/")
        assert item.get("metric_label") and item.get("metric_value")
        assert item.get("metric_context") and item.get("evidence_scope")
        assert item.get("review"), "Each finding needs an action, not just a score"
        plan = item.get("review_plan") or {}
        assert len(plan.get("steps") or []) == 3, "Missing three-step review"
        assert plan.get("trigger") and plan.get("not_proven")
        assert (plan.get("first_record_url") or "").startswith(base + "/"), (
            f"Evidence link outside source repository for {name}")
        row_sources = (report.get("issue_rows") or []) + (
            report.get("pr_rows") or []) + (report.get("ci_rows") or [])
        genuine_urls = {r.get("url") for r in row_sources if r.get("url")}
        for example in item.get("examples") or []:
            assert example["url"] in genuine_urls, (
                f"Untraceable individual GitHub record in {name}")
            assert example["url"].startswith(base + "/")
            assert example.get("label") and example.get("reason")
            verified_record_links += 1
        if not item.get("examples"):
            listing_fallbacks += 1
            assert not plan.get("example_available"), (
                "Listing fallback must not claim an inspected individual record")
        types[item["type"]] = types.get(item["type"], 0) + 1

    brief = executive_brief(cohort, findings=findings)
    if brief["finding"]:
        assert brief["source_url"].startswith("https://github.com/")
        assert brief.get("next_check")
    return {
        "status": "passed",
        "audit_type": "automated snapshot reviewer evidence, not human usability",
        "snapshot_generated_at_utc": meta["generated_at"].isoformat(),
        "tracked_repositories": len(reports),
        "verified_same_cohort_28d": len(cohort),
        "evidence_backed_findings": len(findings),
        "finding_types": types,
        "actual_individual_record_examples": verified_record_links,
        "listing_only_fallbacks": listing_fallbacks,
        "limitations": [
            "No human reviewer comprehension or usability claim",
            "Cannot certify unscanned or private GitHub records",
            "No customer delivery deadline, SLA or software health rating",
        ],
    }


if __name__ == "__main__":
    result = audit()
    output = Path("reviewer-evidence-audit.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print("REAL-SNAPSHOT REVIEWER EVIDENCE:", json.dumps(result, sort_keys=True))
