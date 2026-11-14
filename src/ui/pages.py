"""Six evidence-first Streamlit screens following the purple operational UI reference.

No synthetic production data, no quality rankings, no client-side JavaScript.
Cross-repository comparisons live within Project details, methodology under Risks.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.findings import findings_for_repo, portfolio_findings
from src.analytics.metrics import calculate_issues, calculate_prs, comparable_metrics, utc
from src.ui.charts import category_counts, observed_age_bands, observed_merge_times, source_coverage_counts
from src.ui.filters import issue_age_days, filter_work_items, filter_pull_requests, filter_workflow_runs, page_slice
from src.ui.theme import (
    INK, PURPLE, PURPLE_DARK, LAVENDER,
    page_header, stat, section, finding, empty_state, esc,
)

PALETTE = [PURPLE, "#AE8CF2", "#DED0FC", "#8B6FC8"]
PER_PAGE = 10


def fmt_num(value):
    return "Not Available" if value is None else f"{value:,}"


def fmt_pct(value):
    return "Insufficient Data" if value is None else f"{value:.0f}%"


def fmt_days(value):
    return "Insufficient Data" if value is None else f"{value:.1f} days"


def fmt_short(value):
    return "—" if value is None else f"{value:,}"


def at_time(value):
    return utc(value).strftime("%d %b %Y · %H:%M UTC") if value else "Not available"


def status_for(reports):
    if not reports:
        return "unavailable"
    if all(r["coverage_ok"] for r in reports):
        return "complete"
    values = [value for report in reports for value in report["status"].values()]
    if "failed" in values:
        return "failed"
    if "stale" in values:
        return "stale"
    return "partial"


def source_available(report, source):
    return report["status"].get(source) == "complete"


def chart_style(fig, height=290, showlegend=False):
    fig.update_layout(
        height=height, margin=dict(l=8, r=14, t=22, b=16),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", color=INK, size=11),
        colorway=PALETTE, showlegend=showlegend,
        legend=dict(orientation="h", y=-.28),
        hoverlabel=dict(bgcolor="white", font_color=INK),
        bargap=.28,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#E9E4F3")
    fig.update_yaxes(gridcolor="#EEEAF5", zeroline=False)
    return fig


def _prepare_repo_picker(state, names, key, default):
    """Respect a user change on the current page and sync when pages change.

    Separate Streamlit widget keys otherwise retain stale per-page selections.
    Remove only the stale widget key before rendering; never reset a choice
    the user is making on the current page.
    """
    choice = state.get("active_repo")
    if choice not in names:
        choice = default
    if state.get("_last_repo_picker") != key or state.get(key) not in names:
        state.pop(key, None)
        index = names.index(choice)
    else:
        index = names.index(state[key])
    state["_last_repo_picker"] = key
    return index


def _remember_repo_picker(key):
    st.session_state["active_repo"] = st.session_state[key]


def select_repo(reports, key="project_choice"):
    """Keep the same active repository through all six navigation pages."""
    if not reports:
        return None
    names = [r["repository"]["full_name"] for r in reports]
    chosen = st.session_state.get("active_repo")
    # Open a repository with usable verified records by default. This is a
    # screenshot/navigation starting point, not a project-quality ranking.
    def evidence_depth(report):
        return (
            sum(v == "complete" for v in report.get("status", {}).values()),
            min(len(report.get("issue_rows", [])), 30)
            + min(len(report.get("pr_rows", [])), 30)
            + min(len(report.get("ci_rows", [])), 30),
        )
    default = max(reports, key=evidence_depth)["repository"]["full_name"]
    index = _prepare_repo_picker(st.session_state, names, key, default)
    selection = st.selectbox(
        "Repository", names, index=index, key=key,
        on_change=_remember_repo_picker, args=(key,),
        help="This project selection is shared between the detailed screens.",
    )
    st.session_state["active_repo"] = selection
    return next(r for r in reports if r["repository"]["full_name"] == selection)


def source_warning(report, source):
    status = report["status"].get(source, "unavailable")
    if status != "complete":
        st.warning(
            f"{source.replace('_', ' ').title()} source: {status}. "
            "Observed rows may be incomplete and affected KPIs are deliberately unavailable."
        )


def card_grid(items, columns=4):
    cols = st.columns(columns)
    for col, item in zip(cols, items):
        with col:
            stat(*item)


def _reset_page_on_results_change(state, rows, key):
    """Keep pagination within matching rows after search/repository changes.

    A stable digest of source record identity/order is a UI-only value.
    It is never used to classify completeness or compute business KPIs.
    """
    from hashlib import blake2b
    digest = blake2b(digest_size=12)
    for index, record in enumerate(rows):
        identity = (record.get("url") or record.get("id")
                    or record.get("number") or record.get("created_at")
                    or index)
        digest.update(str(identity).encode("utf-8"))
        digest.update(bytes((0,)))
    state_key = "_row_set_" + key
    signature = digest.hexdigest()
    if state.get(state_key) != signature:
        state.pop(key, None)
        state[state_key] = signature


def paginate(rows, key, page_size=PER_PAGE):
    count = len(rows)
    if not count:
        return [], 0, 0
    pages = math.ceil(count / page_size)
    _reset_page_on_results_change(st.session_state, rows, key)
    if st.session_state.get(key, 1) > pages:
        st.session_state.pop(key, None)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Showing {count:,} observed matching records · {page_size} per page")
    with col2:
        page = st.number_input("Page", min_value=1, max_value=pages, value=1, key=key)
    start = (page - 1) * page_size
    return page_slice(rows, page, page_size), page, pages


def _display_table_date(value):
    """Format actual timestamps; pandas NaT is truthy but has no strftime."""
    if value is None or pd.isna(value):
        return "—"
    stamp = utc(value)
    return stamp.strftime("%d %b %Y") if stamp is not None and not pd.isna(stamp) else "—"


def table_rows(rows, fields, key):
    """Compact evidence table; URL column is a real GitHub link."""
    view, _, _ = paginate(rows, key)
    if not view:
        return empty_state("No matching records", "Try changing the filters. Empty results are not evidence of an inactive repository.")
    frame = pd.DataFrame(view)
    for name in fields:
        if name not in frame:
            frame[name] = None
    frame = frame[fields]
    for col in ("created_at", "updated_at", "closed_at", "merged_at"):
        if col in frame:
            frame[col] = frame[col].map(_display_table_date)
    column_names = {"number": "#", "title": "Title", "state": "State", "draft": "Draft",
                    "created_at": "Created", "updated_at": "Updated", "closed_at": "Closed",
                    "merged_at": "Merged", "url": "Evidence ↗", "workflow_name": "Workflow",
                    "conclusion": "Result", "branch": "Branch", "event": "Event",
                    "age_days": "Age / lifetime (days)", "labels_text": "Labels"}
    frame = frame.rename(columns=column_names)
    conf = {"Evidence ↗": st.column_config.LinkColumn("Evidence ↗", display_text="GitHub ↗")}
    st.dataframe(frame, hide_index=True, use_container_width=True,
                 height=min(454, 42 + len(view) * 39), column_config=conf)


def sample_restriction():
    st.markdown('<div class="footnote">Metrics describe the collected, timestamp-bounded sample. '
                'Issue age is not a missed deadline, and project activity is not a quality ranking.</div>',
                unsafe_allow_html=True)


def overview(reports, selection):
    page_header("Project Delivery Monitor", "Monitor open-source activity, surface evidence, and identify what deserves a closer look.", status_for(reports))
    if not reports:
        card_grid([
            ("Selected repositories", "0", "Not initialized", "▣"),
            ("Observed open issues", "—", "No verified source", "☷"),
            ("Observed open PRs", "—", "No verified source", "⇄"),
            ("CI completed · 90d", "—", "No verified source", "✓"),
        ])
        section("Executive summary")
        empty_state("Ready for initial data collection", "The PostgreSQL connection and GitHub synchronization must be configured first. Until then, no repository counts, charts or findings will be invented.")
        section("Next steps")
        st.write("Initialize the database, run the audited repository discovery, and synchronize the selected repositories. Deployment and live scheduling remain inactive until verified.")
        return
    names = [r["repository"]["full_name"] for r in reports]
    scope = st.selectbox("Analysis scope", ["All selected repositories"] + names,
                         key="overview_scope", help="Display portfolio-wide verified measures or one repository.")
    chosen = reports if scope == "All selected repositories" else [r for r in reports if r["repository"]["full_name"] == scope]
    fully_current = [r for r in chosen if r["coverage_ok"]]
    good_issues = [r["issues"]["observed_open"] for r in chosen if r["issues"]["observed_open"] is not None]
    good_prs = [r["prs"]["open"] for r in chosen if r["prs"]["open"] is not None]
    good_ci = [r["ci"]["completed"] for r in chosen if r["ci"]["completed"] is not None]
    card_grid([
        ("Selected repositories", fmt_num(len(chosen)), "Curated, not representative", "▣"),
        ("Observed open issues", fmt_short(sum(good_issues)) if good_issues else "—", f"{len(good_issues)} verified sources", "☷"),
        ("Observed open PRs", fmt_short(sum(good_prs)) if good_prs else "—", f"{len(good_prs)} verified sources", "⇄"),
        ("Completed CI runs · 90d", fmt_short(sum(good_ci)) if good_ci else "—", f"{len(good_ci)} verified sources", "✓"),
    ])
    section("Executive summary")
    st.write(f"**{len(fully_current)} of {len(chosen)} repositories** have current, complete source checkpoints across issues, pull requests and CI. "
             "The findings below are created from the available verified records, never from guessed activity.")
    section("Activity at a glance", "Real public GitHub records, explicitly labelled when collection is incomplete.")
    all_issues = [item for r in chosen for item in r["issue_rows"]]
    all_prs = [item for r in chosen for item in r["pr_rows"]]
    c1, c2 = st.columns(2)
    with c1:
        bands = observed_age_bands(all_issues)
        sample_count = sum(bands.values())
        if sample_count:
            st.markdown(f"**Observed open issue ages · n={sample_count:,}**")
            if any(r["status"]["issues"] != "complete" for r in chosen):
                st.caption("⚠️ Partial collection: distribution of retrieved records ONLY; not the entire backlog.")
            fig = px.bar(x=list(bands), y=list(bands.values()), color=list(bands),
                         labels={"x":"Issue age","y":"Observed open issues"},
                         color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False)
            st.plotly_chart(chart_style(fig, 295), use_container_width=True)
        else:
            categories = category_counts(chosen)
            st.markdown("**Sample composition by software category**")
            fig = px.bar(x=list(categories), y=list(categories.values()), color=list(categories),
                         labels={"x":"Project category","y":"Selected repositories"},
                         color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False)
            st.plotly_chart(chart_style(fig, 295), use_container_width=True)
    with c2:
        durations = observed_merge_times(all_prs)
        merges = sum(durations.values())
        if merges:
            st.markdown(f"**Observed merge durations · n={merges:,} · 90d**")
            if any(r["status"]["pull_requests"] != "complete" for r in chosen):
                st.caption("⚠️ Retrieved subset; no project-wide median claimed without complete coverage.")
            fig = px.bar(x=list(durations), y=list(durations.values()), color=list(durations),
                         labels={"x":"Merge duration","y":"Observed PR merges"},
                         color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False)
            st.plotly_chart(chart_style(fig, 295), use_container_width=True)
        else:
            coverage = {k:v for k,v in source_coverage_counts(chosen).items() if v}
            st.markdown("**Data source coverage**")
            fig = px.bar(x=list(coverage), y=list(coverage.values()), color=list(coverage),
                         labels={"x":"Collection status","y":"Repository/source checkpoints"},
                         color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False)
            st.plotly_chart(chart_style(fig, 295), use_container_width=True)
    section("Key findings", "Finding → Evidence → Meaning → Next review")
    verified_reports = [r for r in chosen if r["coverage_ok"]]
    findings = portfolio_findings(verified_reports, 3)
    if findings:
        cols = st.columns(min(3, len(findings)))
        for col, item in zip(cols, findings):
            with col:
                finding(item, "REVIEW CANDIDATE")
    else:
        empty_state("No evidence-backed key findings yet", "A finding appears only after complete, current source collection and sufficient sample size.")
    section("Suggested next reviews")
    if findings:
        for f in findings:
            st.markdown(f"**{esc(f['scope'])}** — {esc(f['review'])}")
    else:
        st.write("First verify source coverage, timestamps and the sample-selection audit.")
    with st.expander("Collection coverage & last update"):
        table = [{"Repository": r["repository"]["full_name"], **r["status"],
                  "Latest complete snapshot": at_time(r["last_success"])} for r in chosen]
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    sample_restriction()


def project_details(reports):
    page_header("Project details", "Repository profile, observation history, and responsible cross-repository comparison.", status_for(reports))
    r = select_repo(reports, "details_repository")
    if not r:
        empty_state("No repository is selected")
        return
    repo = r["repository"]
    st.markdown(f'''<div class="surface"><div class="repo-main">◈ &nbsp;{esc(repo['full_name'])}</div>
    <div class="repo-meta">{esc(repo['category'])} &nbsp; · &nbsp; {esc(repo.get('language') or 'Unspecified language')}
    &nbsp; · &nbsp; GitHub repository ID {esc(repo['id'])}</div></div>''', unsafe_allow_html=True)
    st.link_button("↗ Open repository on GitHub", repo["url"])
    tab_a, tab_b, tab_c = st.tabs(["Project profile", "Compare repositories", "Source coverage"])
    with tab_a:
        section("Repository information")
        card_grid([
            ("Default branch", repo.get("default_branch", "—"), "", "⌘"),
            ("Stars · initial filter", fmt_num(repo.get("stars")), "Not a quality score", "☆"),
            ("Observed issues", fmt_num(r["issues"]["total_observed"]), "May be partial", "☷"),
            ("Observed PRs", fmt_num(r["prs"]["total_observed"]), "May be partial", "⇄"),
        ])
        st.caption(f"Last repository push: {at_time(repo.get('pushed_at'))} · Last verified source update: {at_time(r['last_success'])}")
        section("Observation history", "Snapshots are displayed as collected; a small sample is not a historical performance trend.")
        obs = r.get("observations", [])
        if obs:
            st.dataframe(pd.DataFrame([{
                "Observed at": at_time(o["measured_at"]), "Open issues (observed)": o["open_issues_observed"],
                "Open PRs (observed)": o["open_prs_observed"], "30+ day issues (observed)": o["aged_issues_observed"]
            } for o in obs]), hide_index=True, use_container_width=True)
        else:
            empty_state("No historical observations", "At least one successful and complete issue/PR sync is required to create an observation snapshot.")
    with tab_b:
        comparison(reports, embedded=True)
    with tab_c:
        source_coverage(r)


def source_coverage_rows(r):
    """Keep distinct Issue-event coverage and independent open-backlog status.

    The three event-source statuses live in report["status"], whereas the
    independent full open-Issue inventory has its own status field. Neither
    should be inferred from the other, including when checkpoints are absent.
    """
    rows = []
    for source, checkpoint in (r.get("coverage") or {}).items():
        cp = checkpoint or {}
        status = (r.get("open_backlog_status", "unavailable")
                  if source == "open_backlog"
                  else (r.get("status") or {}).get(source, "unavailable"))
        rows.append({
            "Source": source.replace("_", " ").title(),
            "Status": status,
            "Last success": at_time(cp.get("last_success_at")),
            "Pages fetched": cp.get("pages_fetched"),
            "Records in last sync": cp.get("records_fetched"),
            "Coverage begins": at_time(cp.get("coverage_start")),
        })
    return rows


def source_coverage(r):
    section("Source completeness", "Missing and stale collection is not equivalent to zero activity.")
    rows = source_coverage_rows(r)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    with st.expander("Exact checkpoint metadata"):
        st.json({k: {field: str(v) if isinstance(v, datetime) else v for field,v in (data or {}).items()
                     if field not in ("last_error",)} for k, data in r["coverage"].items()})


def issues_backlog(reports):
    page_header("Issues & backlog", "Inspect the age and recent activity of observed GitHub issues, excluding pull requests.", status_for(reports))
    r = select_repo(reports, "issues_repository")
    if not r:
        empty_state("No repository is selected")
        return
    source_warning(r, "issues")
    dist = r["issues"]["age_distribution"]
    if dist is None and r["issue_rows"]:
        bands = observed_age_bands(r["issue_rows"])
        dist = dict(zip(("0–6d","7–29d","30–89d","90d+"), bands.values()))
        st.caption("⚠️ Only observed records are charted because the issues source is incomplete or stale.")
    labels = ["0–6 days", "7–29 days", "30–89 days", "90+ days"]
    keys = ["0–6d", "7–29d", "30–89d", "90d+"]
    card_grid([(label, fmt_short(dist.get(key)) if dist is not None else "—", "Observed open issues", "○")
               for label, key in zip(labels, keys)])
    section("Open issue aging", "The ages below are descriptive, not a measure of overdue work.")
    if dist is not None:
        fig = px.bar(x=labels, y=[dist[k] for k in keys], labels={"x": "Age band", "y": "Observed open issues"},
                     color=labels, color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False)
        st.plotly_chart(chart_style(fig, 260), use_container_width=True)
    else:
        empty_state("Issue aging unavailable", "Source data must be current and complete before the age distribution can be interpreted.")
    section("Issue register", "Search, filter, and open the original GitHub evidence.")
    a,b,c,d = st.columns([2.3,1,1,1])
    with a: search = st.text_input("Search issues", placeholder="Title or issue number", key="issue_search")
    with b: state = st.selectbox("State", ["Open", "Closed", "All"], key="issue_state")
    with c: age = st.selectbox("Age", ["All"] + labels, key="issue_age")
    all_labels = sorted({label for i in r["issue_rows"] for label in i.get("labels", [])})
    with d: label = st.selectbox("Label", ["All"] + all_labels, key="issue_label")
    rows = filter_work_items(r["issue_rows"], search, state, age, label)
    display = [{**v, "age_days": round(issue_age_days(v), 1), "labels_text": ", ".join(v.get("labels", [])[:3])}
               for v in rows]
    table_rows(display, ["number", "title", "age_days", "labels_text", "state", "url"], "issue_page")
    with st.expander("Weekly opened vs closed issues"):
        opened, closed = r["issues"]["weekly_opened"], r["issues"]["weekly_closed"]
        if opened is not None and closed is not None:
            df = pd.DataFrame({"Week": [v["week"] for v in opened], "Opened": [v["count"] for v in opened],
                               "Closed": [v["count"] for v in closed]})
            fig = px.line(df, x="Week", y=["Opened", "Closed"], markers=True,
                          color_discrete_sequence=[PURPLE, "#9E88BD"])
            st.plotly_chart(chart_style(fig, 290, showlegend=True), use_container_width=True)
        else:
            st.info("Comparable time-series coverage unavailable.")
    sample_restriction()


def pull_request_review(reports):
    page_header("Pull request review", "Explore observed PR activity and how long merged changes took to complete.", status_for(reports))
    r = select_repo(reports, "prs_repository")
    if not r:
        empty_state("No repository is selected")
        return
    source_warning(r, "pull_requests")
    p = r["prs"]
    card_grid([
        ("Open PRs", fmt_short(p["open"]), "Includes drafts", "⇄"),
        ("Draft PRs", fmt_short(p["draft_open"]), "Subset of open PRs", "◈"),
        ("Merged · 90d", fmt_short(p["merged_in_period"]), "Coverage required", "✓"),
        ("Median merge time", f"{p['median_merge_days']:.1f}d" if p["median_merge_days"] is not None else "—", "Merged sample ≥5", "◷"),
    ])
    section("Merge duration distribution", "Only PRs actually merged within the observation period are included.")
    buckets = p["merge_distribution"]
    if buckets is None and r["pr_rows"]:
        buckets = observed_merge_times(r["pr_rows"])
        st.caption("⚠️ Observed merged PR subset only; do not infer repository-wide completion times.")
    if buckets:
        fig = px.bar(x=list(buckets), y=list(buckets.values()), labels={"x": "Time to merge", "y": "Merged PRs"},
                     color=list(buckets), color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False)
        st.plotly_chart(chart_style(fig, 250), use_container_width=True)
    else:
        empty_state("Merge-time distribution unavailable", "Requires complete PR coverage for the observation period.")
    section("Pull request register", "The PR list is an observed sample; not necessarily the entire repository backlog.")
    a,b,c,d = st.columns([2,1,1,1])
    with a: search = st.text_input("Search PRs", placeholder="Title or PR number", key="pr_search")
    with b: state = st.selectbox("State", ["All", "Open", "Closed"], key="pr_state")
    with c: draft = st.selectbox("Draft", ["All", "Draft only", "Not draft"], key="pr_draft")
    with d: sort = st.selectbox("Sort", ["Newest", "Oldest", "Longest open"], key="pr_sort")
    filtered = filter_pull_requests(r["pr_rows"], search, state, draft, sort)
    display = [{**v, "age_days": round(issue_age_days(v), 1)} for v in filtered]
    table_rows(display, ["number", "title", "state", "draft", "age_days", "created_at", "merged_at", "url"], "pr_page")
    st.caption("Review approval requirements are not collected consistently. A 'Needs review' quality signal is therefore not calculated.")
    sample_restriction()


def cicd_activity(reports):
    page_header("CI/CD activity", "GitHub Actions workflow outcomes and events in the observed period.", status_for(reports))
    r = select_repo(reports, "ci_repository")
    if not r:
        empty_state("No repository is selected")
        return
    source_warning(r, "workflow_runs")
    ci = r["ci"]
    card_grid([
        ("Completed · 90d", fmt_short(ci["completed"]), "Observed GitHub Actions", "✓"),
        ("Successful", fmt_short(ci["success"]), "Known completed outcomes", "↗"),
        ("Failed / timed out", fmt_short(ci["failure"]), "Completed runs", "×"),
        ("Success share", f"{ci['success_percent']:.0f}%" if ci["success_percent"] is not None else "—",
         "Known conclusions denominator", "◉"),
    ])
    section("Workflow results · recent 28 days", "Daily counts by workflow conclusion, not a software-quality score.")
    if ci["trend_valid"] or r["ci_rows"]:
        if not ci["trend_valid"]:
            st.caption("⚠️ Partial GitHub Actions coverage: timeline shows retrieved runs only.")
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=28)
        daily = Counter()
        for run in r["ci_rows"]:
            created = utc(run.get("created_at")) if run.get("created_at") else None
            if created and since <= created <= now and run.get("status") == "completed":
                category = "Success" if run.get("conclusion") == "success" else (
                    "Failure / timeout" if run.get("conclusion") in ("failure", "timed_out") else "Other outcomes")
                daily[(created.date().isoformat(), category)] += 1
        start = since.date()
        points = [{"Day": (start + timedelta(days=i)).isoformat(), "Result": cat,
                   "Runs": daily[((start + timedelta(days=i)).isoformat(), cat)]}
                  for i in range(29) for cat in ("Success", "Failure / timeout", "Other outcomes")]
        df = pd.DataFrame(points)
        fig = px.bar(df, x="Day", y="Runs", color="Result", barmode="stack",
                     color_discrete_map={"Success": PURPLE, "Failure / timeout": "#D77B90", "Other outcomes": "#CDB8EA"})
        st.plotly_chart(chart_style(fig, 290, showlegend=True), use_container_width=True)
    else:
        empty_state("Workflow timeline unavailable", "A complete, current GitHub Actions collection is required to compare daily outcomes.")
    section("Recent workflow runs")
    a,b,c = st.columns([2,1,1])
    with a: search = st.text_input("Search workflow", placeholder="Workflow name", key="ci_search")
    with b: result = st.selectbox("Outcome", ["All", "success", "failure", "timed_out", "skipped", "cancelled"], key="ci_outcome")
    with c: branch = st.selectbox("Branch", ["All"] + sorted({v["branch"] for v in r["ci_rows"] if v.get("branch")}), key="ci_branch")
    matching = filter_workflow_runs(r["ci_rows"], search, result, branch)
    table_rows(matching, ["workflow_name", "branch", "event", "status", "conclusion", "created_at", "url"], "ci_page")
    st.caption(f"Completed runs with a known conclusion: {fmt_short(ci['known_conclusion_denominator'])}. Skipped: {fmt_short(ci['skipped'])}. Other CI services are outside this dataset.")
    sample_restriction()


def comparison(reports, embedded=False):
    """Evidence-gated comparison with a usable and visibly labelled fallback.

    The previous default 90-day window suppressed nearly every metric for
    sources whose *actual* verified coverage was 28 days. The selected 7/28
    day window now applies to every period metric, and a full-backlog share
    is kept separately gated by an independently exhausted inventory.
    """
    from src.analytics.comparison_views import (
        comparison_rows, metric_options, preferred_metric, metric_disclosure,
        format_merge_days,
    )
    if not embedded:
        page_header("Cross-repository comparison",
                    "Descriptive differences from original GitHub records—not a quality ranking.",
                    status_for(reports))
    if not reports:
        return empty_state("No comparable repositories")
    col1, col2, col3 = st.columns(3)
    with col1:
        days = st.selectbox("Observation window", [7, 28, 90], index=1,
                            format_func=lambda n: f"Last {n} days",
                            key="compare_days")
    categories = sorted({r["repository"].get("category") or "Other" for r in reports})
    with col2:
        cat = st.selectbox("Project category", ["All"] + categories,
                           key="compare_category")
    scoped = [r for r in reports if cat == "All"
              or (r["repository"].get("category") or "Other") == cat]
    rows = comparison_rows(scoped, days=days)
    if not rows:
        return empty_state("No repository matches these filters")
    df = pd.DataFrame(rows)
    options = metric_options(days)
    selected_metric_key = "compare_metric"
    previous_scope_key = "_compare_data_scope"
    signature = (days, cat)
    if st.session_state.get(previous_scope_key) != signature:
        st.session_state.pop(selected_metric_key, None)
        st.session_state[previous_scope_key] = signature
    if st.session_state.get(selected_metric_key) not in (None, *options):
        st.session_state.pop(selected_metric_key, None)
    default = preferred_metric(rows, days)
    with col3:
        metric = st.selectbox(
            "Metric", options, index=options.index(default),
            key=selected_metric_key,
            help="Verified period measures need complete source coverage. "
                 "Exploratory totals explicitly describe retrieved records only.")
    st.caption(metric_disclosure(rows, metric, days))
    if cat == "All" and len(categories) > 1:
        st.caption(
            f"Comparing {len(categories)} different project categories. "
            "Raw event counts are not normalized for project size, "
            "team capacity, complexity or workflow conventions. "
            "Filter by category before interpreting differences."
        )
    chart_rows = df.dropna(subset=[metric])
    if len(chart_rows) >= 2:
        ordered = chart_rows.sort_values(metric, ascending=False)
        visible = ordered.head(12).sort_values(metric)
        st.caption(
            f"Showing {len(visible)} of {len(chart_rows)} repositories with "
            "eligible values. The complete data table remains below.")
        fig = px.bar(
            visible, x=metric, y="Repository", orientation="h",
            color_discrete_sequence=[PURPLE],
            hover_data=["Category", "Event coverage", "Full open inventory"],
            text=metric)
        fig.update_traces(textposition="outside", cliponaxis=False)
        if metric.startswith("Median PR merge days"):
            fig.update_traces(text=[format_merge_days(v) for v in visible[metric]])
            st.caption("Human-readable bar labels; numeric axis and CSV values remain in days.")
        st.plotly_chart(
            chart_style(fig, min(590, max(280, len(visible) * 42))),
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False})
    else:
        st.info(
            f"Only {len(chart_rows)} repository/repositories qualify for "
            f"'{metric}'. No comparison is inferred from missing data. "
            "The table below still reports what was retrieved.")
        exploratory = df[[
            "Repository", "Issue records retrieved · exploratory",
            "PR records retrieved · exploratory",
            "CI records retrieved · exploratory",
            "Event coverage",
        ]]
        st.dataframe(exploratory, hide_index=True, use_container_width=True)
    with st.expander("Within-category context · median and spread"):
        from src.analytics.comparable_groups import (
            category_distributions, category_eligibility,
        )
        if "exploratory" in metric.lower():
            st.info(
                "Sampled record counts cannot be used as comparable peer "
                "benchmarks: pagination and source sizes vary."
            )
        else:
            eligibility = category_eligibility(rows, metric, min_group=4)
            st.markdown("**Data eligibility by category**")
            st.caption(
                "N qualifying / N tracked for the selected metric and period. "
                "Missing, incomplete and ineligible values stay unknown—not "
                "zero. A within-category median is shown only at n≥4."
            )
            st.dataframe(pd.DataFrame(eligibility), hide_index=True,
                         use_container_width=True)
            peers = category_distributions(rows, metric, min_group=4)
            if peers:
                st.caption(
                    "Verified eligible values only. Each category requires "
                    "at least four eligible repositories; median and middle "
                    "50% (25th–75th percentiles) describe this curated "
                    "non-random sample, not project quality or a GitHub-wide norm."
                )
                st.dataframe(pd.DataFrame(peers), hide_index=True,
                             use_container_width=True)
            else:
                st.info(
                    "No category has four eligible repositories for this "
                    "metric and period. Missing sources are not zeros."
                )
    with st.expander("All repositories · verification and original values"):
        st.dataframe(df, hide_index=True, use_container_width=True)
    st.caption("Source counts are observed, not proof of project performance. "
               "Only original GitHub records and verified scan windows "
               "are used; a blank value never means confirmed zero activity.")


def methodology_contents(reports, selection):
    section("How repositories were selected")
    if selection:
        st.write(f"GitHub Search API candidates: **{selection['candidates']}** · selected: **{selection['selected']}** · search status: **{selection['status']}**.")
        st.write("Public, not forked or archived, ≥50 stars as an initial filter, pushed within 30 days at selection, with observed issues and PRs. The same cohort is retained for honest trends; quiet projects are shown, not silently deleted. "
                 "Selection balances ecosystems and sizes; it does not represent GitHub as a whole.")
        decisions = selection.get("decisions", [])
        if decisions:
            frame = pd.DataFrame(decisions)
            st.dataframe(frame[["full_name", "category", "stars", "decision", "reason", "url"]],
                         hide_index=True, use_container_width=True,
                         column_config={"url": st.column_config.LinkColumn("GitHub evidence")})
    else:
        st.info("No discovery audit has run yet.")
    section("Metric definitions & limitations")
    st.markdown("""
- **Issue aging share:** observed open issues created 30+ days ago ÷ all observed open issues × 100. Cross-project percentages require at least five issues.
- **Open PRs:** includes draft PRs. Merged PRs are a separate, period-based measure.
- **Median merge duration:** median(merged_at − created_at) only for PRs merged in the selected observation period, with at least five merges.
- **Issue closure change:** comparison of equal 28-day closure windows; hidden if the previous denominator is zero or collection is incomplete.
- **CI success share:** completed successful runs ÷ completed runs with known conclusions × 100, including skipped runs in the denominator.
- **Review approval compliance:** **Not Available** because full review policies and approvals are not uniformly collected.
- **Scope:** bounded updated-at sampling can omit old unchanged issues; Actions only covers GitHub Actions, not external CI.
- **Interpretation:** age is not lateness, CI is not overall quality, and cross-repository counts are not quality rankings.
""")
    section("Source health")
    if reports:
        frame = pd.DataFrame([{"Repository": r["repository"]["full_name"], **r["status"],
                              "Last complete update": at_time(r["last_success"])} for r in reports])
        st.dataframe(frame, hide_index=True, use_container_width=True)
    else:
        st.info("No synchronization checkpoints are available.")
    st.caption("Scheduled GitHub Actions can be delayed or disabled; database configuration and genuine successful runs must be verified before claiming a live refresh.")


def risks_recommendations(reports, selection):
    page_header("Risks & recommendations", "Evidence-based review candidates, with their limits and suggested next actions.", status_for(reports))
    valid = [r for r in reports if r["coverage_ok"]]
    findings = portfolio_findings(valid, max_findings=5)
    distinct = len(set(f["scope"] for f in findings))
    card_grid([
        ("Evidence-backed findings", fmt_num(len(findings)) if reports else "—", "Rule-based, not AI-generated", "◎"),
        ("Repositories flagged", fmt_num(distinct) if reports else "—", "For follow-up review", "△"),
        ("Current source coverage", f"{len(valid)}/{len(reports)}" if reports else "—", "Across all 3 sources", "✓"),
        ("Other repositories", fmt_num(len(reports) - distinct) if reports else "—", "Not a clean bill of health", "ⓘ"),
    ])
    section("Top findings", "These are review prompts—not verified defects, missed deadlines, or automated risk scores.")
    tab_a, tab_b = st.tabs(["Priority reviews", "Methodology & limitations"])
    with tab_a:
        if not findings:
            empty_state("No defensible findings yet", "Review prompts require complete, current source data and meaningful denominators. Zero findings never means zero risk.")
        for f in findings:
            tag = {"issue-aging": "BACKLOG REVIEW", "merge-duration": "MERGE-TIME REVIEW",
                   "closure-change": "ACTIVITY CHANGE", "ci": "CI FOLLOW-UP"}.get(f["type"], "REVIEW")
            finding(f, tag)
    with tab_b:
        methodology_contents(reports, selection)


# Backward-compatible interfaces used by earlier local test fixtures.
repository_analysis = project_details
explorer = project_details
methodology = methodology_contents
