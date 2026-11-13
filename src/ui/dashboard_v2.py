"""Visual-first, read-only Streamlit dashboard using observed public GitHub records.

The six screens prioritize charts and plain-language actions. Existing collectors,
metrics, checkpoints, source links, and technical appendix remain unchanged.
A missing or incomplete source is never treated as an observed zero.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.findings import portfolio_findings
from src.analytics.executive import executive_brief
from src.analytics.metrics import utc
from src.analytics.activity import recent_activity, sample_activity, activity_label, weekly_activity
from src.analytics.comparisons import comparable_observation_pair, checks_in_period
from src.ui.charts import observed_age_bands, observed_merge_times, observed_outcomes
from src.ui.filters import (filter_work_items, filter_pull_requests,
                            filter_workflow_runs, issue_age_days)
from src.ui.pages import (status_for, select_repo, table_rows, source_coverage,
                          comparison, methodology_contents, at_time)
from src.ui.theme import esc, empty_state
from src.ui.observed import summary
from src.ui.trend_panels import trend_panel, coverage_progress, compare_two_repositories

PURPLE = "#6941C6"
PURPLE_LIGHT = "#AE8BE8"
GREEN = "#198E74"
RED = "#D86172"
GOLD = "#E0A64E"
INK = "#211A35"
BAR = ["#BBA6E9", "#987ADD", "#7348C7", "#49218C"]


def _number(value):
    if value is None:
        return "—"
    return f"{int(value):,}"


def _percent(value):
    return "—" if value is None else f"{value:.0f}%"


def _duration(value):
    """Keep short merges readable: 0.0 days can conceal real hours."""
    if value is None:
        return "—"
    if value < 1 / 24:
        return f"{value * 1440:.0f} min"
    if value < 1:
        return f"{value * 24:.1f} hours"
    return f"{value:.1f} days"


def _section(title, note=""):
    st.markdown(f'<div class="d-section">{esc(title)}</div>' +
                (f'<div class="d-sub">{esc(note)}</div>' if note else ""),
                unsafe_allow_html=True)


def _heading(kicker, title, note, reports):
    from src.ui.observed import verified_joint_cohort
    # A "complete" recent bounded scan is NOT proof of 28-day coverage.
    # Make the exact eligible denominator visible on every detail screen.
    n = len(reports)
    verified_28 = len(verified_joint_cohort(reports, days=28))
    complete = n > 0 and verified_28 == n
    status_text = (f"28d verified {verified_28}/{n} in view"
                   if n else "No source data")
    st.markdown(
        f'<div class="d-heading"><div><div class="d-overline">{esc(kicker)}</div>'
        f'<h1>{esc(title)}</h1><p>{esc(note)}</p></div>'
        f'<span class="d-status {"ok" if complete else ""}">{esc(status_text)}</span>'
        '</div>', unsafe_allow_html=True)


def _kpis(cards):
    """Compact, responsive evidence cards with descriptive native tooltips."""
    fragments = []
    for label, value, context, glyph in cards:
        fragments.append(
            f'<div class="d-kpi" title="{esc(label)}: {esc(context)}">'
            f'<div class="d-kpi-label"><span>{esc(label)}</span>'
            f'<span class="d-kpi-icon" aria-hidden="true">{esc(glyph)}</span></div>'
            f'<div class="d-kpi-value">{esc(value)}</div>'
            f'<div class="d-kpi-note">{esc(context)}</div></div>'
        )
    st.markdown('<div class="d-kpis">' + ''.join(fragments) + '</div>',
                unsafe_allow_html=True)



def _chart(fig, height=265, legend=False):
    """Shared restrained Plotly typography, axes, legends and hover labels."""
    fig.update_layout(
        template="plotly_white", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=35, t=12, b=48 if legend else 26),
        font=dict(family="Arial, sans-serif", color=INK, size=11),
        showlegend=legend,
        legend=dict(orientation="h", y=-.22, x=0, yanchor="top",
                    title=None, font=dict(size=10)),
        hoverlabel=dict(bgcolor="#fff", font_color=INK),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, linecolor="#E8E5EE", zeroline=False,
                     tickfont=dict(color="#746D81"))
    fig.update_yaxes(gridcolor="#F1EDF7", zeroline=False,
                     tickfont=dict(color="#746D81"))
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False, "displayModeBar": False})


def _horizontal_bars(labels, counts, colors=None, height=245, unit="Observed records"):
    """Readable labelled categorical counts, without a separate legend."""
    labels = [str(x) for x in labels]
    values = [int(x or 0) for x in counts]
    if not values or not sum(values):
        st.info("No matching activity is available in the retrieved records.")
        return
    palette = colors or [PURPLE] * len(values)
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation="h",
        marker=dict(color=palette, line=dict(width=0)),
        text=[f"{v:,}" for v in values], textposition="outside",
        textfont=dict(size=11, color=INK), cliponaxis=False,
        hovertemplate="%{y}: %{x:,}<extra></extra>",
    ))
    fig.update_layout(bargap=.36, xaxis_title=unit, yaxis_title=None,
                      yaxis=dict(autorange="reversed"),
                      xaxis=dict(range=[0, max(values)*1.25]))
    _chart(fig, height=height)



def _donut(labels, values, colors, total_label, height=245):
    """Use a part-of-whole chart only with a genuine, non-zero denominator."""
    count = sum(values)
    if not count:
        st.info("No usable records were retrieved for this chart.")
        return
    # Remove zero-size sectors so overlapping "0%" labels cannot appear.
    sectors = [(label, value, color) for label, value, color in zip(labels, values, colors)
               if value > 0]
    fig = go.Figure(go.Pie(
        labels=[x[0] for x in sectors], values=[x[1] for x in sectors], hole=.69,
        sort=False, direction="clockwise",
        marker=dict(colors=[x[2] for x in sectors], line=dict(color="#FFFFFF", width=2)),
        textinfo="none", texttemplate="%{percent:.1%}", textposition="outside",
        textfont=dict(size=10, color=INK), automargin=True,
        hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=8, r=6, b=44, l=6),
        annotations=[dict(text=f"<b>{count:,}</b><br><span style='font-size:9px'>{total_label}</span>",
                          showarrow=False, x=.5, y=.5, font=dict(size=17, color=INK))],
    )
    _chart(fig, height=height, legend=True)


def _ci_donut(rows, period=30):
    """Known outcomes only, with the same numerator and denominator as KPI."""
    info = checks_in_period(rows, days=period)
    labels = [k for k in ("Success", "Failure / timeout", "Skipped", "Other outcomes")
              if info["counts"].get(k)]
    palette = {"Success": GREEN, "Failure / timeout": RED,
               "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD}
    if not labels:
        st.info("No completed automated checks with known outcomes were retrieved.")
        return
    _donut(labels, [info["counts"][k] for k in labels],
           [palette[k] for k in labels], "known checks", height=245)
    success = info["success_percent"]
    if success is not None:
        st.caption(
            f'**{info["success"]:,} succeeded / {info["known"]:,} known outcomes '
            f'({success:.1f}%)** · Failed/timed out {info["failure"]:,} · '
            f'Skipped {info["skipped"]:,} · Other known {info["other"]:,}. '
            "Skipped and other outcomes remain in the known denominator; "
            "they are not all software failures. A passed check is not a "
            "software-quality score."
        )
    if info["unknown"]:
        st.caption(f'{info["unknown"]:,} completed runs with unknown '
                   "conclusions are excluded from the success rate.")


def _issue_age_donut(rows):
    bands = observed_age_bands(rows)
    values = list(bands.values())
    _donut(list(bands), values, BAR, "open issues", height=250)
    count = sum(values)
    if count:
        older = values[2] + values[3]
        st.caption(f"{older:,} of {count:,} observed open issues are at least 30 days old "
                   f"({older / count:.0%}). Age alone does not establish lateness.")


def _duration_columns(buckets):
    names = list(buckets)
    values = [int(v or 0) for v in buckets.values()]
    if not sum(values):
        st.info("No merged PR records were retrieved in this period.")
        return
    fig = go.Figure(go.Bar(
        x=names, y=values,
        marker_color=BAR[:len(values)], text=[f'{v:,}' for v in values],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y:,} merged changes<extra></extra>",
    ))
    fig.update_layout(
        bargap=.43,
        xaxis_title="Time from opening to merge",
        yaxis_title="Merged pull requests",
        yaxis=dict(range=[0, max(values) * 1.20]),
    )
    _chart(fig, height=255)


def _outcome_bars(rows, period=30):
    """Percentages and denominators share the same time window as the KPI."""
    info = checks_in_period(rows, days=period)
    labels = [k for k in ("Success", "Failure / timeout", "Skipped", "Other outcomes")
              if info["counts"].get(k)]
    if not labels or not info["known"]:
        st.info("No completed automated checks with known outcomes were retrieved.")
        return
    colors = {"Success": GREEN, "Failure / timeout": RED,
              "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD}
    counts = [info["counts"][key] for key in labels]
    percentages = [100 * value / info["known"] for value in counts]
    fig = go.Figure(go.Bar(
        y=labels, x=percentages, orientation="h",
        marker_color=[colors[label] for label in labels],
        text=[f"{share:.1f}%  ({count:,})" for share, count in zip(percentages, counts)],
        textposition="outside", textfont=dict(size=10, color=INK),
        cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(bargap=.33, yaxis=dict(autorange="reversed"),
                      xaxis_title="Share of known results",
                      xaxis=dict(range=[0, 132], ticksuffix="%"))
    _chart(fig, height=235)
    st.caption(f'{info["known"]:,} known results · {period} days. '
               f'{info["unknown"]:,} unknown conclusions are excluded from the percentages.')



def _chart_title(title, note=""):
    st.markdown(f'<div class="d-chart-title">{esc(title)}</div>'
                f'<div class="d-chart-sub">{esc(note)}</div>', unsafe_allow_html=True)


def _scope(reports, key):
    if not reports:
        return []
    left_filter, right_filter = st.columns(2, gap="small")
    from src.ui.observed import verified_joint_cohort
    verified_28 = verified_joint_cohort(reports, days=28)
    verified_7 = verified_joint_cohort(reports, days=7)
    global_scope = st.session_state.get("global_evidence_scope", "")
    is_all_tracked = global_scope.startswith("All tracked")
    # The global scope has already filtered the input reports. Never describe
    # its verified subset as "All tracked" when other projects are excluded.
    all_label = ("All tracked projects · exploratory" if is_all_tracked
                 else "All projects in verified cohort")
    options = [
        "Verified all three sources · 28 days",
        "Verified all three sources · 7 days",
        all_label,
        "Code pushed · last 7 days",
        "Issue or PR events · last 7 days",
        "No recent signal · last 7 days",
        "Code pushed · last 30 days",
        "Issue or PR events · last 30 days",
        "No recent signal · last 30 days",
    ]
    # Verified-first is the global default. Preserve a valid custom filter,
    # but reset invalid stale Streamlit widgets when global scope changes.
    if global_scope.startswith("All tracked"):
        default_index = 2
    elif global_scope.startswith("Verified · 7"):
        default_index = 1
    else:
        default_index = 0 if verified_28 else 1 if verified_7 else 2
    activity_key = key + "_activity"
    if st.session_state.get(activity_key) not in (None, *options):
        st.session_state.pop(activity_key, None)
    with left_filter:
        mode = st.selectbox("Activity filter", options, index=default_index,
                            key=activity_key)
    chosen = []
    period = 30 if "30 days" in mode else 7
    if mode.startswith("Verified all three sources"):
        days = 28 if "28 days" in mode else 7
        chosen = verified_joint_cohort(reports, days=days)
        st.caption(
            f"{len(chosen)} of {len(reports)} tracked projects have independently "
            f"verified Issue, PR and CI/CD sources for the same {days}-day period. "
            "Excluded projects are not counted as inactive."
        )
    else:
        for r in reports:
            status = recent_activity(r, days=period)
            active = status["pushed_recently"] or status["recent_issue_or_pr_event"]
            if (mode == all_label
                    or mode.startswith("Code pushed") and status["pushed_recently"]
                    or mode.startswith("Issue or PR events") and status["recent_issue_or_pr_event"]
                    or mode.startswith("No recent signal") and not active):
                chosen.append(r)
    if not chosen:
        st.info(
            "No repositories qualify for the selected view. Missing verified "
            "coverage does not establish inactivity or missed deadlines."
        )
        return []
    if not mode.startswith("Verified"):
        if is_all_tracked:
            st.caption(
                "**Exploratory selection:** some displayed repositories may "
                "have incomplete source scans. Retrieved absence is not proof "
                "of inactivity; verify source-specific windows before inferring a trend."
            )
        else:
            st.caption(
                "**Within verified cohort:** the selected repositories still "
                "come from the global evidence scope. Push/activity filters are "
                "descriptive; a 30-day event filter does not certify a 30-day "
                "source history when only 28 days were verified."
            )
    names = [r["repository"]["full_name"] for r in chosen]
    with right_filter:
        picked = st.selectbox("Repository", ["All matching projects"] + names, key=key)
    return chosen if picked == "All matching projects" else [
        r for r in chosen if r["repository"]["full_name"] == picked]


def _available_total(reports, source, block, name):
    matched = [r for r in reports if r["status"].get(source) == "complete"
               and r[block].get(name) is not None]
    note = f"Verified in {len(matched)}/{len(reports)} repositories"
    return (_number(sum(r[block][name] for r in matched)) if matched else "—", note)


def _observed_note(reports, source):
    if all(r["status"].get(source) == "complete" for r in reports):
        return "Verified collected records"
    return "Retrieved records only · coverage may be incomplete or stale"


def _findings(reports, limit=3):
    # A small set of DIFFERENT finding types is more informative to HR than
    # six near-identical cards drawn from different repositories.
    candidates = portfolio_findings(reports, max_findings=max(limit, 10))
    seen = set()
    result = []
    for finding in candidates:
        if finding["type"] in seen:
            continue
        seen.add(finding["type"])
        result.append(finding)
        if len(result) >= limit:
            break
    return result


def _finding_visual(f):
    """Tiny evidence distribution; no health score or inferred benchmark."""
    kind = f.get("type")
    observed = None
    total = None
    suffix = "observed source records"
    # Show a real proportion ONLY for metrics with a meaningful denominator.
    # Do not turn median merge time or sample size into a fake percentage.
    if kind in ("issue-aging", "ci"):
        observed = f.get("observed")
        total = f.get("denominator")
        suffix = ("open issues 30+ days old" if kind == "issue-aging"
                  else "successful known automated checks")
    if observed is None or total is None or total <= 0:
        st.caption(f.get("metric_context", "Based on retrieved GitHub evidence"))
        return
    observed = min(total, max(0, observed))
    remainder = max(0, total - observed)
    share = observed / total
    st.progress(float(share),
                text=f"{int(observed):,} of {int(total):,} {suffix} ({share:.0%})")


def _findings_view(findings):
    types = {
        "issue-aging": "Older open tasks",
        "merge-duration": "Code review duration",
        "closure-change": "Change in issue closures",
        "ci": "Automated check outcomes",
    }
    if not findings:
        st.info("No evidence-backed findings meet the sample rules yet. "
                "Try a different repository or inspect collected source coverage.")
        return
    st.caption(
        "Inspection order is an evidence-review sequence, not a severity "
        "or project-health ranking. Multiple findings may meet the same "
        "'Review first' trigger; confirm the original GitHub record before "
        "deciding whether action is needed."
    )
    columns = st.columns(min(3, len(findings)), gap="small")
    for idx, f in enumerate(findings):
        with columns[idx % len(columns)]:
            with st.container(border=True):
                st.caption(
                    f'CHECK {idx + 1}/{len(findings)} · '
                    f'{f.get("review_priority", "Explore context")} '
                    f'· {f["scope"]}'
                )
                st.markdown(f'**{types.get(f["type"], "Evidence to inspect")}**')
                if f["type"] == "closure-change":
                    st.caption("Issues closed · two verified 28-day periods")
                    earlier, latest = st.columns(2, gap="small")
                    with earlier:
                        st.metric("Earlier 28d", f["previous_count"],
                                  help="Issue closures observed in the earlier period.")
                    with latest:
                        st.metric("Latest 28d", f["recent_count"],
                                  help="Issue closures observed in the current period.")
                elif f.get("metric_value"):
                    st.metric(f.get("metric_label", "Observed metric"),
                              f["metric_value"], help=f.get("evidence"))
                else:
                    st.write(f["headline"])
                _finding_visual(f)
                st.caption(f'Next check: {f["review"]}')
                plan = f.get("review_plan") or {}
                if plan.get("trigger"):
                    st.caption(f'Why inspect: {plan["trigger"]}')
                from src.analytics.review_decisions import evidence_action
                action = evidence_action(f)
                if action["url"]:
                    st.link_button(action["button"], action["url"],
                                   use_container_width=True)
                st.caption(action["disclosure"])
                with st.expander("Evidence and limitations"):
                    st.caption(f.get("evidence_scope", "Observed GitHub records"))
                    plan = f.get("review_plan") or {}
                    if plan.get("steps"):
                        st.markdown("**A three-step evidence review**")
                        for step in plan["steps"]:
                            st.write(step)
                    if plan.get("not_proven"):
                        st.caption("Not proven: " + plan["not_proven"])
                    st.write(f["evidence"])
                    st.write(f["interpretation"])
                    examples = f.get("examples") or []
                    if examples:
                        st.markdown("**Original records to inspect**")
                        st.caption("These are examples from retrieved data, not confirmed defects.")
                        for example in examples:
                            st.link_button(example["label"], example["url"],
                                           use_container_width=True)
                            st.caption(example["reason"])
                    else:
                        st.caption("No record-level example is available in this snapshot; "
                                   "use the source link above and check collection coverage.")


def _weekly(rows, days=84):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    first = (since - timedelta(days=since.weekday())).date()
    weeks = []
    cursor = first
    while cursor <= now.date():
        weeks.append(cursor)
        cursor += timedelta(weeks=1)
    counter = Counter()
    for row in rows:
        for field, label in (("created_at", "Opened"), ("closed_at", "Closed")):
            stamp = utc(row.get(field))
            if stamp and since <= stamp <= now:
                week = (stamp.date() - timedelta(days=stamp.weekday())).isoformat()
                counter[(week, label)] += 1
    return pd.DataFrame([
        {"Week": week.isoformat(), "Activity": activity,
         "Issues": counter[(week.isoformat(), activity)]}
        for week in weeks for activity in ("Opened", "Closed")
    ])


def _coverage_details(reports):
    with st.expander("About the data and its limitations"):
        st.caption("Updated-event coverage and full open-Issue inventory are independent. A complete 28-day updated-event scan does not cover every older open issue. A bounded backlog scan is complete only when all open-Issue pages were exhausted; otherwise the open counts remain samples. Missing records are not zero activity.")
        if reports:
            frame = pd.DataFrame([
                {"Repository": r["repository"]["full_name"],
                 "Issues": r["status"].get("issues"),
                 "Full open backlog": r.get("open_backlog_status", "unavailable"),
                 "Code changes": r["status"].get("pull_requests"),
                 "Automated checks": r["status"].get("workflow_runs"),
                 "Last source refresh": at_time(r.get("last_success"))}
                for r in reports
            ])
            st.dataframe(frame, hide_index=True, use_container_width=True)


def _coverage_banner(reports):
    from src.ui.observed import coverage_counts
    counts = coverage_counts(reports)
    count = len(reports)
    st.markdown(
        '<div class="d-coverage"><strong>Bounded source scans complete / tracked:</strong> '
        f'Issues {counts["issues"]}/{count} · '
        f'Pull requests {counts["pull_requests"]}/{count} · '
        f'GitHub Actions {counts["workflow_runs"]}/{count}. '
        '<em>These are recent-window scans, not full repository histories. '
        'All displayed totals use retrieved records only.</em></div>',
        unsafe_allow_html=True)


def _matched_snapshot_chart(chosen):
    paired = comparable_observation_pair(chosen)
    if paired:
        with st.container(border=True):
            _chart_title(
                "Open Issues across two verified inventory checks",
                f'{paired["previous_date"]} → {paired["current_date"]} · '
                f'{paired["matched_count"]} identical repositories with '
                'complete open-Issue inventories on both dates'
            )
            first, second = paired["previous_date"], paired["current_date"]
            before, after = paired["previous_issues"], paired["current_issues"]
            st.caption(
                f'Verified open Issues: {before:,} → {after:,} '
                f'({after-before:+,} items in the matched cohort). '
                'This is a change in observed open work, not a deadline '
                'or productivity score.'
            )
            ylo = max(0, min(before, after) -
                      max(1, round(max(before, after) * .10)))
            yhi = max(before, after) + max(
                1, round(max(before, after) * .15))
            if yhi <= ylo:
                yhi = ylo + 1
            fig = go.Figure(go.Scatter(
                x=[first, second], y=[before, after],
                mode="lines+markers+text",
                line=dict(color=PURPLE, width=3),
                marker=dict(size=11, color=PURPLE,
                            line=dict(color="white", width=2)),
                text=[f'{before:,}', f'{after:,}'],
                textposition="top center",
                hovertemplate="%{x}<br>Verified open Issues: %{y:,}<extra></extra>",
            ))
            fig.update_layout(
                yaxis=dict(range=[ylo, yhi], title="Open Issues in matched projects"),
                xaxis=dict(type="category", title=None),
            )
            _chart(fig, height=245)
            st.caption(
                "Open pull requests are intentionally excluded from this "
                "backlog-change chart because a full-open PR inventory has "
                "not been independently verified. A sampling change must "
                "not masquerade as real project progress."
            )
    else:
        with st.container(border=True):
            _chart_title("Opened vs completed activity · last 7 days",
                         "Compare events within each category; counts cover retrieved records only.")
            a = sample_activity(chosen, days=7)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Opened", x=["Issues", "Pull requests"],
                y=[a["new_issues"], a["new_prs"]],
                marker_color=PURPLE,
                text=[f'{a["new_issues"]:,}', f'{a["new_prs"]:,}'],
                textposition="outside", cliponaxis=False,
            ))
            fig.add_trace(go.Bar(
                name="Closed / merged", x=["Issues", "Pull requests"],
                y=[a["closed_issues"], a["merged_prs"]],
                marker_color=GREEN,
                text=[f'{a["closed_issues"]:,}', f'{a["merged_prs"]:,}'],
                textposition="outside", cliponaxis=False,
            ))
            fig.update_layout(barmode="group", bargap=.45,
                              yaxis_title="Observed events",
                              xaxis_title=None)
            _chart(fig, height=270, legend=True)
            st.caption("A comparable two-day snapshot is not yet available. "
                       "Older API events may be undercounted; these bars are not a historical growth trend.")


def overview(reports, selection, all_reports=None):
    """Show the true 75-repository denominator even in filtered view."""

    from src.ui.observed import summary
    st.markdown(
        '<div class="d-hero d-hero-overview"><div><span class="d-eyebrow">PUBLIC GITHUB · ACTIVITY MONITOR</span>'
        '<h1>Delivery activity at a glance.</h1>'
        '<p>Issues, code changes and automated checks—with source links.</p>'
        '</div><div class="d-mark">D / M</div></div>',
        unsafe_allow_html=True)
    if not reports:
        _kpis([("Projects tracked", "0", "No snapshot", "▣"),
               ("Open tasks retrieved", "—", "No available records", "◷"),
               ("Open code changes", "—", "No available records", "⇄"),
               ("Completed checks · 90d", "—", "No available records", "✓")])
        st.info("Run the public GitHub snapshot workflow to display real measurements.")
        return

    chosen = _scope(reports, "v2_scope")
    if not chosen:
        return
    info = summary(chosen)
    activity = sample_activity(chosen, days=7)
    scope = "Selected project" if len(chosen) == 1 else "Curated public sample"
    _kpis([
        ("Projects in analysis", _number(info["repositories"]),
         "Verified cohort or explicitly exploratory selection · tracked total shown in sidebar", "▣"),
        ("Open tasks retrieved", _number(info["open_issues"]), "Observed GitHub issues · not the full backlog", "◷"),
        ("Open code changes", _number(info["open_changes"]), "Observed PRs including drafts", "⇄"),
        ("Projects pushed · 7d", _number(activity["pushed_recently"]),
         "GitHub last-push metadata, not feature releases", "↗"),
    ])
    from src.ui.observed import evidence_readiness
    readiness = evidence_readiness(chosen)
    from src.ui.reviewer_cohort import decision_brief_cohort
    global_cohort = all_reports if all_reports is not None else reports
    cohort = decision_brief_cohort(global_cohort, chosen)
    initial_findings = _findings(chosen)
    next_subject = (
        initial_findings[0]["type"].replace("-", " ")
        if initial_findings else "source coverage before drawing conclusions"
    )
    st.markdown(
        f'**Decision brief:** {cohort["verified_28d"]}/{cohort["tracked"]} '
        'total tracked repositories have 28-day verified Issue, PR and CI sources. '
        f'This current filtered view contains {cohort["in_view"]} repositories. '
        f'First inspect **{esc(next_subject)}**, open the original GitHub evidence, '
        'then check source completeness. No client-deadline or quality verdict '
        'is inferred from these records.'
    )
    with st.expander("Evidence coverage · verified vs exploratory"):
        st.caption(
            "Evidence-ready cohorts within this selection: "
            f"**{readiness['joint_verified_7d']}/{readiness['tracked']}** projects "
            "have all three sources verified for 7 days; "
            f"**{readiness['joint_verified_28d']}/{readiness['tracked']}** "
            "for 28 days. A verified window uses existing source history; "
            "it does not require waiting 28 new days. Partial repositories "
            "remain accessible as explicitly exploratory observations. "
            "Unverified sources are retained, never deleted or counted as zero activity."
        )
    _section("01 / Activity over time",
             "Daily recorded events · 7 or 28 days · exploratory and verified scopes")
    trend_panel(chosen)

    # Keep the first chart visual-first. Follow it with a small executive
    # readout instead of a dense technical paragraph.
    finding_cards = initial_findings
    brief = executive_brief(chosen, findings=finding_cards)
    with st.container(border=True):
        st.caption("Quick reading · public development signals, not client deadlines")
        recent, review, confidence = st.columns([1.0, 1.4, 1.1], gap="medium")
        with recent:
            st.markdown("**Activity · last 7 days**")
            st.metric("Projects with a code push",
                      f'{brief["activity"]["recent_pushes"]:,}/{len(chosen):,}',
                      help="Repository last-push metadata. This does not prove a feature release.")
            st.caption(
                f'{brief["activity"]["opened_issues"]:,} issues opened · '
                f'{brief["activity"]["merged_prs"]:,} PRs merged '
                'in retrieved records. Missing records are not zero activity.'
            )
        with review:
            st.markdown("**What should we inspect?**")
            if brief["finding"]:
                lead = brief["finding"]
                st.markdown(f'**{lead["title"]}**')
                st.caption(
                    f'{lead["metric_label"]}: {lead["metric_value"]} '
                    f'· {lead["scope"]}'
                )
                if brief.get("why_review"):
                    st.caption("Why this deserves a look: " + brief["why_review"])
                st.caption(f'Next check: {brief["next_check"]}')
                if brief["source_url"]:
                    st.link_button("Open an original GitHub record",
                                   brief["source_url"], use_container_width=True)
            else:
                st.write("No source-backed finding passes the review thresholds.")
                st.caption("This is not proof that all monitored projects are healthy.")
        with confidence:
            st.markdown("**How complete is the evidence?**")
            verified = brief["coverage_28d"]
            st.metric("Verified Issues · 28d",
                      f'{verified["issues"]}/{len(chosen)}',
                      help="Number of source scans verified for the full last 28 days.")
            st.caption(
                f'PRs {verified["pull_requests"]}/{len(chosen)} · '
                f'CI checks {verified["workflow_runs"]}/{len(chosen)} verified '
                'for 28 days. Incomplete sources remain excluded from verified trends.'
            )

    _section("02 / Three evidence-backed checks",
             "Numbers, context and a direct next step—not unverified project-health scores")
    _findings_view(finding_cards)

    with st.expander("Source completeness, periods and technical terms"):
        _coverage_banner(chosen)
        coverage_progress(chosen)
        st.markdown(
            "**Issues:** reported tasks or bugs. "
            "**PR:** proposed code changes. "
            "**Merge:** code changes incorporated into a repository. "
            "**CI/CD checks:** automated tests and builds, not proof of overall quality."
        )
        st.caption(
            "The overview uses 7-day push and event metadata, the line uses "
            "a selectable 7/28-day window, and the check outcome donut uses "
            "the last 28 days. Different windows are always labelled."
        )

    _section("03 / Delivery activity", "What remains open, and how did automatic checks perform?")
    left, right = st.columns([1.1, 1], gap="large")
    with left, st.container(border=True):
        _chart_title("Open issues by age", "Time since creation · not a deadline assessment.")
        bands = observed_age_bands(info["issue_rows"])
        _horizontal_bars(list(bands), list(bands.values()), BAR,
                         height=250, unit="Observed open issues")
    with right, st.container(border=True):
        _chart_title("Automated check outcomes", "Share of known GitHub Actions results · last 28 days.")
        _ci_donut(info["ci_rows"], period=28)

    _section("04 / Matched snapshot change",
             "A trend is shown only for projects with comparable validated observations on two different days.")
    _matched_snapshot_chart(chosen)

    _section("05 / Where are new changes happening?", "Recent activity is not a score of project quality or developer productivity.")
    rows = []
    for report, a in sample_activity(chosen, days=7)["items"]:
        events = a["new_issues"] + a["closed_issues"] + a["new_prs"] + a["merged_prs"]
        if events:
            rows.append({
                "Repository": report["repository"]["full_name"],
                "Recent issue/PR events": events,
                "Opened issues": a["new_issues"],
                "Closed issues": a["closed_issues"],
                "Opened PRs": a["new_prs"],
                "Merged PRs": a["merged_prs"],
                "GitHub": report["repository"]["url"],
            })
    if rows:
        view = pd.DataFrame(rows).sort_values("Recent issue/PR events", ascending=False)
        top = view.head(8).sort_values("Recent issue/PR events")
        with st.container(border=True):
            _chart_title("Where observed activity happened · 7 days",
                         "Stacked by issue versus pull-request events; not a project-quality ranking.")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Issue events", orientation="h",
                y=top["Repository"].tolist(),
                x=(top["Opened issues"] + top["Closed issues"]).tolist(),
                marker_color=PURPLE,
                hovertemplate="%{y}<br>Issue events: %{x:,}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                name="PR events", orientation="h",
                y=top["Repository"].tolist(),
                x=(top["Opened PRs"] + top["Merged PRs"]).tolist(),
                marker_color=GREEN,
                hovertemplate="%{y}<br>Pull-request events: %{x:,}<extra></extra>",
            ))
            fig.update_layout(barmode="stack", bargap=.33,
                              xaxis_title="Observed events",
                              yaxis_title=None, margin=dict(l=10, r=25, t=8, b=45))
            _chart(fig, height=max(290, len(top) * 37), legend=True)
            st.caption("The same change can generate multiple events. "
                       "These counts describe captured GitHub activity, not effort or development quality.")
        with st.expander("Inspect recent event counts and source links"):
            st.dataframe(view, hide_index=True, use_container_width=True,
                         column_config={"GitHub": st.column_config.LinkColumn(
                             "Original repository", display_text="Open ↗")})
    else:
        st.info("No new issue or PR events are present in the retrieved 7-day window.")
    with st.expander("About the 75-project sample · languages and categories"):
        left, right = st.columns([1, 1])
        from src.ui.charts import category_counts
        with left:
            cats = pd.DataFrame([{"Category": k, "Projects": v}
                                 for k, v in category_counts(chosen).items()])
            if not cats.empty:
                fig = px.bar(cats.sort_values("Projects"), x="Projects", y="Category",
                             orientation="h", color_discrete_sequence=[PURPLE])
                _chart(fig, height=max(230, 33 * len(cats)))
        with right:
            counts = Counter(r["repository"].get("language") or "Not specified" for r in chosen)
            langs = pd.DataFrame([{"Language": k, "Projects": v}
                                  for k, v in counts.most_common(7)])
            if not langs.empty:
                fig = px.bar(langs.sort_values("Projects"), x="Projects", y="Language",
                             orientation="h", color_discrete_sequence=[PURPLE_LIGHT])
                _chart(fig, height=max(230, 33 * len(langs)))
    _coverage_details(chosen)


def project_details(reports):
    _heading("REPOSITORY EXPLORER", "Explore a project",
             "Select a repository, see recent observations, and inspect the actual GitHub records.", reports)
    r = select_repo(reports, "v2_details_repo")
    if not r:
        empty_state("No repository selected")
        return
    repo = r["repository"]
    st.markdown(f'<div class="d-repo-header"><strong>{esc(repo["full_name"])}</strong>'
                f'<small>{esc(repo.get("category") or "Other")} · '
                f'{esc(repo.get("language") or "Language not provided")}</small></div>',
                unsafe_allow_html=True)
    st.link_button("Open GitHub project ↗", repo["url"])
    recent = recent_activity(r)
    st.caption(
        f"7-day activity: {activity_label(r)} · "
        f"{recent['new_issues']} issues opened · "
        f"{recent['new_prs']} PRs opened · "
        f"{recent['merged_prs']} PRs merged. "
        "A recent push is not proof of a feature release."
    )
    observed = summary([r])
    _kpis([
        ("Open tasks retrieved", _number(observed["open_issues"]), "Observed GitHub issues", "◷"),
        ("Open code changes", _number(observed["open_changes"]), "Observed PRs", "⇄"),
        ("Completed checks · 90d", _number(observed["completed_checks"]), "Observed GitHub Actions runs", "✓"),
        ("Last repository push", utc(repo["pushed_at"]).strftime("%d %b") if repo.get("pushed_at") else "—",
         "GitHub metadata timestamp", "↗"),
    ])
    st.caption("Counts describe retrieved records. Use Source details to inspect completeness.")
    a, side_by_side, b, c = st.tabs(["Activity history", "Compare two projects",
                                      "Compare projects", "Source details"])
    with a:
        from src.analytics.comparison_views import current_history_evidence
        current = current_history_evidence(r)
        st.markdown("**Current collected snapshot**")
        if current["count"] is None:
            st.info("No collected open-Issue records are available in this source. "
                    "The collector has not verified an empty backlog.")
        else:
            st.metric(current["label"], f'{current["count"]:,}')
        st.caption(current["scope"])
        st.caption(
            "Last qualifying inventory/source check: "
            + at_time(current["measured_at"])
            + ". This is not a project SLA or overdue-work measurement."
        )
        pair = comparable_observation_pair([r])
        if pair is not None:
            st.markdown("**Verified historical comparison · same repository**")
            st.caption(
                f'{pair["previous_date"]} → {pair["current_date"]} · '
                "two independent verified full-open Issue inventories"
            )
            before, after = pair["previous_issues"], pair["current_issues"]
            st.metric("Change in verified open Issues", f'{after - before:+,}',
                      help=f"Verified open Issues: {before:,} then {after:,}. "
                           "Different observation dates; no deadlines inferred.")
            fig = go.Figure(go.Scatter(
                x=[pair["previous_date"], pair["current_date"]],
                y=[before, after], mode="lines+markers+text",
                line=dict(color=PURPLE, width=3),
                marker=dict(color=PURPLE, size=10),
                text=[str(before), str(after)], textposition="top center"
            ))
            fig.update_layout(yaxis_title="Verified open Issues")
            _chart(fig, height=235)
            st.caption("Only open Issues are compared: open PRs have a different "
                       "inventory verification method and are not a backlog trend.")
        else:
            st.info(
                "A verified open-backlog change needs complete inventories on "
                "two different UTC dates for this exact repository. The system "
                "does not join incomplete update samples or invent a trend."
            )
            bands = observed_age_bands(r["issue_rows"])
            if sum(bands.values()):
                _chart_title("Open Issue ages in the current retrieved records",
                             "Single snapshot · observed sample, not historical change")
                fig = go.Figure(go.Bar(
                    x=list(bands), y=list(bands.values()),
                    marker_color=BAR, text=list(bands.values()),
                    textposition="outside"))
                fig.update_layout(yaxis_title="Observed open Issues")
                _chart(fig, height=250)
                st.caption("These Issue ages are descriptive, not a deadline "
                           "or missed-milestone indicator.")
            else:
                st.caption("No open Issues were retrieved for this snapshot; "
                           "this does not establish the complete backlog is zero.")
        observed_entries = sorted(
            (v for v in r.get("observations") or []
             if v.get("collection_basis") == "verified_open_inventory"),
            key=lambda v: utc(v["measured_at"]), reverse=True,
        )
        with st.expander("Recorded full-inventory observations and provenance"):
            if observed_entries:
                st.dataframe(pd.DataFrame([
                    {
                        "Observed at (UTC)": utc(v["measured_at"]).isoformat()[:19],
                        "Verified open Issues": v["open_issues_observed"],
                        "Basis": v["collection_basis"],
                    } for v in observed_entries
                ]), hide_index=True, use_container_width=True)
            else:
                st.caption("No independently verified full-open inventory "
                           "observation has been recorded for this repository.")
    with side_by_side:
        compare_two_repositories(reports)
    with b:
        comparison(reports, embedded=True)
    with c:
        source_coverage(r)


def issues_backlog(reports):
    _heading("WORK TRACKING", "Open issues",
             "Which tasks remain open, and how long have they existed?", reports)
    r = select_repo(reports, "v2_issues_repo")
    if not r:
        empty_state("No repository selected")
        return
    info = r["issues"]
    observed = summary([r])
    full_backlog = r.get("open_backlog_status") == "complete"
    _kpis([
        ("Open tasks retrieved", _number(observed["open_issues"]),
         "Retrieved GitHub Issues · not necessarily full backlog", "◷"),
        ("30+ days old · observed", _number(info["sample_aged_open"]),
         "Observed sample age · not a missed deadline", "◴"),
        ("Share aged 30+ days" if full_backlog else "Share aged · sample only",
         _percent(info["aged_percent"] if full_backlog
                  else info["sample_aged_percent"]),
         "Verified full open-Issue inventory" if full_backlog
         else "Sample of retrieved open Issues; may omit older items", "%"),
    ])
    if full_backlog:
        st.caption("Full open-Issue inventory scan finished for this repository. "
                   "Open-item counts reflect that scan; source event trends "
                   "still need their own 28-day verification.")
    else:
        st.caption(
            "Open-task counts use retrieved Issue records, not a verified "
            "full backlog. Older Issues that were never recently updated "
            "may be missing. Independent open-inventory scan: " +
            str(r.get("open_backlog_status", "unavailable")) + "."
        )
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(border=True):
        _chart_title("Age of observed open issues",
                     "Long-lived issues are not automatically overdue.")
        _issue_age_donut(r["issue_rows"])
    with c2, st.container(border=True):
        _chart_title("Issue activity · last 7 days",
                     "Actual opened and closed events in retrieved records.")
        a = recent_activity(r, days=7)
        _horizontal_bars(["Opened", "Closed"],
                         [a["new_issues"], a["closed_issues"]],
                         [PURPLE, GREEN], height=248, unit="Issue events")
        st.caption(
            f"Reading: {a['new_issues']:,} observed tasks opened vs "
            f"{a['closed_issues']:,} closed in 7 days. "
            "These event counts do not prove how the entire project backlog changed."
        )
    _section("Inspect the original issues")
    a, b, c = st.columns([2, 1, 1])
    with a:
        search = st.text_input("Search a task", placeholder="Issue title or number", key="v2_issue_search")
    with b:
        state = st.selectbox("Status", ["Open", "Closed", "All"], key="v2_issue_state")
    with c:
        age = st.selectbox("Age", ["All", "0–6 days", "7–29 days",
                                   "30–89 days", "90+ days"], key="v2_issue_age")
    matches = filter_work_items(r["issue_rows"], search=search, state=state, age=age)
    rows = [{**x, "age_days": round(issue_age_days(x), 1)} for x in matches]
    table_rows(rows, ["number", "title", "state", "age_days", "url"], "v2_issues_page")
    _coverage_details([r])


def pull_request_review(reports):
    _heading("CODE CHANGES", "Changes & reviews",
             "Understand open code changes and how long completed changes took.", reports)
    r = select_repo(reports, "v2_pr_repo")
    if not r:
        empty_state("No repository selected")
        return
    info = r["prs"]
    observed = summary([r])
    from src.ui.observed import qualified_reports
    if not qualified_reports([r], "pull_requests", days=90):
        st.caption(
            "The 90-day PR view contains retrieved records and may be "
            "incomplete. Its counts are observations, not the total "
            "number of changes across all 90 days."
        )
    _kpis([
        ("Open changes retrieved", _number(observed["open_changes"]), "Includes draft pull requests", "⇄"),
        ("Draft changes", _number(observed["draft_changes"]), "Of observed open changes", "◈"),
        ("Merged · 90 days", _number(observed["merged_changes"]), "Observed merge timestamps", "✓"),
        ("Median merge time", _duration(info.get("median_merge_days")),
         "Only with sufficient verified coverage", "◷"),
    ])
    st.caption("Counts describe retrieved PR records; the median is withheld without sufficient evidence.")
    buckets = info.get("merge_distribution")
    if buckets is None:
        buckets = observed_merge_times(r["pr_rows"])
    has_merges = sum(buckets.values()) > 0
    with st.container(border=True):
        if has_merges:
            _chart_title("Time from PR creation to merge",
                         "Observed merged pull requests · last 90 days.")
            _duration_columns(buckets)
            merged_total = sum(buckets.values())
            first_bucket = next(iter(buckets.values()))
            st.caption(
                f"Reading: {first_bucket:,} of {merged_total:,} observed merged changes "
                f"({first_bucket / merged_total:.0%}) finished within the first duration band. "
                "Change complexity differs; this is not a developer productivity ranking."
            )
        elif observed["open_changes"]:
            _chart_title("Open pull requests by status",
                         "No merged pull requests were retrieved in this period.")
            draft_count = observed["draft_changes"] or 0
            ready_count = max(0, observed["open_changes"] - draft_count)
            _horizontal_bars(["Draft", "Ready for review"],
                             [draft_count, ready_count],
                             [PURPLE_LIGHT, PURPLE], height=220,
                             unit="Retrieved open changes")
            st.caption("Open or draft state alone does not demonstrate a blockage or late delivery.")
        else:
            st.info("No merged or open pull request records were retrieved in the period.")
    _section("Explore original pull requests")
    a, b, c = st.columns([2, 1, 1])
    with a:
        search = st.text_input("Search a change", key="v2_pr_search")
    with b:
        state = st.selectbox("Status", ["All", "Open", "Closed"], key="v2_pr_state")
    with c:
        draft = st.selectbox("Draft", ["All", "Draft only", "Not draft"], key="v2_pr_draft")
    rows = filter_pull_requests(r["pr_rows"], search, state, draft)
    table_rows(rows, ["number", "title", "state", "draft",
                      "created_at", "merged_at", "url"], "v2_pr_page")
    _coverage_details([r])


def cicd_activity(reports):
    _heading("AUTOMATED CHECKS", "Build activity",
             "See GitHub Actions results for the same period in every chart and KPI.", reports)
    r = select_repo(reports, "v2_ci_repo")
    if not r:
        empty_state("No repository selected")
        return
    period = st.selectbox("Observation period", [28, 90],
                          format_func=lambda d: f"Last {d} days", key="v3_ci_period")
    info = checks_in_period(r["ci_rows"], days=period)
    from src.ui.observed import qualified_reports
    if not qualified_reports([r], "workflow_runs", days=period):
        st.warning(
            f"Only a retrieved sample is available for the selected {period}-day "
            "CI/CD period; the source has not verified this entire interval. "
            "Outcome percentages describe retrieved known runs only."
        )
    _kpis([
        (f"Completed checks · {period}d", _number(info["total"]),
         "Retrieved GitHub Actions runs", "▣"),
        ("Succeeded", _number(info["success"]), "Known results only", "✓"),
        ("Failed / timed out", _number(info["failure"]), "Known results only", "×"),
        ("Success share", _percent(info["success_percent"]),
         f'{info["known"]} known results · {period}d', "%"),
    ])
    st.caption(
        (
            f'**Outcome definitions · {period} days:** '
            f'{info["success"]:,} succeeded · '
            f'{info["failure"]:,} failed/timed out · '
            f'{info["skipped"]:,} skipped · '
            f'{info["other"]:,} other known results. '
            f'{info["unknown"]:,} runs have unknown conclusions and are excluded '
            f'from the success rate. **{info["success"]:,}/{info["known"]:,}** '
            "known outcomes succeeded. Skipped/cancelled/other are not "
            "automatically software failures; CI outcome is not a quality score."
        ) if info["known"] else
        "No completed runs with known conclusions are available. A success "
        "rate cannot be calculated; missing conclusions are not failures."
    )
    left, right = st.columns([1.12, .88], gap="large")
    with left, st.container(border=True):
        _chart_title(f"Weekly automated checks · {period} days",
                     "Stacked outcomes by week · known results only.")
        if info["daily"]:
            df = pd.DataFrame(info["daily"])
            df["Week"] = pd.to_datetime(df["Day"]).dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
            df = df.groupby(["Week", "Outcome"], as_index=False)["Runs"].sum()
            fig = px.bar(df, x="Week", y="Runs", color="Outcome", barmode="stack",
                 color_discrete_map={
                     "Success": GREEN, "Failure / timeout": RED,
                     "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD})
            fig.update_layout(bargap=.26, xaxis_title=None, yaxis_title="Observed runs")
            _chart(fig, height=285, legend=True)
        else:
            st.info("No completed workflow runs with known outcomes in this period.")
    with right, st.container(border=True):
        _chart_title(f"Outcome distribution · {period} days",
                     f'{info["known"]:,} known results · same window as the KPIs.')
        _ci_donut(r["ci_rows"], period=period)
    if r["status"].get("workflow_runs") != "complete":
        st.caption("The repository's source scan is incomplete or older. "
                   "Observed results may omit other runs; do not generalize this rate.")
    _section("Inspect individual GitHub Actions runs",
             "Open any recorded workflow for the source evidence.")
    a, b, c = st.columns([2, 1, 1])
    with a:
        term = st.text_input("Find a workflow", key="v2_ci_search")
    with b:
        outcome = st.selectbox("Outcome", ["All", "success", "failure",
                  "timed_out", "skipped", "cancelled"], key="v2_ci_outcome")
    with c:
        branches = sorted({str(v["branch"]) for v in r["ci_rows"] if v.get("branch")})
        branch = st.selectbox("Branch", ["All"] + branches, key="v2_ci_branch")
    rows = filter_workflow_runs(r["ci_rows"], term, outcome, branch)
    now = datetime.now(timezone.utc)
    rows = [v for v in rows if v.get("created_at")
            and now - timedelta(days=period) <= utc(v["created_at"]) <= now]
    table_rows(rows, ["workflow_name", "branch", "event", "conclusion",
                      "created_at", "url"], "v2_ci_page")
    _coverage_details([r])

def risks_recommendations(reports, selection):
    _heading("ACTIONABLE FINDINGS", "Where should we look next?",
             "Evidence-backed observations with a direct link to the actual records.", reports)
    from src.ui.observed import coverage_counts
    found = _findings(reports, limit=3)
    verified = coverage_counts(reports)
    _kpis([
        ("Evidence-based findings", _number(len(found)), "Observed data with original source links", "◎"),
        ("Projects for review", _number(len({x["scope"] for x in found})),
         "Suggestions, not confirmed defects", "◷"),
        ("Verified issue sources", f'{verified["issues"]}/{len(reports)}' if reports else "—",
         "Coverage is not a quality score", "✓"),
    ])
    if reports:
        _coverage_banner(reports)
    _section("Priorities for a closer look",
             "Source-linked observations; inspection priority is not a project-quality ranking.")
    _findings_view(found)
    if found:
        from src.analytics.review_decisions import review_csv
        st.download_button(
            "Export evidence review plan (CSV)",
            data=review_csv(found),
            file_name="delivery-monitor-evidence-review.csv",
            mime="text/csv", key="p1_review_plan_csv",
            help="The same source-backed findings currently shown above. "
                 "Records and decisions are not invented.",
        )
    st.caption("Review first is a transparent inspection priority—not proof of delay. "
               "Record-level links in each expanded finding allow the reviewer to test the claim. "
               "It does not mean a project is delayed, low-quality, or has a confirmed defect.")
    with st.expander("Data selection, formulas and limitations"):
        methodology_contents(reports, selection)


# Keep old domain calculations and searchable evidence displays intact.
