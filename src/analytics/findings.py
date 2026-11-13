"""Evidence-first, bounded business insights from verified figures."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from src.analytics.metrics import utc
from src.analytics.review_decisions import review_decision


def _has_verified_history(report: dict, source: str, days: int, now=None) -> bool:
    """A previous-period comparison requires a complete, current scan."""
    if report.get("status", {}).get(source) != "complete":
        return False
    cp = (report.get("coverage") or {}).get(source) or {}
    first = utc(cp.get("coverage_start"))
    now = utc(now or datetime.now(timezone.utc))
    return first is not None and first <= now - timedelta(days=days)





def evidence_examples(report: dict, kind: str, *, now=None, limit=3) -> list[dict]:
    """Trace a review suggestion to real GitHub records, not generic listing pages.

    Examples are inspection starting points, not proof of a defect, lateness,
    individual performance, or a complete project backlog.
    """
    now = utc(now or datetime.now(timezone.utc))
    repo_url = str(report["repository"]["url"]).rstrip("/")
    allowed = {
        "issue-aging": "/issues/",
        "closure-change": "/issues/",
        "merge-duration": "/pull/",
        "ci": "/actions/runs/",
    }
    if kind not in allowed or not 1 <= limit <= 10:
        return []
    candidates = []
    source = ("issue_rows" if kind in {"issue-aging", "closure-change"} else
              "pr_rows" if kind == "merge-duration" else "ci_rows")
    for row in report.get(source) or []:
        url = row.get("url")
        if not isinstance(url, str) or not url.startswith(repo_url + allowed[kind]):
            continue
        title = str(row.get("title") or row.get("workflow_name") or "GitHub record")
        title = " ".join(title.split())[:76]
        if kind == "issue-aging":
            created = utc(row.get("created_at"))
            if row.get("state") != "open" or not created or created > now:
                continue
            age = (now - created).days
            if age < 30:
                continue
            reason = f"Observed open for {age} days"
            priority = (age, created)
        elif kind == "merge-duration":
            created, merged = utc(row.get("created_at")), utc(row.get("merged_at"))
            if not created or not merged or not now - timedelta(days=90) <= merged <= now:
                continue
            elapsed = max(0.0, (merged - created).total_seconds() / 86400)
            reason = f"Observed merge duration: {elapsed:.1f} days"
            priority = (elapsed, merged)
        elif kind == "ci":
            created = utc(row.get("created_at"))
            if (not created or not now - timedelta(days=90) <= created <= now or
                    row.get("status") != "completed" or
                    row.get("conclusion") not in {"failure", "timed_out"}):
                continue
            reason = f"Recorded outcome: {row['conclusion']}"
            priority = (created, created)
        else:
            closed = utc(row.get("closed_at"))
            if not closed or not now - timedelta(days=56) <= closed <= now:
                continue
            bucket = "latest" if closed >= now - timedelta(days=28) else "earlier"
            reason = f"Closed in {bucket} 28-day period"
            priority = (closed, closed)
        number = row.get("number")
        label = f"#{number} · {title}" if number is not None else title
        candidates.append((priority, {"label": label, "url": url, "reason": reason}))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in candidates[:limit]]


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
                        "review": "Start with the oldest retrieved open issues; verify ownership, current relevance and next steps.",
                        "url": url + "/issues?q=is%3Aissue+is%3Aopen", "scope": name,
                        "review_priority": "Review first" if value >= 60 and i["aged_denominator"] >= 10 else "Review next"})
    if p["median_merge_days"] is not None and p["merge_duration_n"] >= 5:
        d = p["median_merge_days"]
        duration = (f"{d * 1440:.0f} min" if d < 1 / 24 else
                    f"{d * 24:.1f} hours" if d < 1 else f"{d:.1f} days")
        out.append({"type": "merge-duration", "headline": f"Merged PRs took a median of {duration} (n={p['merge_duration_n']})",
                    "evidence": f"Computed from creation to merge timestamps for {p['merge_duration_n']} merged PRs in the observation window.",
                    "interpretation": "This describes observed completion time, not the cause of slower or faster merges.",
                    "review": "Inspect the longest observed merged PRs; compare change complexity and review history before drawing conclusions.",
                    "url": p["merged_evidence"][0] if p["merged_evidence"] else url + "/pulls", "scope": name, "review_priority": "Explore context"})
    if (_has_verified_history(report, "issues", days=56)
            and c and c["denominator"] >= 5
            and c["change_percent"] is not None
            and abs(c["change_percent"]) >= 20):
        out.append({"type": "closure-change",
                    "headline": (f"Recorded issue closures: {c['recent']} in the latest "
                                 f"28 days, versus {c['previous']} in the preceding 28 days."),
                    "evidence": (f"{c['recent']} issue closures recorded in the latest 28 days "
                                 f"and {c['previous']} in the previous 28 days, from a "
                                 "verified 56-day source window."),
                    "interpretation": ("A change in recorded closures does not prove "
                                       "that a project slowed down, missed a deadline "
                                       "or reduced developer productivity."),
                    "review": "Inspect closed issues from both 28-day periods before explaining the observed change.",
                    "url": url + "/issues?q=is%3Aissue+is%3Aclosed", "scope": name,
                    "review_priority": "Review first" if abs(c["change_percent"]) >= 50 and c["denominator"] >= 10 else "Review next"})
    if (ci["known_conclusion_denominator"] or 0) >= 10 and ci["success_percent"] is not None and ci["success_percent"] < 80:
        out.append({"type": "ci", "headline": f"{ci['success_percent']:.0f}% of completed runs with known outcomes succeeded",
                    "evidence": f"{ci['success']} successes out of {ci['known_conclusion_denominator']} completed runs with known conclusions.",
                    "interpretation": "The observed CI completion share is not an overall software-quality score.",
                    "review": "Open the most recent failed checks; compare workflows, branches and repeated failure causes.",
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
                metric_label="Issues closed in the latest 28 days",
                metric_value=f'{c["recent"]:,}',
                metric_context=(f'{c["recent"]:,} latest vs {c["previous"]:,} earlier '
                                'recorded closures · two verified 28-day windows'),
                recent_count=c["recent"],
                previous_count=c["previous"],
            )
    source_context = {
        "issue-aging": "Current observed open issues · completed bounded issue scan",
        "merge-duration": "Merged changes · verified 90-day PR window",
        "closure-change": "Issue closures · verified adjacent 28+28-day windows",
        "ci": "Known completed checks · verified 90-day Actions window",
    }
    for item in out:
        item["evidence_scope"] = source_context.get(item["type"], "Observed GitHub records")
        if item["type"] == "issue-aging":
            item["evidence_scope"] = (
                "Verified complete current open-Issue inventory at the last scan"
                if report.get("open_backlog_status") == "complete"
                else "Observed retrieved open Issues · not a complete backlog"
            )
        item["examples"] = evidence_examples(report, item["type"])
        # A structured, checkable decision: measured signal -> original
        # record -> inspection -> bounded conclusion. Never a defect verdict.
        item["review_plan"] = review_decision(item)
    return out


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
