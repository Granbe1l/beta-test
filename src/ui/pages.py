"""Five compact dashboard views; data is always sourced from persisted records."""
from __future__ import annotations
from datetime import datetime, timezone
from src.analytics.metrics import calculate_issues, calculate_prs, calculate_ci
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.analytics.findings import findings_for_repo, portfolio_findings
from src.analytics.metrics import comparable_metrics
from src.ui.theme import hero, stat, insight, empty_state

NAVY = "#16334c"
BLUE = "#418fbb"


def fmt_num(n): return "Not Available" if n is None else f"{n:,}"
def fmt_pct(n): return "Insufficient Data" if n is None else f"{n:.0f}%"
def fmt_days(n): return "Insufficient Data" if n is None else f"{n:.1f} days"
def at_time(value):
    return value.strftime("%d %b %Y, %H:%M UTC") if value else "Not Available"


def chart_style(fig, height=310):
    fig.update_layout(height=height, font=dict(family="sans-serif", color=NAVY, size=12),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=10,r=10,t=30,b=15),showlegend=True,legend=dict(orientation="h",y=-.3))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e4edf3", zeroline=False)
    return fig


def verified(reports):
    return [r for r in reports if r["coverage_ok"]]


def overview(reports, selection):
    hero("Project Delivery Monitor", "Understand observable open-source activity, identify review priorities, and inspect the original evidence.")
    valid = verified(reports)
    all_syncs = [r["last_success"] for r in reports if r["last_success"]]
    updated = min(all_syncs) if reports and len(all_syncs) == len(reports) else None
    a,b,c = st.columns(3)
    with a: stat("Repositories selected", len(reports))
    with b: stat("Fully current repositories", f"{len(valid)} / {len(reports)}")
    with c: stat("Oldest source update", at_time(updated))
    st.subheader("Executive summary")
    if not reports:
        empty_state("No repositories have been selected")
        return
    st.write(f"This curated sample covers **{len(reports)} public repositories**. "
             f"**{len(valid)}** have complete, current source collection across issues, pull requests and GitHub Actions runs. "
             "Observed counts describe the configured collection window, not every historical record or all of GitHub.")
    findings = portfolio_findings(reports)
    st.subheader("Three key findings")
    if findings:
        cols = st.columns(min(len(findings),3))
        for col,item in zip(cols,findings):
            with col: insight(item)
    else:
        empty_state("No defensible findings meet the evidence and sample-size rules")
    st.subheader("Key measures — verified subset")
    a,b,c,d = st.columns(4)
    with a: st.metric("Observed open issues", fmt_num(sum(r["issues"]["observed_open"] for r in reports if r["issues"]["observed_open"] is not None) if any(r["issues"]["observed_open"] is not None for r in reports) else None))
    with b: st.metric("Observed open PRs", fmt_num(sum(r["prs"]["open"] for r in reports if r["prs"]["open"] is not None) if any(r["prs"]["open"] is not None for r in reports) else None))
    with c: st.metric("Completed CI runs · 90d", fmt_num(sum(r["ci"]["completed"] for r in reports if r["ci"]["completed"] is not None) if any(r["ci"]["completed"] is not None for r in reports) else None))
    with d: st.metric("Data coverage", f"{len(valid)}/{len(reports)} current")
    st.subheader("What varies across repositories?")
    comparable = comparable_metrics(reports)
    df = pd.DataFrame(comparable)
    if not df.empty:
        c1,c2 = st.columns(2)
        with c1:
            rows = df.dropna(subset=["30+ day issues (%)"])
            if not rows.empty:
                st.caption("Share of observed open issues aged 30+ days · denominator ≥5")
                fig = px.bar(rows, x="30+ day issues (%)", y="Repository", orientation="h", color_discrete_sequence=[BLUE], hover_data=["Open issue sample (n)"])
                chart_style(fig); fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Insufficient Data for issue aging comparison")
        with c2:
            rows = df.dropna(subset=["Median merge (days)"])
            if not rows.empty:
                st.caption("Median duration of merged PRs · 90 days · sample ≥5")
                fig = px.bar(rows, x="Median merge (days)", y="Repository", orientation="h", color_discrete_sequence=[NAVY], hover_data=["Merged PR sample (n)"])
                chart_style(fig); fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Insufficient Data for merge duration comparison")
    else: st.info("Comparative charts will appear after verified synchronization")
    st.subheader("Suggested next reviews")
    if findings:
        for f in findings: st.write(f"**{f['scope']}:** {f['review']}")
    else: st.write("Verify collection coverage before interpreting project differences.")
    with st.expander("Data completeness and evidence rules"):
        st.write("A metric is suppressed when its source is unavailable, partial, stale, or lacks minimum sample size. Repository selection is curated, not a random or representative sample.")
        st.dataframe(pd.DataFrame([{"Repository":r["repository"]["full_name"],**r["status"]} for r in reports]), hide_index=True, use_container_width=True)


def explorer(reports):
    hero("Repository Explorer", "Explore the selected sample and open a repository's evidence-focused analysis.")
    if not reports: return empty_state()
    df = pd.DataFrame([{
        "Repository":r["repository"]["full_name"], "Category":r["repository"]["category"],
        "Language":r["repository"]["language"], "Stars (selection filter)":r["repository"]["stars"],
        "Issues observed":r["issues"]["total_observed"], "PRs observed":r["prs"]["total_observed"],
        "Status":"Complete" if r["coverage_ok"] else "Incomplete / stale", "Evidence":r["repository"]["url"]
    } for r in reports])
    a,b,c = st.columns([2,1,1])
    with a: search = st.text_input("Search repository", placeholder="Owner or project")
    with b: lang = st.selectbox("Language", ["All"] + sorted(df["Language"].dropna().unique().tolist()))
    with c: category = st.selectbox("Category", ["All"] + sorted(df["Category"].dropna().unique().tolist()))
    if search: df = df[df["Repository"].str.contains(search,case=False,regex=False)]
    if lang != "All": df=df[df["Language"] == lang]
    if category != "All": df=df[df["Category"] == category]
    sort = st.selectbox("Sort by", ["Repository", "Issues observed", "PRs observed", "Stars (selection filter)"])
    df = df.sort_values(sort, ascending=sort=="Repository")
    st.caption(f"{len(df)} repositories · observed records are bounded samples")
    st.dataframe(df,hide_index=True,use_container_width=True,height=min(560,100+len(df)*37),
                 column_config={"Evidence":st.column_config.LinkColumn("GitHub source")})
    st.caption("Select a repository under Repository Analysis for charts, details, and source links.")


def detail_table(rows, name, page_key):
    st.markdown(f"**{name} — source evidence**")
    if not rows: return st.info("No records collected for this source")
    max_page = max(1,math.ceil(len(rows)/20))
    page = st.number_input("Page",min_value=1,max_value=max_page,value=1,key=page_key)
    fields = [k for k in ("number","title","state","draft","created_at","closed_at","merged_at","url") if k in rows[0]]
    frame = pd.DataFrame(rows[(page-1)*20:page*20])[fields]
    st.dataframe(frame, hide_index=True, use_container_width=True, column_config={"url":st.column_config.LinkColumn("GitHub evidence")})
    st.caption(f"Page {page}/{max_page} · {len(rows)} observed records")


def repository_analysis(reports):
    hero("Repository Analysis", "Look beyond the headline with issue aging, merge timing, and GitHub Actions activity.")
    if not reports: return empty_state()
    name = st.selectbox("Repository", [r["repository"]["full_name"] for r in reports])
    r = next(r for r in reports if r["repository"]["full_name"]==name)
    st.link_button("Open repository on GitHub",r["repository"]["url"])
    if not r["coverage_ok"]:
        st.warning("One or more sources are partial, stale, failed, or unavailable. Unverified KPIs are suppressed rather than shown as zero.")
    a,b,c,d=st.columns(4)
    with a: st.metric("Observed open issues",fmt_num(r["issues"]["observed_open"]))
    with b: st.metric("Issues 30+ days",fmt_pct(r["issues"]["aged_percent"]))
    with c: st.metric("Open PRs (draft included)",fmt_num(r["prs"]["open"]))
    with d: st.metric("Median merge duration · 90d",fmt_days(r["prs"]["median_merge_days"]))
    t1,t2 = st.tabs(["Work items", "CI/CD & evidence"])
    with t1:
        a,b=st.columns(2)
        with a:
            dist=r["issues"]["age_distribution"]
            if dist:
                st.markdown("**Open issue age bands**")
                fig=px.bar(x=list(dist),y=list(dist.values()),labels={"x":"Age","y":"Observed issues"},color_discrete_sequence=[BLUE])
                st.plotly_chart(chart_style(fig),use_container_width=True)
            else: st.info("Issue age distribution unavailable")
        with b:
            buckets=r["prs"]["merge_distribution"]
            if buckets:
                st.markdown("**Merge duration of PRs merged in past 90 days**")
                fig=px.bar(x=list(buckets),y=list(buckets.values()),labels={"x":"Duration","y":"Merged PRs"},color_discrete_sequence=[NAVY])
                st.plotly_chart(chart_style(fig),use_container_width=True)
            else: st.info("Merge-time distribution unavailable")
        opened,closed=r["issues"]["weekly_opened"],r["issues"]["weekly_closed"]
        if opened and closed:
            st.markdown("**Issues opened vs closed each week · recent 90 days**")
            df=pd.DataFrame({"week":[v["week"] for v in opened],"Opened":[v["count"] for v in opened],"Closed":[v["count"] for v in closed]})
            fig=px.line(df,x="week",y=["Opened","Closed"],markers=True,color_discrete_sequence=[BLUE,NAVY])
            st.plotly_chart(chart_style(fig),use_container_width=True)
        else: st.info("Comparable time-series data unavailable; historical snapshots are not treated as a trend")
        st.subheader("Repository findings")
        findings=findings_for_repo(r)
        if findings:
            for f in findings: insight(f)
        else: st.info("No qualifying quantitative finding for the current sample")
    with t2:
        a,b,c,d=st.columns(4)
        with a: st.metric("Completed CI runs",fmt_num(r["ci"]["completed"]))
        with b: st.metric("Successful",fmt_num(r["ci"]["success"]))
        with c: st.metric("Failed / timed out",fmt_num(r["ci"]["failure"]))
        with d: st.metric("Success share",fmt_pct(r["ci"]["success_percent"]))
        st.caption("Success denominator: completed workflow runs with a known conclusion in the past 90 days. Skipped runs remain in the denominator.")
        st.write(f"Skipped runs: {fmt_num(r['ci']['skipped'])} · Review compliance: Not Available (approval reviews not fully collected)")
        detail_table(r["ci_rows"],"Workflow runs", "ci_page")
    with st.expander("Issues — paged source records"):
        detail_table(r["issue_rows"],"Issues", "issues_page")
    with st.expander("Pull requests — paged source records"):
        detail_table(r["pr_rows"],"Pull requests", "pr_page")
    with st.expander("Source checkpoints"):
        st.json({k: {"status":v.get("status"),"last_success_at":str(v.get("last_success_at")),"coverage_start":str(v.get("coverage_start")),"pages_fetched":v.get("pages_fetched")} if v else None for k,v in r["coverage"].items()})


def comparison(reports):
    hero("Cross-Repository Comparison", "Compare observable project activity without assigning a project-quality ranking.")
    if not reports: return empty_state()
    days=st.selectbox("Observation period (days)",[30,60,90],index=2)
    now=datetime.now(timezone.utc)
    recomputed=[]
    for r in reports:
        x=dict(r)
        x["issues"]=calculate_issues(r["issue_rows"],now,days,r["status"]["issues"]=="complete",(r["coverage"]["issues"] or {}).get("coverage_start"))
        x["prs"]=calculate_prs(r["pr_rows"],now,days,r["status"]["pull_requests"]=="complete",(r["coverage"]["pull_requests"] or {}).get("coverage_start"))
        x["ci"]=calculate_ci(r["ci_rows"],now,days,r["status"]["workflow_runs"]=="complete",(r["coverage"]["workflow_runs"] or {}).get("coverage_start"))
        recomputed.append(x)
    st.caption(f"Recent {days} days · low-sample measures are hidden · only complete sources contribute")
    df=pd.DataFrame(comparable_metrics(recomputed))
    cats=["All"]+sorted(df["Category"].dropna().unique().tolist())
    category=st.selectbox("Category filter",cats)
    if category!="All": df=df[df["Category"]==category]
    metric=st.selectbox("Compare metric",["30+ day issues (%)","Median merge (days)","Closed issues (28d)"])
    ready=df.dropna(subset=[metric])
    if len(ready):
        st.caption("Bars indicate measured differences, not quality or timeliness judgments")
        fig=px.bar(ready,x=metric,y="Repository",orientation="h",hover_data=["Open issue sample (n)","Merged PR sample (n)","Coverage"],color_discrete_sequence=[BLUE])
        fig.update_layout(showlegend=False)
        st.plotly_chart(chart_style(fig,max(330,len(ready)*38)),use_container_width=True)
    else: st.info("Insufficient Data with current scope and sample-size checks")
    st.dataframe(df,hide_index=True,use_container_width=True,height=min(580,120+len(df)*37))
    st.caption("Comparisons can be affected by repository size, project governance, issue usage, PR complexity, and endpoint coverage.")


def methodology(reports,selection):
    hero("Findings & Methodology", "Know exactly which evidence supports each statement—and where the analysis stops.")
    findings=portfolio_findings(reports,max_findings=5)
    st.subheader("Evidence-backed findings")
    if findings:
        for f in findings: insight(f)
    else: empty_state("No evidence-backed findings available")
    st.subheader("Sample selection")
    if selection:
        st.write(f"GitHub Search API candidates: **{selection['candidates']}** · selected: **{selection['selected']}** · selection status: **{selection['status']}**.")
        st.write("Public, not archived/forked, 50+ stars as a preliminary filter, pushed in the preceding 90 days, with observed standalone issues and PRs. Category/size round-robin prevents top-stars-only selection.")
        with st.expander("Selection decisions and rejection reasons"):
            st.dataframe(pd.DataFrame(selection["decisions"])[["full_name","category","stars","decision","reason","url"]],hide_index=True,use_container_width=True,column_config={"url":st.column_config.LinkColumn()})
    else: st.warning("No selection audit record found")
    st.subheader("Metric definitions")
    st.markdown('''
- **Observed open issues:** open issues retrieved from the configured updated-at collection window, excluding pull requests. Not the entire historical backlog.
- **30+ day issue share:** observed open issues aged at least 30 days ÷ all observed open issues × 100. Cross-repository share needs ≥5 observed open issues.
- **Median PR merge time:** median(merged_at − created_at) of PRs merged within the observation period; requires ≥5 merged PRs and complete source coverage.
- **Draft PRs:** included in open PR counts, not added to open PRs again.
- **Opened/closed per week:** creation and closure events within the period, only when collection covers that period.
- **Issue closure change:** (last 28d closures − previous 28d closures) ÷ previous 28d closures × 100; suppressed when prior = 0.
- **CI success share:** completed runs with conclusion `success` ÷ completed runs with known conclusions × 100; includes skipped/neutral in denominator. Missing conclusions are excluded and counted separately.
- **Review-compliance share:** **Not Available** until required approval review events and the applicable review policy are comprehensively collected.
''')
    st.subheader("Source health")
    if reports:
        frame=pd.DataFrame([{"Repository":r["repository"]["full_name"],**r["status"],"oldest_success":at_time(r["last_success"])} for r in reports])
        st.dataframe(frame,hide_index=True,use_container_width=True)
    else: st.info("No synchronization checkpoints")
    with st.expander("Limitations and integrity safeguards",expanded=True):
        st.markdown('''
- **Not a census:** at most 20 eligible repositories drawn from bounded search results. Excludes many communities, repository sizes, and activity patterns.
- **Bounded extraction:** page caps and update windows exclude older unchanged records; a source becomes `partial` if the cap is reached. Missing/stale sources are not silently displayed as zero.
- **Actions scope:** only GitHub Actions workflow runs, not every external CI provider.
- **Causality:** issue age is not a missed deadline; merge duration is not PR efficiency; CI success is not product quality. No single metric is a quality ranking.
- **Temporal validity:** metrics based on events use timestamp windows with complete coverage; historical observations are stored but not naively converted into trends.
- **Synchronization:** GitHub Actions schedules can be delayed or disabled due to inactivity; credentials and managed PostgreSQL must be configured externally.
''')
