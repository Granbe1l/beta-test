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
    status = status_for(reports)
    statuses = {
        "complete": "Sources verified", "partial": "Coverage in progress",
        "stale": "Coverage in progress", "failed": "Collection needs review",
        "unavailable": "Sources unavailable",
    }
    good = "ok" if status == "complete" else ""
    st.markdown(
        f'<div class="d-heading"><div><div class="d-overline">{esc(kicker)}</div>'
        f'<h1>{esc(title)}</h1><p>{esc(note)}</p></div>'
        f'<span class="d-status {good}">{esc(statuses.get(status, status.title()))}</span>'
        '</div>', unsafe_allow_html=True)


def _kpis(cards):
    """Compact, responsive cards; never interactive/injected source content."""
    fragments = []
    for label, value, context, glyph in cards:
        fragments.append(
            f'<div class="d-kpi"><div class="d-kpi-label"><span>{esc(label)}</span>'
            f'<span class="d-kpi-icon">{esc(glyph)}</span></div>'
            f'<div class="d-kpi-value">{esc(value)}</div>'
            f'<div class="d-kpi-note">{esc(context)}</div></div>'
        )
    st.markdown('<div class="d-kpis">' + ''.join(fragments) + '</div>',
                unsafe_allow_html=True)


def _chart(fig, height=270, legend=False):
    fig.update_layout(
        template="plotly_white", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=9, r=12, t=22, b=12),
        font=dict(family="Inter, Arial, sans-serif", color=INK, size=11),
        showlegend=legend,
        legend=dict(orientation="h", y=1.17, title=None),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=INK),
    )
    fig.update_xaxes(showgrid=False, linecolor="#EAE4F3", zeroline=False)
    fig.update_yaxes(gridcolor="#F1EDF8", zeroline=False)
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


def _chart_title(title, note=""):
    st.markdown(f'<div class="d-chart-title">{esc(title)}</div>'
                f'<div class="d-chart-sub">{esc(note)}</div>', unsafe_allow_html=True)


def _scope(reports, key):
    if not reports:
        return []
    left_filter, right_filter = st.columns(2, gap="small")
    with left_filter:
        mode = st.selectbox("Activity filter", [
            "All tracked projects",
            "Code pushed · last 7 days",
            "Issue or PR events · last 7 days",
            "No recent signal · last 7 days",
        ], key=key + "_activity")
    chosen = []
    for r in reports:
        status = recent_activity(r)
        active = status["pushed_recently"] or status["recent_issue_or_pr_event"]
        if (mode == "All tracked projects"
                or mode == "Code pushed · last 7 days" and status["pushed_recently"]
                or mode == "Issue or PR events · last 7 days" and status["recent_issue_or_pr_event"]
                or mode == "No recent signal · last 7 days" and not active):
            chosen.append(r)
    if not chosen:
        st.info("No matching signal was observed. That does not mean the projects are finished.")
        return []
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


def _findings_view(findings):
    types = {
        "issue-aging": "Older open tasks",
        "merge-duration": "How code changes get merged",
        "closure-change": "Change in issue closures",
        "ci": "Automated check outcomes",
    }
    if not findings:
        st.info("No source-verified insight meets the evidence rules yet. More data is needed before claiming a trend or issue.")
        return
    columns = st.columns(2, gap="medium")
    for idx, f in enumerate(findings):
        with columns[idx % 2]:
            with st.container(border=True):
                st.caption(f'{idx + 1:02d} · {f["scope"]}')
                st.markdown(f'**{types.get(f["type"], "Evidence to inspect")}**')
                st.write(f["headline"])
                with st.expander("What does the evidence mean?"):
                    st.write(f["evidence"])
                    st.write(f["interpretation"])
                st.caption(f'Next step: {f["review"]}')
                if f.get("url"):
                    st.link_button("View original GitHub records", f["url"])


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
        st.caption("Selected, bounded public GitHub repositories. A complete bounded scan does not mean the full issue/PR history was collected. Missing records are not zero activity; a push does not prove feature development.")
        if reports:
            frame = pd.DataFrame([
                {"Repository": r["repository"]["full_name"],
                 "Issues": r["status"].get("issues"),
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
            _chart_title("Change in open work across verified snapshots",
                f'{paired["previous_date"]} vs {paired["current_date"]} · '
                f'{paired["matched_count"]} identical repositories observed on both days')
            frame = pd.DataFrame([
                {"Type": "Open issues", "Snapshot": paired["previous_date"],
                 "Observed count": paired["previous_issues"]},
                {"Type": "Open issues", "Snapshot": paired["current_date"],
                 "Observed count": paired["current_issues"]},
                {"Type": "Open pull requests", "Snapshot": paired["previous_date"],
                 "Observed count": paired["previous_prs"]},
                {"Type": "Open pull requests", "Snapshot": paired["current_date"],
                 "Observed count": paired["current_prs"]},
            ])
            fig = px.bar(frame, x="Type", y="Observed count", color="Snapshot",
                         barmode="group", text="Observed count",
                         color_discrete_sequence=[PURPLE_LIGHT, PURPLE])
            _chart(fig, height=265, legend=True)
            st.caption("Only projects with source-validated observations on both dates are compared. "
                       "This is not a comparison of all 75 projects, and open work alone cannot measure delivery speed.")
    else:
        with st.container(border=True):
            _chart_title("Most recently observed events", "Last 7 days · descriptive snapshot")
            recent = sample_activity(chosen, days=7)
            frame = pd.DataFrame([
                {"Event": "Issues opened", "Observed count": recent["new_issues"]},
                {"Event": "Issues closed", "Observed count": recent["closed_issues"]},
                {"Event": "PRs opened", "Observed count": recent["new_prs"]},
                {"Event": "PRs merged", "Observed count": recent["merged_prs"]},
            ])
            fig = px.bar(frame, x="Event", y="Observed count",
                         color_discrete_sequence=[PURPLE], text="Observed count")
            _chart(fig, height=235)
            st.caption("No two-day verified snapshot comparison is available yet. "
                       "The bars show collected event timestamps only; comparing older weeks could "
                       "create a false rising trend because old records are under-sampled.")


def overview(reports, selection):
    from src.ui.observed import summary
    st.markdown(
        '<div class="d-hero"><div><span class="d-eyebrow">PUBLIC GITHUB · PROJECT DELIVERY MONITOR</span>'
        '<h1>Monitor real GitHub project activity.</h1>'
        '<p>Explore recent development signals, open tasks, code changes and checks—'
        'with evidence you can inspect.</p></div><div class="d-mark">D / M</div></div>',
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
        ("Projects tracked", _number(info["repositories"]), scope, "▣"),
        ("Open tasks retrieved", _number(info["open_issues"]), "Observed GitHub issues · not the full backlog", "◷"),
        ("Open code changes", _number(info["open_changes"]), "Observed PRs including drafts", "⇄"),
        ("Projects pushed · 7d", _number(activity["pushed_recently"]),
         "GitHub last-push metadata, not feature releases", "↗"),
    ])
    _coverage_banner(chosen)
    st.markdown(
        '<div class="d-context"><strong>Last 7 days (retrieved records):</strong> '
        f'{activity["new_issues"]:,} issues opened · '
        f'{activity["closed_issues"]:,} issues closed · '
        f'{activity["new_prs"]:,} PRs opened · '
        f'{activity["merged_prs"]:,} PRs merged. '
        '<span>These are recorded events; incomplete collection can omit activity.</span>'
        '</div>', unsafe_allow_html=True)

    _section("01 / Delivery activity", "What is still open, and what happened in recent automated checks?")
    left, right = st.columns([1.1, 1], gap="large")
    with left, st.container(border=True):
        _chart_title("Age of retrieved open tasks", "These are open GitHub issues; age is not a deadline.")
        bands = observed_age_bands(info["issue_rows"])
        if sum(bands.values()):
            fig = go.Figure(go.Bar(y=list(bands), x=list(bands.values()),
                orientation="h", marker_color=BAR, text=list(bands.values()),
                textposition="outside", hovertemplate="%{y}: %{x} open tasks<extra></extra>"))
            fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Retrieved open tasks")
            _chart(fig)
        else:
            st.info("No open task records were retrieved for this selection.")
    with right, st.container(border=True):
        _chart_title("Automated checks · last 30 days", "Outcome split of completed GitHub Actions runs.")
        outcomes = {k: v for k, v in observed_outcomes(info["ci_rows"], days=30).items() if v}
        if outcomes:
            colors = [{"Success": GREEN, "Failure / timeout": RED,
                       "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD}.get(k, PURPLE)
                      for k in outcomes]
            fig = go.Figure(go.Pie(labels=list(outcomes), values=list(outcomes.values()),
                hole=.65, marker=dict(colors=colors), textinfo="percent",
                hovertemplate="%{label}: %{value} runs<extra></extra>"))
            fig.update_layout(annotations=[dict(text=f'{sum(outcomes.values()):,} checks',
                x=.5, y=.5, showarrow=False, font=dict(size=14, color=INK))])
            _chart(fig, legend=True)
        else:
            st.info("No completed GitHub Actions outcomes were retrieved during the last 30 days.")

    _section("02 / Compare change without sample bias",
             "A trend is shown only for projects with comparable validated observations on two different days.")
    _matched_snapshot_chart(chosen)

    _section("03 / What needs a closer look?", "Only findings supported by sufficient verified source data appear below.")
    _findings_view(_findings(chosen))
    _section("04 / Where are new changes happening?", "Recent activity is not a score of project quality or developer productivity.")
    rows = []
    for report, a in sample_activity(chosen, days=7)["items"]:
        events = a["new_issues"] + a["closed_issues"] + a["new_prs"] + a["merged_prs"]
        if events:
            rows.append({
                "Repository": report["repository"]["full_name"],
                "Recent issue/PR events": events,
                "Opened issues": a["new_issues"],
                "Opened PRs": a["new_prs"],
                "Merged PRs": a["merged_prs"],
                "GitHub": report["repository"]["url"],
            })
    if rows:
        view = pd.DataFrame(rows).sort_values("Recent issue/PR events", ascending=False)
        top = view.head(10).sort_values("Recent issue/PR events")
        with st.container(border=True):
            _chart_title("Projects with the most observed events · 7d",
                         "Issue open/close + PR open/merge events in this sample; counts are not performance rankings.")
            fig = px.bar(top, x="Recent issue/PR events", y="Repository",
                         orientation="h", color_discrete_sequence=[PURPLE],
                         text="Recent issue/PR events")
            _chart(fig, height=min(460, max(255, len(top) * 36)))
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
    a, b, c = st.tabs(["Activity history", "Compare projects", "Source details"])
    with a:
        observations = sorted(r.get("observations") or [],
                              key=lambda x: utc(x["measured_at"]))
        if len(observations) >= 2:
            df = pd.DataFrame([
                {"Observation": utc(v["measured_at"]).isoformat()[:16],
                 "Open issues": v["open_issues_observed"],
                 "Open changes": v["open_prs_observed"]}
                for v in observations])
            fig = px.line(df, x="Observation", y=["Open issues", "Open changes"],
                          markers=True, color_discrete_sequence=[PURPLE, GREEN])
            _chart(fig, legend=True)
        elif observations:
            st.caption("One real snapshot is available; a time trend requires at least two.")
            bands = observed_age_bands(r["issue_rows"])
            if sum(bands.values()):
                _chart_title("Open task age in this snapshot", "Observed issue records—not a delay score.")
                fig = go.Figure(go.Bar(
                    x=list(bands), y=list(bands.values()), marker_color=BAR,
                    text=list(bands.values()), textposition="outside"))
                _chart(fig, height=240)
            else:
                st.info("There are no collected open issue records to chart yet.")
        else:
            st.info("No observation history has been collected yet.")
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
    _kpis([
        ("Open tasks retrieved", _number(observed["open_issues"]), "Observed issue records", "◷"),
        ("30+ days old", _number(observed["aged_issues"]), "Open task age · not lateness", "◴"),
        ("Share aged 30+ days", _percent(observed["aged_share"]), "Of retrieved open tasks", "%"),
    ])
    st.caption("Issue cards and charts count the same retrieved records—not the complete backlog.")
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(border=True):
        _chart_title("Issue age groups", _observed_note([r], "issues"))
        bands = observed_age_bands(r["issue_rows"])
        if sum(bands.values()):
            fig = go.Figure(go.Bar(x=list(bands), y=list(bands.values()),
                        marker_color=BAR, text=list(bands.values()), textposition="outside"))
            _chart(fig)
        else:
            st.info("No observed open issues to chart.")
    with c2, st.container(border=True):
        _chart_title("Opened vs closed", "12 weeks · full observation coverage required")
        if r["issue_rows"]:
            fig = px.line(_weekly(r["issue_rows"]), x="Week", y="Issues", color="Activity",
                          markers=True, color_discrete_map={"Opened": PURPLE, "Closed": GREEN})
            _chart(fig, legend=True)
            st.caption("Retrieved activity only; missing source coverage can omit events.")
        else:
            st.info("No issue records were retrieved for this repository.")
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
    _kpis([
        ("Open changes retrieved", _number(observed["open_changes"]), "Includes draft pull requests", "⇄"),
        ("Draft changes", _number(observed["draft_changes"]), "Of observed open changes", "◈"),
        ("Merged · 90 days", _number(observed["merged_changes"]), "Observed merge timestamps", "✓"),
        ("Median merge time", _duration(info.get("median_merge_days")),
         "Only with sufficient verified coverage", "◷"),
    ])
    st.caption("Counts describe retrieved PR records; the median is withheld without sufficient evidence.")
    l, rcol = st.columns([1.2, .8], gap="large")
    with l, st.container(border=True):
        buckets = info.get("merge_distribution")
        if buckets is None:
            buckets = observed_merge_times(r["pr_rows"])
        has_merges = sum(buckets.values()) > 0
        _chart_title(
            "Time to finish merged changes" if has_merges else "Open changes by review status",
            "Creation → merge · last 90 days" if has_merges
            else "Observed open pull requests (draft vs ready for review)")
        if has_merges:
            if info.get("merge_distribution") is None:
                st.caption("Retrieved sample only; a repository-wide measure is not verified.")
            fig = go.Figure(go.Bar(x=list(buckets), y=list(buckets.values()),
                                   marker_color=BAR, text=list(buckets.values()),
                                   textposition="outside"))
            _chart(fig)
        elif observed["open_changes"]:
            st.caption("No merges retrieved in this window; showing open changes instead.")
            draft_count = observed["draft_changes"] or 0
            ready_count = max(0, observed["open_changes"] - draft_count)
            fig = go.Figure(go.Bar(
                x=["Draft", "Ready for review"], y=[draft_count, ready_count],
                marker_color=[PURPLE_LIGHT, PURPLE],
                text=[draft_count, ready_count], textposition="outside"))
            fig.update_layout(yaxis_title="Retrieved open pull requests")
            _chart(fig)
        else:
            st.info("No merged or open pull request records retrieved in this window.")
    with rcol, st.container(border=True):
        _chart_title("How to read this chart", "Interpretation")
        if has_merges:
            st.write("Merge time is the observed number of days between opening and merging a change. It does not measure developer performance or explain delays.")
        else:
            st.write("Draft PRs are still being prepared. Ready-for-review PRs can be reviewed, but neither state proves a blocker or deadline breach.")
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
    period = st.selectbox("Observation period", [30, 90],
                          format_func=lambda d: f"Last {d} days", key="v3_ci_period")
    info = checks_in_period(r["ci_rows"], days=period)
    _kpis([
        (f"Completed checks · {period}d", _number(info["total"]),
         "Retrieved GitHub Actions runs", "▣"),
        ("Succeeded", _number(info["success"]), "Known results only", "✓"),
        ("Failed / timed out", _number(info["failure"]), "Known results only", "×"),
        ("Success share", _percent(info["success_percent"]),
         f'{info["known"]} known results · {period}d', "%"),
    ])
    st.caption(
        f'{info["unknown"]} completed runs with unknown conclusions are excluded '
        "from the success share and plotted outcomes. "
        "A successful check does not prove software quality."
    )
    left, right = st.columns([1.12, .88], gap="large")
    with left, st.container(border=True):
        _chart_title(f"Daily check outcomes · {period} days",
                     "Completed runs with known results; same period as the KPIs.")
        if info["daily"]:
            df = pd.DataFrame(info["daily"]).groupby(
                ["Day", "Outcome"], as_index=False)["Runs"].sum()
            fig = px.bar(df, x="Day", y="Runs", color="Outcome", barmode="stack",
                 color_discrete_map={
                     "Success": GREEN, "Failure / timeout": RED,
                     "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD})
            _chart(fig, height=270, legend=True)
        else:
            st.info("No completed workflow runs with known outcomes in this period.")
    with right, st.container(border=True):
        _chart_title(f"Outcome mix · {period} days",
                     f'{info["known"]} known results · same denominator as success share')
        dist = info["counts"]
        if dist:
            colors = [{"Success": GREEN, "Failure / timeout": RED,
                       "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD}[k]
                      for k in dist]
            fig = go.Figure(go.Pie(labels=list(dist), values=list(dist.values()),
                                   hole=.65, marker=dict(colors=colors),
                                   textinfo="percent"))
            _chart(fig, height=270, legend=True)
        else:
            st.info("No results with a known outcome.")
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
    found = _findings(reports, limit=4)
    verified = coverage_counts(reports)
    _kpis([
        ("Evidence-based findings", _number(len(found)), "Backed by verified source records", "◎"),
        ("Projects for review", _number(len({x["scope"] for x in found})),
         "Suggestions, not confirmed defects", "◷"),
        ("Verified issue sources", f'{verified["issues"]}/{len(reports)}' if reports else "—",
         "Coverage is not a quality score", "✓"),
    ])
    if reports:
        _coverage_banner(reports)
    _section("Priorities for a closer look", "Each finding requires sufficient verified evidence from its specific source.")
    _findings_view(found)
    kinds = Counter(x["type"] for x in found)
    if kinds:
        _section("What types of review appear?", "Number of evidence-backed observations by category.")
        titles = {"issue-aging": "Older issues", "merge-duration": "Merge duration",
                  "closure-change": "Closure activity", "ci": "Automated checks"}
        frame = pd.DataFrame([{"Type": titles.get(k, k), "Findings": n}
                              for k, n in kinds.items()])
        fig = px.bar(frame, x="Type", y="Findings", color_discrete_sequence=[PURPLE],
                     text="Findings")
        _chart(fig, height=260)
    with st.expander("Data selection, formulas and limitations"):
        methodology_contents(reports, selection)


# Keep old domain calculations and searchable evidence displays intact.
