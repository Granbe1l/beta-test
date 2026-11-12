"""Evidence-first daily line charts, coverage details and two-repo comparison.

The visualized activity is from timestamps in retrieved GitHub rows; no fake
release dates, productivity scores or interpolated missing GitHub records.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics.trends import daily_event_series, observed_event_totals
from src.ui.observed import coverage_counts, summary

PURPLE = "#6941C6"
GREEN = "#198E74"
INK = "#211A35"


def _draw_plot(fig, height=310):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=15, t=8, b=65),
        font=dict(family="Arial, sans-serif", color=INK, size=11),
        legend=dict(orientation="h", y=-.25, x=0, title=None),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor="#E8E5EE")
    fig.update_yaxes(gridcolor="#F0ECF7", zeroline=False)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False})


def trend_panel(reports):
    """Daily 7/28-day lines, two readable tabs, explicit sampling caution."""
    if not reports:
        st.info("No monitored repositories are available.")
        return
    with st.container(border=True):
        head, choose = st.columns([3, 1], gap="small")
        with head:
            st.markdown("**Daily development activity**")
            st.caption("Actual GitHub issue and PR events from the retrieved sample.")
        with choose:
            days = st.selectbox("Period", [28, 7],
                                format_func=lambda n: f"Last {n} days",
                                key="overview_trend_period")
        data = pd.DataFrame(daily_event_series(reports, days=days))
        totals = observed_event_totals(data.to_dict("records"))
        issue_tab, pr_tab = st.tabs(["Issues · tasks & reports",
                                     "Pull requests · code changes"])
        for tab, first, second, topic in (
            (issue_tab, "Issues opened", "Issues closed", "issues"),
            (pr_tab, "PRs opened", "PRs merged", "pull requests"),
        ):
            with tab:
                if not totals[first] + totals[second]:
                    st.info(f"No {topic} events were retrieved in this period. "
                            "This does not establish that the repositories were inactive.")
                    continue
                fig = go.Figure()
                for field, color in ((first, PURPLE), (second, GREEN)):
                    fig.add_trace(go.Scatter(
                        x=data["Date"], y=data[field], name=field,
                        mode="lines+markers",
                        line=dict(color=color, width=2.5),
                        marker=dict(size=5, color=color),
                        hovertemplate="%{x}<br>%{y:,} observed events<extra>%{fullData.name}</extra>",
                    ))
                fig.update_layout(
                    xaxis=dict(type="date", nticks=7 if days == 28 else 8),
                    yaxis=dict(title="Observed daily events", rangemode="tozero"),
                )
                _draw_plot(fig)
                if topic == "issues":
                    st.caption(
                        f"**Reading:** {totals[first]:,} issues opened and "
                        f"{totals[second]:,} closed in collected records over {days} days. "
                        "The difference is NOT proof of a change in the total project backlog.")
                else:
                    st.caption(
                        f"**Reading:** {totals[first]:,} PRs opened and "
                        f"{totals[second]:,} merged in collected records over {days} days. "
                        "A code change may remain open for valid review reasons.")
        source = coverage_counts(reports)
        total = len(reports)
        st.caption(
            f"**Coverage:** Issues {source['issues']}/{total} source scans complete; "
            f"PRs {source['pull_requests']}/{total}. "
            "Past events may be missing in this bounded GitHub collection. "
            "Zeros describe retrieved rows, not absence of real project activity.")
        st.download_button(
            "Export daily event data (CSV)",
            data=data.to_csv(index=False).encode("utf-8"),
            file_name=f"observed_github_activity_{days}d.csv",
            mime="text/csv", key="trend_csv")


def coverage_progress(reports):
    """Show the exact source denominator without claiming complete Git history."""
    complete = coverage_counts(reports)
    n = len(reports)
    with st.expander("Data coverage · what was actually collected"):
        st.caption("A completed bounded scan is not the same as full GitHub history.")
        for source, label in (
            ("issues", "Tasks and reported issues"),
            ("pull_requests", "Code changes (pull requests)"),
            ("workflow_runs", "Automated checks (CI/CD)"),
        ):
            v = complete[source]
            st.progress(v / n if n else 0,
                        text=f"{label}: {v}/{n} source scans complete")
        st.caption("Incomplete collection can omit activity; it must not be treated as zero.")


def compare_two_repositories(reports):
    """Simple side-by-side observed activity, not a developer ranking."""
    if len(reports) < 2:
        st.info("At least two repositories are needed.")
        return
    names = [r["repository"]["full_name"] for r in reports]
    lcol, rcol = st.columns(2)
    with lcol:
        a = st.selectbox("First project", names, key="v4_repo_first")
    with rcol:
        b = st.selectbox("Second project", names, index=1,
                         key="v4_repo_second")
    if a == b:
        st.info("Select two different projects.")
        return
    chosen = [next(r for r in reports if r["repository"]["full_name"] == n)
              for n in (a, b)]
    scores = [summary([r]) for r in chosen]
    measures = (
        ("Open issues (retrieved)", "open_issues"),
        ("Open PRs (retrieved)", "open_changes"),
        ("Merged PRs · 90 days (retrieved)", "merged_changes"),
        ("Completed checks · 90 days (retrieved)", "completed_checks"),
    )
    def display(v):
        return "—" if v is None else f"{v:,}"
    df = pd.DataFrame([{"Measure": label,
                        a: display(scores[0][key]),
                        b: display(scores[1][key])}
                       for label, key in measures])
    st.dataframe(df, hide_index=True, use_container_width=True)
    for col, report in zip((lcol, rcol), chosen):
        with col:
            st.link_button("View original GitHub project", report["repository"]["url"])
    st.caption("These are observed counts, not a comparison of performance. "
               "Project sizes and source completeness can differ.")
