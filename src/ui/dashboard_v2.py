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
from src.ui.charts import observed_age_bands, observed_merge_times, observed_outcomes
from src.ui.filters import (filter_work_items, filter_pull_requests,
                            filter_workflow_runs, issue_age_days)
from src.ui.pages import (status_for, select_repo, table_rows, source_coverage,
                          comparison, methodology_contents, at_time)
from src.ui.theme import esc, empty_state

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


def _section(title, note=""):
    st.markdown(f'<div class="d-section">{esc(title)}</div>' +
                (f'<div class="d-sub">{esc(note)}</div>' if note else ""),
                unsafe_allow_html=True)


def _heading(kicker, title, note, reports):
    status = status_for(reports)
    statuses = {
        "complete": "Sources verified", "partial": "Partial coverage",
        "stale": "Refresh needed", "failed": "Collection issue",
        "unavailable": "Sources unavailable",
    }
    good = "ok" if status == "complete" else ""
    st.markdown(
        f'<div class="d-heading"><div><div class="d-overline">{esc(kicker)}</div>'
        f'<h1>{esc(title)}</h1><p>{esc(note)}</p></div>'
        f'<span class="d-status {good}">● {esc(statuses.get(status, status.title()))}</span>'
        '</div>', unsafe_allow_html=True)


def _kpis(cards):
    """Each card is (label, value, context, glyph)."""
    columns = st.columns(len(cards), gap="small")
    for column, (label, value, context, glyph) in zip(columns, cards):
        with column:
            st.markdown(
                f'<div class="d-kpi"><div class="d-kpi-label"><span>{esc(label)}</span>'
                f'<span class="d-kpi-icon">{esc(glyph)}</span></div>'
                f'<div class="d-kpi-value">{esc(value)}</div>'
                f'<div class="d-kpi-note">{esc(context)}</div></div>',
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
    names = [r["repository"]["full_name"] for r in reports]
    picked = st.selectbox("Repository", ["All tracked repositories"] + names, key=key)
    return reports if picked == "All tracked repositories" else [
        r for r in reports if r["repository"]["full_name"] == picked]


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
    return portfolio_findings([r for r in reports if r.get("coverage_ok")], limit)


def _findings_view(findings):
    names = {
        "issue-aging": "Older issues deserve a closer look",
        "merge-duration": "Check how long changes remain open",
        "closure-change": "Issue closure activity has changed",
        "ci": "Review automated check outcomes",
    }
    if not findings:
        st.info("No confirmed review finding is available. This can mean incomplete data—not necessarily zero problems.")
        return
    for idx, f in enumerate(findings, 1):
        st.markdown(
            f'<div class="d-finding"><span class="d-finding-index">{idx:02d}</span>'
            f'<div class="d-finding-body"><div class="d-finding-scope">{esc(f["scope"])}</div>'
            f'<div class="d-finding-title">{esc(names.get(f["type"], "Review the observed activity"))}</div>'
            f'<div class="d-finding-fact">{esc(f["headline"])}</div>'
            f'<div class="d-finding-next"><strong>Next check:</strong> {esc(f["review"])}</div>'
            '</div></div>', unsafe_allow_html=True)
        if f.get("url"):
            st.link_button("Open GitHub evidence ↗", f["url"])


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
        st.caption("A selected, bounded sample of public GitHub repositories. Issue age is not an overdue deadline; successful builds do not establish code quality. Missing records are not zero activity.")
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


def overview(reports, selection):
    st.markdown(
        '<div class="d-hero"><div><span class="d-eyebrow">OPEN SOURCE · DELIVERY ANALYTICS</span>'
        '<h1>Where does the work stand?</h1>'
        '<p>See what remains open, how changes progress, and which automated checks need attention—all supported by public GitHub records.</p>'
        '</div><div class="d-mark">◈</div></div>',
        unsafe_allow_html=True)
    if not reports:
        _kpis([("Tracked projects", "0", "No data yet", "▣"),
               ("Open issues", "—", "No verified source", "◷"),
               ("Open changes", "—", "No verified source", "⇄"),
               ("Automated checks", "—", "No verified source", "✓")])
        st.info("Load the genuine GitHub snapshot or configure PostgreSQL to display real measurements.")
        return

    chosen = _scope(reports, "v2_scope")
    issues, issue_note = _available_total(chosen, "issues", "issues", "observed_open")
    prs, pr_note = _available_total(chosen, "pull_requests", "prs", "open")
    runs, run_note = _available_total(chosen, "workflow_runs", "ci", "completed")
    _kpis([("Tracked projects", _number(len(chosen)), "Curated public sample", "▣"),
           ("Open issues", issues, issue_note, "◷"),
           ("Open changes", prs, pr_note, "⇄"),
           ("Checks · 90 days", runs, run_note, "✓")])

    _section("01 / Work at a glance", "Visual summaries of retrieved records. Select a repository above to focus the view.")
    left, right = st.columns([1.12, 1], gap="large")
    with left, st.container(border=True):
        _chart_title("How old are the open issues?", _observed_note(chosen, "issues"))
        bands = observed_age_bands([x for r in chosen for x in r["issue_rows"]])
        if sum(bands.values()):
            fig = go.Figure(go.Bar(y=list(bands), x=list(bands.values()),
                orientation="h", marker_color=BAR,
                text=list(bands.values()), textposition="outside",
                hovertemplate="%{y}: %{x} issues<extra></extra>"))
            fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Observed open issues")
            _chart(fig)
        else:
            st.info("No open issue records retrieved. This does not prove the backlog is empty.")
    with right, st.container(border=True):
        _chart_title("Automated check outcomes", "Retrieved GitHub Actions · 30 days")
        outcomes = {k: v for k, v in observed_outcomes(
            [x for r in chosen for x in r["ci_rows"]], days=30).items() if v}
        if outcomes:
            colors = [{"Success": GREEN, "Failure / timeout": RED,
                       "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD}.get(k, PURPLE)
                      for k in outcomes]
            fig = go.Figure(go.Pie(labels=list(outcomes), values=list(outcomes.values()),
                hole=.62, marker=dict(colors=colors), textinfo="percent",
                hovertemplate="%{label}: %{value} runs<extra></extra>"))
            fig.update_layout(annotations=[dict(text=f"{sum(outcomes.values()):,} runs",
                x=.5, y=.5, showarrow=False, font=dict(size=15, color=INK))])
            _chart(fig, legend=True)
            if any(r["status"].get("workflow_runs") != "complete" for r in chosen):
                st.caption("The chart may describe a retrieved subset, not all checks.")
        else:
            st.info("No completed GitHub Actions outcomes retrieved in the last 30 days.")

    _section("02 / Activity over time", "Weekly issue activity in the same 12-week observation window.")
    with st.container(border=True):
        _chart_title("Issues opened vs closed", "A trend is shown only with verified time-window coverage.")
        if all(r["issues"].get("trend_valid") for r in chosen):
            frame = _weekly([x for r in chosen for x in r["issue_rows"]])
            fig = px.line(frame, x="Week", y="Issues", color="Activity", markers=True,
                          color_discrete_map={"Opened": PURPLE, "Closed": GREEN})
            _chart(fig, height=260, legend=True)
        else:
            st.info("The 12-week trend is unavailable until issue coverage is complete for this period.")

    _section("03 / What deserves a closer look?", "Evidence-backed findings with short next steps.")
    _findings_view(_findings(chosen))
    _section("04 / Compare older open issues", "Counts are descriptive—not performance or project-quality rankings.")
    rows = [
        {"Repository": r["repository"]["full_name"], "Open issues aged 30+ days": r["issues"]["aged_open"]}
        for r in chosen if r["status"].get("issues") == "complete"
        and (r["issues"].get("aged_denominator") or 0) >= 5
    ]
    if rows:
        frame = pd.DataFrame(rows).nlargest(8, "Open issues aged 30+ days").sort_values(
            "Open issues aged 30+ days")
        fig = px.bar(frame, x="Open issues aged 30+ days", y="Repository",
                     orientation="h", color_discrete_sequence=[PURPLE])
        _chart(fig, height=max(240, len(rows) * 36))
    else:
        st.caption("Comparable verified issue totals are not available yet.")
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
    _kpis([
        ("Open issues", _number(r["issues"].get("observed_open")), "Verified source only", "◷"),
        ("Open changes", _number(r["prs"].get("open")), "Verified source only", "⇄"),
        ("Checks · 90 days", _number(r["ci"].get("completed")), "Verified history only", "✓"),
        ("Last repository push", utc(repo["pushed_at"]).strftime("%d %b") if repo.get("pushed_at") else "—",
         "GitHub recorded timestamp", "↗"),
    ])
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
            st.info("One genuine observation exists. At least two snapshots are needed for a trend.")
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
    _kpis([
        ("Open issues", _number(info.get("observed_open")), "Verified count", "◷"),
        ("30+ days old", _number(info.get("aged_open")), "Not a missed deadline", "◴"),
        ("Share aged 30+ days", _percent(info.get("aged_percent")), "Of observed open issues", "%"),
    ])
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
        if info.get("trend_valid"):
            fig = px.line(_weekly(r["issue_rows"]), x="Week", y="Issues", color="Activity",
                          markers=True, color_discrete_map={"Opened": PURPLE, "Closed": GREEN})
            _chart(fig, legend=True)
        else:
            st.info("Weekly trend unavailable without complete collection.")
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
    _kpis([
        ("Open changes", _number(info.get("open")), "Includes drafts", "⇄"),
        ("Draft changes", _number(info.get("draft_open")), "Of the open changes", "◈"),
        ("Merged · 90 days", _number(info.get("merged_in_period")), "Verified time window", "✓"),
        ("Median merge time", f'{info["median_merge_days"]:.1f} days'
         if info.get("median_merge_days") is not None else "—", "At least five merges", "◷"),
    ])
    l, rcol = st.columns([1.2, .8], gap="large")
    with l, st.container(border=True):
        _chart_title("Time to finish merged changes", "Creation date → merge date · 90 days")
        buckets = info.get("merge_distribution")
        if buckets is None:
            buckets = observed_merge_times(r["pr_rows"])
            st.caption("Retrieved sample only; a repository-wide measure is not verified.")
        if sum(buckets.values()):
            fig = go.Figure(go.Bar(x=list(buckets), y=list(buckets.values()),
                                   marker_color=BAR, text=list(buckets.values()),
                                   textposition="outside"))
            _chart(fig)
        else:
            st.info("No observed merges to plot in this window.")
    with rcol, st.container(border=True):
        _chart_title("How to read this chart", "Interpretation")
        st.write("Merge time describes how long observed code changes took from opening to completion. It does not measure developer performance or establish the cause of a delay.")
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
             "See the outcomes of completed public GitHub Actions runs.", reports)
    r = select_repo(reports, "v2_ci_repo")
    if not r:
        empty_state("No repository selected")
        return
    info = r["ci"]
    _kpis([
        ("Completed checks", _number(info.get("completed")), "Last 90 days", "▣"),
        ("Successful", _number(info.get("success")), "Known outcomes", "✓"),
        ("Failed or timed out", _number(info.get("failure")), "Known outcomes", "×"),
        ("Success share", _percent(info.get("success_percent")), "Not a code quality score", "%"),
    ])
    left, right = st.columns([1.16, .84], gap="large")
    now = datetime.now(timezone.utc)
    recent = []
    for item in r["ci_rows"]:
        stamp = utc(item.get("created_at"))
        if stamp and now - timedelta(days=30) <= stamp <= now and item.get("status") == "completed":
            conclusion = item.get("conclusion")
            recent.append({
                "Day": stamp.date().isoformat(),
                "Outcome": "Success" if conclusion == "success" else
                           "Failure / timeout" if conclusion in ("failure", "timed_out") else "Other",
                "Runs": 1,
            })
    with left, st.container(border=True):
        _chart_title("Daily automated check outcomes", "Observed completed runs · last 30 days")
        if recent:
            df = pd.DataFrame(recent).groupby(["Day", "Outcome"], as_index=False)["Runs"].sum()
            fig = px.bar(df, x="Day", y="Runs", color="Outcome", barmode="stack",
                color_discrete_map={"Success": GREEN, "Failure / timeout": RED, "Other": PURPLE_LIGHT})
            _chart(fig, legend=True)
            if r["status"].get("workflow_runs") != "complete":
                st.caption("Data coverage may be incomplete.")
        else:
            st.info("No completed run retrieved in the last 30 days.")
    with right, st.container(border=True):
        _chart_title("Check outcomes", "30-day distribution")
        dist = {k: v for k, v in observed_outcomes(r["ci_rows"], days=30).items() if v}
        if dist:
            colors = [{"Success": GREEN, "Failure / timeout": RED,
                       "Skipped": PURPLE_LIGHT, "Other outcomes": GOLD}.get(k, PURPLE)
                      for k in dist]
            fig = go.Figure(go.Pie(labels=list(dist), values=list(dist.values()),
                                   hole=.6, marker=dict(colors=colors), textinfo="percent"))
            _chart(fig, legend=True)
        else:
            st.info("No check outcome distribution available.")
    _section("Inspect individual GitHub Actions runs")
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
    table_rows(rows, ["workflow_name", "branch", "event", "conclusion",
                      "created_at", "url"], "v2_ci_page")
    _coverage_details([r])


def risks_recommendations(reports, selection):
    _heading("ACTIONABLE FINDINGS", "Where should we look next?",
             "Evidence-backed observations with a direct link to the actual records.", reports)
    ready = [r for r in reports if r.get("coverage_ok")]
    found = _findings(reports, limit=6)
    _kpis([
        ("Review points", _number(len(found)), "Supported by verified records", "◎"),
        ("Projects flagged", _number(len({x["scope"] for x in found})),
         "Candidates for manual review", "◷"),
        ("Current coverage", f"{len(ready)}/{len(reports)}" if reports else "—",
         "All three GitHub sources", "✓"),
    ])
    _section("Priorities for a closer look", "These are review suggestions, not confirmed defects or risk scores.")
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
