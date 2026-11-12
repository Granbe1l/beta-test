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
    """Visual-first lines, with source-specific eligibility and clear caveats."""
    if not reports:
        st.info("No monitored repositories are available.")
        return
    with st.container(border=True):
        heading, period_col, scope_col = st.columns([2.5, 1, 1.7], gap="small")
        with heading:
            st.markdown("**Daily development activity**")
            st.caption("Actual issue and code-change events")
        with period_col:
            days = st.selectbox(
                "Days", [7, 28], format_func=lambda n: f"{n} days",
                key="overview_trend_period",
                help="Both event lines use the same UTC calendar window.",
            )
        with scope_col:
            scope = st.selectbox(
                "Evidence scope",
                ["Verified source windows", "All retrieved events (exploratory)"],
                key="trend_evidence_scope",
                help="Verified: use only projects with the entire selected period collected. Exploratory: include all observed records with missing-data warnings.",
            )
        exploratory = scope.startswith("All retrieved")
        if exploratory:
            st.markdown(
                '<div class="d-trend-caveat"><strong>Exploratory sample.</strong> '
                'Older events can be missing; apparent increases or zero counts '
                'are not verified changes in real activity.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption(
                "**Comparable records only:** the chart uses projects with a "
                "verified scan for all selected days. Others are excluded, "
                "not counted as inactive."
            )

        issue_tab, pr_tab = st.tabs([
            "Issues · tasks & reports", "Pull requests · code changes",
        ])
        collected = {}
        any_usable = False
        for tab, source, first, second, topic in (
            (issue_tab, "issues", "Issues opened", "Issues closed", "issues"),
            (pr_tab, "pull_requests", "PRs opened", "PRs merged", "pull requests"),
        ):
            eligible = qualified_reports(reports, source, days)
            displayed = reports if exploratory else eligible
            with tab:
                st.caption(
                    f"**{len(displayed)} of {len(reports)} projects shown** · "
                    f"{len(eligible)} have checked {topic} data for all "
                    f"{days} days. Other projects are excluded from this graph."
                )
                if not displayed:
                    st.info(
                        f"No repositories qualify for the verified {days}-day "
                        f"{topic} view. Data are missing for the requested period; "
                        "choose 7 days or inspect all retrieved records (with a warning)."
                    )
                    if st.button(
                        "Show observed sample instead",
                        key=f"trend_switch_{source}",
                        on_click=lambda: st.session_state.update(
                            trend_evidence_scope="All retrieved events (exploratory)"
                        ),
                    ):
                        pass
                    collected[source] = pd.DataFrame(daily_event_series([], days))
                    continue
                any_usable = True
                data = pd.DataFrame(daily_event_series(displayed, days=days))
                collected[source] = data
                totals = observed_event_totals(data.to_dict("records"))
                if totals[first] + totals[second] == 0:
                    st.info(
                        f"No {topic} events appear in the retrieved {days}-day "
                        "records. This does not prove that the projects were inactive."
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
                    xaxis=dict(type="date", nticks=7 if days == 28 else 8,
                               tickformat="%d %b"),
                    yaxis=dict(title="Recorded events / day", rangemode="tozero"),
                )
                _draw_plot(fig, height=272)
                if topic == "issues":
                    st.caption(
                        f"**Reading:** {totals[first]:,} issues opened and "
                        f"{totals[second]:,} closed in recorded events over "
                        f"{days} days. This is not proof of total backlog change."
                    )
                else:
                    st.caption(
                        f"**Reading:** {totals[first]:,} PRs opened and "
                        f"{totals[second]:,} merged in recorded events over "
                        f"{days} days. Not all PRs are expected to merge immediately."
                    )

        with st.expander("Source confidence · limitations"):
            source_counts = coverage_counts(reports)
            ready = analysis_window_coverage(reports, days=days)
            st.caption(
                f"**Complete bounded scans:** Issues {source_counts['issues']}/{len(reports)}, "
                f"PRs {source_counts['pull_requests']}/{len(reports)}. "
                f"**Full {days}-day window verified:** Issues {ready['issues']}/{len(reports)}, "
                f"PRs {ready['pull_requests']}/{len(reports)}. "
                "Only a bounded collection is available; it does not imply complete GitHub history."
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
            mime="text/csv", key="trend_csv", disabled=not any_usable,
            help="CSV includes the displayed source scope and repository denominators.",
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
