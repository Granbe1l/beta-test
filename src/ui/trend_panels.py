"""Evidence-first daily line charts, coverage details and two-repo comparison.

The visualized activity is from timestamps in retrieved GitHub rows; no fake
release dates, productivity scores or interpolated missing GitHub records.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics.trends import daily_event_series, observed_event_totals
from src.ui.observed import coverage_counts, analysis_window_coverage, qualified_reports, summary

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
    """Visualize only real GitHub records, with an explicit verification scope.

    A verified window excludes any repo whose scan covers fewer days than the
    chosen period. Exploratory mode keeps the incomplete-sample line visible
    but never permits claims of total project activity or true growth.
    """
    if not reports:
        st.info("No monitored repositories are available.")
        return
    with st.container(border=True):
        head, period_col = st.columns([3, 1], gap="small")
        with head:
            st.markdown("**Daily development activity**")
            st.caption("Issue and pull-request events from actual GitHub records.")
        with period_col:
            days = st.selectbox("Period", [7, 28],
                                format_func=lambda n: f"Last {n} days",
                                key="overview_trend_period")

        scope = st.radio(
            "Evidence scope",
            ["All retrieved events (exploratory)", "Verified source windows"],
            horizontal=True, key="trend_evidence_scope",
            help="Verified uses only repos with completed scans covering this full window.",
        )
        exploratory = scope.startswith("All retrieved")
        if exploratory:
            st.warning(
                "Exploratory view: older or busy GitHub activity may be missing "
                "from the collected records. Apparent increases and zeros are "
                "not verified trends or evidence of inactivity."
            )

        issue_tab, pr_tab = st.tabs([
            "Issues · tasks & reports", "Pull requests · code changes",
        ])
        collected = {}
        for tab, source, first, second, topic in (
            (issue_tab, "issues", "Issues opened", "Issues closed", "issues"),
            (pr_tab, "pull_requests", "PRs opened", "PRs merged", "pull requests"),
        ):
            eligible = qualified_reports(reports, source, days)
            displayed = reports if exploratory else eligible
            with tab:
                if not exploratory:
                    st.caption(
                        f"Verified {days}-day bounded windows: "
                        f"**{len(eligible)}/{len(reports)} repositories** "
                        f"for {topic}. The other repositories are excluded."
                    )
                else:
                    st.caption(
                        f"**{len(reports)} repositories** in the exploratory sample; "
                        f"only **{len(eligible)}** have a verified full "
                        f"{days}-day scan for {topic}."
                    )
                if not displayed:
                    st.info(
                        f"No repository has a verified {days}-day {topic} "
                        "window yet. Choose 7 days or exploratory mode to inspect "
                        "the bounded records without a completeness claim."
                    )
                    collected[source] = pd.DataFrame(daily_event_series([], days))
                    continue
                data = pd.DataFrame(daily_event_series(displayed, days=days))
                collected[source] = data
                totals = observed_event_totals(data.to_dict("records"))
                if totals[first] + totals[second] == 0:
                    st.info(
                        f"No {topic} events were found in the retrieved data. "
                        "This does not establish that development stopped."
                    )
                    continue
                fig = go.Figure()
                for field, color in ((first, PURPLE), (second, GREEN)):
                    fig.add_trace(go.Scatter(
                        x=data["Date"], y=data[field], name=field,
                        mode="lines+markers",
                        line=dict(color=color, width=2.5),
                        marker=dict(size=5, color=color),
                        hovertemplate=(
                            "%{x}<br>%{y:,} recorded events"
                            "<extra>%{fullData.name}</extra>"
                        ),
                    ))
                fig.update_layout(
                    xaxis=dict(type="date", nticks=7 if days == 28 else 8),
                    yaxis=dict(title="Recorded daily events", rangemode="tozero"),
                )
                _draw_plot(fig)
                if topic == "issues":
                    st.caption(
                        f"**Reading:** {totals[first]:,} issues opened and "
                        f"{totals[second]:,} closed in selected records over "
                        f"{days} days. This does not prove a change in total backlog."
                    )
                else:
                    st.caption(
                        f"**Reading:** {totals[first]:,} PRs opened and "
                        f"{totals[second]:,} merged in selected records over "
                        f"{days} days. Not every PR is expected to merge immediately."
                    )

        source_counts = coverage_counts(reports)
        ready = analysis_window_coverage(reports, days=days)
        st.caption(
            f"**Cohort checks:** Issues {source_counts['issues']}/{len(reports)} "
            f"bounded scans complete, {ready['issues']}/{len(reports)} "
            f"cover {days} days. PRs {source_counts['pull_requests']}/{len(reports)} "
            f"complete, {ready['pull_requests']}/{len(reports)} "
            f"cover {days} days. Only a bounded collection is available; these scans do not imply complete GitHub history."
        )
        issue_data = collected["issues"][["Date", "Issues opened", "Issues closed"]]
        pr_data = collected["pull_requests"][["Date", "PRs opened", "PRs merged"]]
        export = issue_data.merge(pr_data, on="Date", how="outer")
        export["Issue eligible repositories"] = (
            len(reports) if exploratory else len(qualified_reports(reports, "issues", days))
        )
        export["PR eligible repositories"] = (
            len(reports) if exploratory else len(qualified_reports(reports, "pull_requests", days))
        )
        export["Scope"] = "exploratory" if exploratory else "verified_source_windows"
        st.download_button(
            "Export displayed events (CSV)",
            data=export.to_csv(index=False).encode("utf-8"),
            file_name=f"github_{export['Scope'].iloc[0]}_{days}d.csv",
            mime="text/csv", key="trend_csv",
        )


def coverage_progress(reports):
    """Show the exact source denominator without claiming complete Git history."""
    complete = coverage_counts(reports)
    ready = analysis_window_coverage(reports, days=28)
    n = len(reports)
    with st.expander("Data coverage · what was actually collected"):
        st.caption("A completed source scan may cover only one or seven days after an adaptive retry. "
                   "The second number below shows repositories with a complete 28-day window.")
        for source, label in (
            ("issues", "Tasks and reported issues"),
            ("pull_requests", "Code changes (pull requests)"),
            ("workflow_runs", "Automated checks (CI/CD)"),
        ):
            v = complete[source]
            st.progress(v / n if n else 0,
                        text=f"{label}: {v}/{n} scan complete · "
                             f"{ready[source]}/{n} have 28-day verified coverage")
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
