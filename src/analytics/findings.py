"""Evidence-first, bounded business insights from verified figures."""
from __future__ import annotations


def findings_for_repo(report: dict) -> list[dict]:
    i, p, ci, c = report["issues"], report["prs"], report["ci"], report["closure"]
    name = report["repository"]["full_name"]
    url = report["repository"]["url"]
    out = []
    if (i["aged_denominator"] or 0) >= 5 and i["aged_percent"] is not None:
        value = i["aged_percent"]
        if value >= 40:
            out.append({"type": "issue-aging", "headline": f"{value:.0f}% of {i['aged_denominator']} observed open issues are 30+ days old",
                        "evidence": f"{i['aged_open']} of {i['aged_denominator']} observed open issues in {name}.",
                        "interpretation": "Older issues form a substantial share of this observed sample; age alone does not establish delay.",
                        "review": "Check a sample of older issues for relevance, ownership, and next steps.",
                        "url": url + "/issues?q=is%3Aissue+is%3Aopen", "scope": name})
    if p["median_merge_days"] is not None and p["merge_duration_n"] >= 5:
        d = p["median_merge_days"]
        duration = (f"{d * 1440:.0f} min" if d < 1 / 24 else
                    f"{d * 24:.1f} hours" if d < 1 else f"{d:.1f} days")
        out.append({"type": "merge-duration", "headline": f"Merged PRs took a median of {duration} (n={p['merge_duration_n']})",
                    "evidence": f"Computed from creation to merge timestamps for {p['merge_duration_n']} merged PRs in the observation window.",
                    "interpretation": "This describes observed completion time, not the cause of slower or faster merges.",
                    "review": "Inspect a few long-running merges alongside PR complexity and review activity.",
                    "url": p["merged_evidence"][0] if p["merged_evidence"] else url + "/pulls", "scope": name})
    if c and c["denominator"] >= 5 and c["change_percent"] is not None and abs(c["change_percent"]) >= 20:
        direction = "increased" if c["change_percent"] > 0 else "decreased"
        out.append({"type": "closure-change", "headline": f"Issue closures {direction} {abs(c['change_percent']):.0f}% (28d vs prior 28d)",
                    "evidence": f"{c['recent']} closures vs {c['previous']} closures in adjacent equal-length windows.",
                    "interpretation": "The change measures closure activity, not project productivity or issue complexity.",
                    "review": "Check issue types and contributor activity in both periods before explaining the change.",
                    "url": url + "/issues?q=is%3Aissue+is%3Aclosed", "scope": name})
    if (ci["known_conclusion_denominator"] or 0) >= 10 and ci["success_percent"] is not None and ci["success_percent"] < 80:
        out.append({"type": "ci", "headline": f"{ci['success_percent']:.0f}% of completed runs with known outcomes succeeded",
                    "evidence": f"{ci['success']} successes out of {ci['known_conclusion_denominator']} completed runs with known conclusions.",
                    "interpretation": "The observed CI completion share is not an overall software-quality score.",
                    "review": "Look for recurring failure patterns by workflow and event.",
                    "url": url + "/actions", "scope": name})
    return out[:3]


def portfolio_findings(repo_reports: list[dict], max_findings=3) -> list[dict]:
    pool = [f for r in repo_reports for f in findings_for_repo(r)]
    # First diversify finding types, then scope. Highest observed ratios are not quality rankings.
    seen_types = set()
    selected = []
    for f in pool:
        if f["type"] not in seen_types:
            selected.append(f)
            seen_types.add(f["type"])
        if len(selected) >= max_findings: break
    for f in pool:
        if len(selected) >= max_findings: break
        if f not in selected and f["scope"] not in {s["scope"] for s in selected}:
            selected.append(f)
    return selected
