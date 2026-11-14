"""Source-linked descriptive CI workflow-name contributions, not CI quality rankings.

GitHub REST observations contain a workflow *display name*, not an always
unique workflow-definition identifier. This groups by stored names only.
Repeated runs of the same workflow are separate observed runs. The calculation
reuses the exact 28-day completed/known denominator definition.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import defaultdict

from src.analytics.metrics import utc


def workflow_contributions(runs: list[dict], *, days: int = 28,
                           now=None, max_groups: int = 5) -> dict:
    if days < 1 or max_groups < 1:
        raise ValueError("days and max_groups must be positive")
    now = utc(now or datetime.now(timezone.utc))
    since = now - timedelta(days=days)
    groups = defaultdict(lambda: {
        "Known results": 0, "Success": 0, "Failure / timeout": 0,
        "Skipped": 0, "Other known": 0, "Unknown": 0,
    })
    complete = 0
    for run in runs:
        created = utc(run.get("created_at"))
        if (run.get("status") != "completed" or created is None
                or not since <= created <= now):
            continue
        complete += 1
        raw = run.get("workflow_name")
        label = str(raw).strip() if raw is not None else ""
        name = label or "(workflow name unavailable)"
        entry = groups[name]
        conclusion = run.get("conclusion")
        if conclusion is None:
            entry["Unknown"] += 1
            continue
        entry["Known results"] += 1
        key = (
            "Success" if conclusion == "success"
            else "Failure / timeout"
            if conclusion in ("failure", "timed_out")
            else "Skipped" if conclusion == "skipped"
            else "Other known"
        )
        entry[key] += 1
    known = sum(v["Known results"] for v in groups.values())
    unknown = sum(v["Unknown"] for v in groups.values())
    assert known + unknown == complete
    ordered = sorted(groups.items(), key=lambda item: (
        -item[1]["Known results"], -item[1]["Unknown"], item[0]))
    def row(name, counts):
        n = counts["Known results"]
        return {"Workflow (recorded name)": name, **counts,
                "Share of known outcomes (%)": (
                    round(n * 100 / known, 1) if known else None),
                "Success share within group (%)": (
                    round(counts["Success"] * 100 / n, 1) if n else None)}
    selected = [row(name, values) for name, values in ordered[:max_groups]]
    if len(ordered) > max_groups:
        remainder = {
            "Known results": 0, "Success": 0, "Failure / timeout": 0,
            "Skipped": 0, "Other known": 0, "Unknown": 0,
        }
        for _, values in ordered[max_groups:]:
            for k in remainder:
                remainder[k] += values[k]
        selected.append(row("Other recorded workflow names (aggregated)", remainder))
    assert sum(r["Known results"] for r in selected) == known
    assert sum(r["Unknown"] for r in selected) == unknown
    return {
        "days": days, "completed_total": complete, "known_total": known,
        "unknown_total": unknown, "recorded_name_groups": len(groups),
        "rows": selected,
        "disclaimer": (
            "Group names come from stored GitHub Actions labels, which need "
            "not be globally unique. Multiple runs can reflect retries, "
            "branches or one high-volume workflow; shares are descriptive, "
            "not independent defects, code quality or delivery outcomes."
        ),
    }
