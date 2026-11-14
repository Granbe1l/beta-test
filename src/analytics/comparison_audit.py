"""Independent comparison readiness checks against real stored source records.

These checks do NOT certify completeness of GitHub's API. They ensure that
our displayed comparisons respect the declared checkpoint eligibility,
preserve observed zeros, and never infer historical change without matched
verified inventories. All counters are measured; no default pass booleans.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.analytics.metrics import utc
from src.analytics.comparison_views import comparison_rows, metric_options, preferred_metric
from src.analytics.comparisons import comparable_observation_pair

EVENTS = (
    ("issues", "issue_rows", "closed_at", "Issues closed · 28d"),
    ("pull_requests", "pr_rows", "merged_at", "PRs merged · 28d"),
    ("workflow_runs", "ci_rows", "created_at", "Completed CI checks · 28d"),
)


def audit_comparison_readiness(reports: list[dict], *, now=None) -> dict:
    now = utc(now or datetime.now(timezone.utc))
    if len(reports) < 2:
        raise AssertionError("Actual compared cohort must include 2+ reports")
    period_start = now - timedelta(days=28)
    rows = comparison_rows(reports, days=28, now=now)
    if len(rows) != len(reports):
        raise AssertionError("Comparison dropped a tracked repository")
    assert [r["Repository"] for r in rows] == [
        r["repository"]["full_name"] for r in reports]
    assert all(x["Event coverage"].endswith("sources · 28d") for x in rows)

    present_values = 0
    true_zeros = 0
    disqualified_none = 0
    forced_partial_none = 0
    forced_short_none = 0
    for report, shown in zip(reports, rows):
        for source, key, stamp, metric in EVENTS:
            cp = (report.get("coverage") or {}).get(source) or {}
            coverage_start = utc(cp.get("coverage_start"))
            verified = (
                report.get("status", {}).get(source) == "complete"
                and coverage_start is not None
                and coverage_start <= period_start
            )
            value = shown[metric]
            if verified:
                expected = sum(
                    1 for item in report.get(key) or []
                    if ((source != "workflow_runs"
                         or item.get("status") == "completed")
                        and (event_time := utc(item.get(stamp))) is not None
                        and period_start <= event_time <= now)
                )
                assert value == expected, (
                    f"{report['repository']['full_name']}: {metric} "
                    f"reported {value} but original rows count {expected}")
                present_values += 1
                true_zeros += int(expected == 0)
            else:
                assert value is None, (
                    f"Missing/incomplete {source} was shown as {value}, not unknown")
                disqualified_none += 1
            # Negative controls: keep original rows, revoke only the claimed
            # verified status. An observed zero must become UNKNOWN, not zero.
            modified = {**report, "status": {
                **report.get("status", {}), source: "partial"}}
            muted = comparison_rows([modified], days=28, now=now)[0]
            assert muted[metric] is None, f"{source} leaked a false zero"
            forced_partial_none += 1
            # Independently assert a 7-day checkpoint cannot justify a
            # 28-day metric, even with 28 days of actual source rows present.
            coverage = dict(report.get("coverage") or {})
            coverage[source] = {
                **cp, "coverage_start": now - timedelta(days=7)}
            short = {**report, "coverage": coverage,
                     "status": {**report.get("status", {}),
                                source: "complete"}}
            short_value = comparison_rows([short], days=28, now=now)[0]
            assert short_value[metric] is None, (
                f"Short {source} coverage falsely certified 28-day values")
            forced_short_none += 1

    # Reconstruct the exact source observation/date that the historical
    # comparison would need; no values are synthesized for absent pairs.
    pair = comparable_observation_pair(reports)
    if pair is not None:
        dates = (pair["previous_date"], pair["current_date"])
        matched = pair["repositories"]
        assert matched and pair["matched_count"] == len(matched)
        report_by_name = {r["repository"]["full_name"]: r for r in reports}
        source_totals = {}
        for day in dates:
            issue_total, pr_total = 0, 0
            for name in matched:
                latest = None
                for obs in report_by_name[name].get("observations") or []:
                    measured = utc(obs.get("measured_at"))
                    if measured and measured.date().isoformat() == day and (
                            latest is None or measured > latest[0]):
                        latest = (measured, obs)
                assert latest is not None
                row = latest[1]
                assert row.get("collection_basis") == "verified_open_inventory"
                assert row.get("open_issues_observed") is not None
                assert row.get("open_prs_observed") is not None
                issue_total += int(row["open_issues_observed"])
                pr_total += int(row["open_prs_observed"])
            source_totals[day] = (issue_total, pr_total)
        assert (pair["previous_issues"], pair["previous_prs"]) == source_totals[dates[0]]
        assert (pair["current_issues"], pair["current_prs"]) == source_totals[dates[1]]

    values = {metric: sum(row.get(metric) is not None for row in rows)
              for metric in metric_options(28) if "exploratory" not in metric}
    metric = preferred_metric(rows, 28)
    return {
        "status": "passed",
        "tracked_repositories": len(reports),
        "period_days": 28,
        "default_metric": metric,
        "default_metric_eligible": sum(r.get(metric) is not None for r in rows),
        "metric_eligible_counts": values,
        "source_row_counts_independently_verified": present_values,
        "verified_true_zeros": true_zeros,
        "unverified_values_confirmed_unknown": disqualified_none,
        "negative_partial_checkpoint_gates_passed": forced_partial_none,
        "negative_short_window_gates_passed": forced_short_none,
        "historical_matched_verified_pair": (
            {"previous_date": pair["previous_date"],
             "current_date": pair["current_date"],
             "matched_repositories": pair["matched_count"]}
            if pair is not None else None
        ),
        "history_disclosure": (
            "A matched verified pair was individually checked against stored records"
            if pair is not None else
            "No eligible two-date verified comparison; historical change not reported"
        ),
    }
