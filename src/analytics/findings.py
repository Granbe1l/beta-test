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
                        "url": url + "/issues?q=is%3Aissue+is%3Aopen", "scope": name,
                        "review_priority": "Review first" if value >= 60 and i["aged_denominator"] >= 10 else "Review next"})
    if p["median_merge_days"] is not None and p["merge_duration_n"] >= 5:
        d = p["median_merge_days"]
        duration = (f"{d * 1440:.0f} min" if d < 1 / 24 else
                    f"{d * 24:.1f} hours" if d < 1 else f"{d:.1f} days")
        out.append({"type": "merge-duration", "headline": f"Merged PRs took a median of {duration} (n={p['merge_duration_n']})",
                    "evidence": f"Computed from creation to merge timestamps for {p['merge_duration_n']} merged PRs in the observation window.",
                    "interpretation": "This describes observed completion time, not the cause of slower or faster merges.",
                    "review": "Inspect a few long-running merges alongside PR complexity and review activity.",
                    "url": p["merged_evidence"][0] if p["merged_evidence"] else url + "/pulls", "scope": name, "review_priority": "Explore context"})
    if c and c["denominator"] >= 5 and c["change_percent"] is not None and abs(c["change_percent"]) >= 20:
        direction = "increased" if c["change_percent"] > 0 else "decreased"
        out.append({"type": "closure-change", "headline": f"Issue closures {direction} {abs(c['change_percent']):.0f}% (28d vs prior 28d)",
                    "evidence": f"{c['recent']} closures vs {c['previous']} closures in adjacent equal-length windows.",
                    "interpretation": "The change measures closure activity, not project productivity or issue complexity.",
                    "review": "Check issue types and contributor activity in both periods before explaining the change.",
                    "url": url + "/issues?q=is%3Aissue+is%3Aclosed", "scope": name,
                    "review_priority": "Review first" if abs(c["change_percent"]) >= 50 and c["denominator"] >= 10 else "Review next"})
    if (ci["known_conclusion_denominator"] or 0) >= 10 and ci["success_percent"] is not None and ci["success_percent"] < 80:
        out.append({"type": "ci", "headline": f"{ci['success_percent']:.0f}% of completed runs with known outcomes succeeded",
                    "evidence": f"{ci['success']} successes out of {ci['known_conclusion_denominator']} completed runs with known conclusions.",
                    "interpretation": "The observed CI completion share is not an overall software-quality score.",
                    "review": "Look for recurring failure patterns by workflow and event.",
                    "url": url + "/actions", "scope": name,
                    "review_priority": "Review first" if ci["success_percent"] < 50 and ci["known_conclusion_denominator"] >= 20 else "Review next"})
    # Compact visual evidence uses only this report's already-computed
    # measurements. Ratios are displayed only where a real denominator exists.
    for finding in out:
        kind = finding["type"]
        if kind == "issue-aging":
            finding.update(
                metric_label="Issues aged 30+ days",
                metric_value=f'{i["aged_percent"]:.0f}%',
                metric_context=f'{i["aged_open"]:,} of {i["aged_denominator"]:,} retrieved open issues',
                observed=i["aged_open"], denominator=i["aged_denominator"],
            )
        elif kind == "ci":
            finding.update(
                metric_label="CI checks succeeded",
                metric_value=f'{ci["success_percent"]:.0f}%',
                metric_context=f'{ci["success"]:,} of {ci["known_conclusion_denominator"]:,} known completed checks',
                observed=ci["success"],
                denominator=ci["known_conclusion_denominator"],
            )
        elif kind == "merge-duration":
            finding.update(
                metric_label="Median merge time",
                metric_value=duration,
                metric_context=f'{p["merge_duration_n"]:,} observed merged changes in the calculation',
            )
        elif kind == "closure-change":
            finding.update(
                metric_label="Issue closure change",
                metric_value=f'{c["change_percent"]:+.0f}%',
                metric_context=f'{c["recent"]:,} recent vs {c["previous"]:,} prior observed closures',
            )
    return out[:3]


def portfolio_findings(repo_reports: list[dict], max_findings=3) -> list[dict]:
    """Select diverse, source-supported checks—not an algorithmic quality rank.

    Priority is a transparent review queue with evidence thresholds, not a
    developer-productivity or software-quality score. Keep one finding per
    evidence category before adding another project of the same type.
    """
    pool = [item for report in repo_reports for item in findings_for_repo(report)]
    order = {"Review first": 0, "Review next": 1, "Explore context": 2}
    category = {"ci": 0, "issue-aging": 1, "closure-change": 2,
                "merge-duration": 3}
    pool.sort(key=lambda f: (
        order.get(f.get("review_priority"), 3),
        category.get(f.get("type"), 9),
        f.get("scope", ""),
    ))
    chosen = []
    types = set()
    for item in pool:
        if item["type"] in types:
            continue
        chosen.append(item)
        types.add(item["type"])
        if len(chosen) >= max_findings:
            return chosen
    for item in pool:
        if len(chosen) >= max_findings:
            break
        if item not in chosen and item["scope"] not in {x["scope"] for x in chosen}:
            chosen.append(item)
    return chosen
