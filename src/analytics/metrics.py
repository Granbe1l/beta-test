"""Deterministic descriptive metrics; no project-quality or lateness scoring."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median


def utc(value):
    if value is None: return None
    if isinstance(value, str): value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def ratio(num, denom):
    return (num / denom * 100) if denom else None


def days(start, end):
    return (utc(end) - utc(start)).total_seconds() / 86400


def weekly_series(items, key: str, since, now):
    """Zero is meaningful only when endpoint coverage is verified elsewhere."""
    since, now = utc(since), utc(now)
    ticks = []
    cursor = (since - timedelta(days=since.weekday())).date()
    while cursor <= now.date():
        ticks.append(cursor.isoformat())
        cursor += timedelta(days=7)
    counts = Counter()
    for item in items:
        value = utc(item.get(key))
        if value and since <= value <= now:
            counts[(value.date() - timedelta(days=value.weekday())).isoformat()] += 1
    return [{"week": t, "count": counts[t]} for t in ticks]


def calculate_issues(issues: list[dict], now, observation_days: int = 90, complete=True, coverage_start=None, backlog_complete=False) -> dict:
    now = utc(now)
    active = [i for i in issues if i.get("state") == "open"]
    aged = [i for i in active if days(i["created_at"], now) >= 30]
    age_groups = {"0–6d": 0, "7–29d": 0, "30–89d": 0, "90d+": 0}
    for i in active:
        age = days(i["created_at"], now)
        age_groups["0–6d" if age < 7 else "7–29d" if age < 30 else "30–89d" if age < 90 else "90d+"] += 1
    since = now - timedelta(days=observation_days)
    trend_valid = complete and (coverage_start is not None and utc(coverage_start) <= since)
    opened = weekly_series(issues, "created_at", since, now) if trend_valid else None
    closed = weekly_series(issues, "closed_at", since, now) if trend_valid else None
    labels = Counter(label for i in issues for label in i.get("labels", []))
    # A complete recent-updates scan does not certify all open issues.
    # An independent exhausted open-backlog scan does, but never changes
    # eligibility for 7/28/90-day source event trends.
    valid_observed_open = complete or backlog_complete
    # NEVER equate a complete recent-updates scan with the entire open
    # backlog. Such scans miss years-old Issues that were never updated.
    # Independent full-open inventory is the sole gate for true backlog
    # shares; the observed sample is reported separately and explicitly.
    return {"observed_open": len(active) if valid_observed_open else None,
            "observed_open_partial": len(active),
            "sample_aged_open": len(aged),
            "sample_aged_denominator": len(active),
            "sample_aged_percent": ratio(len(aged), len(active)),
            "sample_age_distribution": age_groups,
            "aged_open": len(aged) if backlog_complete else None,
            "aged_percent": ratio(len(aged), len(active)) if backlog_complete else None,
            "aged_denominator": len(active) if backlog_complete else None,
            "age_distribution": age_groups if backlog_complete else None,
            "full_open_backlog_verified": bool(backlog_complete),
            "weekly_opened": opened, "weekly_closed": closed,
            "label_counts": labels.most_common(8) if complete else None,
            "total_observed": len(issues), "trend_valid": trend_valid}


def calculate_prs(prs: list[dict], now, observation_days: int = 90, complete=True, coverage_start=None) -> dict:
    now = utc(now)
    since = now - timedelta(days=observation_days)
    opened = [p for p in prs if p.get("state") == "open"]
    drafted = [p for p in opened if p.get("draft")]
    merged = [p for p in prs if p.get("merged_at") and since <= utc(p["merged_at"]) <= now]
    closed_no_merge = [p for p in prs if p.get("state") == "closed" and not p.get("merged_at") and p.get("closed_at") and since <= utc(p["closed_at"]) <= now]
    durations = [max(days(p["created_at"], p["merged_at"]), 0) for p in merged]
    buckets = {"<1 day": 0, "1–7 days": 0, "7–30 days": 0, ">30 days": 0}
    for d in durations:
        buckets["<1 day" if d < 1 else "1–7 days" if d < 7 else "7–30 days" if d <= 30 else ">30 days"] += 1
    trend_valid = complete and coverage_start is not None and utc(coverage_start) <= since
    return {"open": len(opened) if complete else None, "draft_open": len(drafted) if complete else None,
            "merged_in_period": len(merged) if trend_valid else None,
            "closed_unmerged_in_period": len(closed_no_merge) if trend_valid else None,
            "median_merge_days": median(durations) if trend_valid and len(durations) >= 5 else None,
            "merge_duration_n": len(durations) if trend_valid else None,
            "merge_distribution": buckets if trend_valid else None,
            "merged_evidence": [p["url"] for p in merged[:5] if p.get("url")],
            "total_observed": len(prs), "trend_valid": trend_valid,
            "review_rule": "No review-compliance claim: review approvals were not fully collected"}


def calculate_ci(runs: list[dict], now, observation_days=90, complete=True, coverage_start=None) -> dict:
    now = utc(now)
    since = now - timedelta(days=observation_days)
    valid = complete and coverage_start is not None and utc(coverage_start) <= since
    completed = [r for r in runs if r.get("status") == "completed" and since <= utc(r["created_at"]) <= now]
    known = [r for r in completed if r.get("conclusion") is not None]
    counts = Counter(r.get("conclusion") for r in known)
    failures = counts["failure"] + counts["timed_out"]
    other_known = len(known) - counts["success"] - failures - counts["skipped"]
    return {"completed": len(completed) if valid else None,
            "success": counts["success"] if valid else None,
            "failure": failures if valid else None,
            "skipped": counts["skipped"] if valid else None,
            "other_known": other_known if valid else None,
            "unknown_conclusion": len(completed) - len(known) if valid else None,
            "known_conclusion_denominator": len(known) if valid else None,
            # This is a success share across ALL known conclusions: skipped,
            # cancelled and neutral outcomes are not silently treated as failures.
            "success_percent": ratio(counts["success"], len(known)) if valid else None,
            "total_observed": len(runs), "trend_valid": valid}


def closure_change(issues: list[dict], now, complete=True, coverage_start=None):
    """Non-overlapping 28d windows; preserve uncertainty for insufficient coverage."""
    now = utc(now)
    if not complete or not coverage_start or utc(coverage_start) > now - timedelta(days=56):
        return None
    recent, previous = 0, 0
    for item in issues:
        closed = utc(item.get("closed_at"))
        if closed and now - timedelta(days=28) <= closed <= now:
            recent += 1
        elif closed and now - timedelta(days=56) <= closed < now - timedelta(days=28):
            previous += 1
    return {"recent": recent, "previous": previous,
            "change_percent": (recent - previous) / previous * 100 if previous else None,
            "denominator": previous}


def comparable_metrics(repo_rows: list[dict]) -> list[dict]:
    """Suppress low sample ratios and medians; never assign a 'best' repository."""
    result = []
    for r in repo_rows:
        i, p = r["issues"], r["prs"]
        result.append({"Repository": r["repository"]["full_name"],
                       "Category": r["repository"]["category"],
                       "Language": r["repository"]["language"],
                       "30+ day issues (%)": i["aged_percent"] if (i["aged_denominator"] or 0) >= 5 else None,
                       "Open issue sample (n)": i["aged_denominator"],
                       "Median merge (days)": p["median_merge_days"],
                       "Merged PR sample (n)": p["merge_duration_n"],
                       "Closed issues (28d)": r["closure"]["recent"] if r["closure"] else None,
                       "Coverage": "complete" if r["coverage_ok"] else "incomplete"})
    return result
