"""Public GitHub URL inspector, separate from the fixed curated 50-project cohort.

The only write is an expiring, session-facing cache; this module never adds
external repositories to SQL, snapshots, trend comparisons, or Verified KPIs.
"""
from __future__ import annotations

import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics.inspector_presenter import inspection_summary
from src.analytics.inspection_export import inspection_csv
from src.analytics.on_demand import (
    PublicLookupError, inspect_public_repository, parse_public_repo,
)


@st.cache_data(ttl=300, show_spinner=False, max_entries=64)
def _cached_public_preview(repository: str):
    return inspect_public_repository(repository)


def _short(value, limit=110):
    text = str(value or "Untitled")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _as_table(items, kind):
    if kind == "Issues":
        return [
            {"#": x.get("number"), "Title": _short(x.get("title")),
             "Status": x.get("state"), "GitHub": x.get("html_url")}
            for x in items
        ]
    if kind == "Pull requests":
        return [
            {"#": x.get("number"), "Title": _short(x.get("title")),
             "Status": ("Merged" if x.get("merged_at")
                        else "Draft" if x.get("draft") and x.get("state") == "open"
                        else x.get("state")),
             "GitHub": x.get("html_url")}
            for x in items
        ]
    return [
        {"Workflow": _short(x.get("name"), 65),
         "Status": x.get("status"),
         "Outcome": x.get("conclusion") or "Pending",
         "GitHub": x.get("html_url")}
        for x in items
    ]


def _table(label, items, error):
    st.markdown("**" + label + " · latest observed sample**")
    st.caption("Most recent API page only (up to 30 items). Not 28-day coverage.")
    if error:
        st.warning(
            label + " is currently unavailable (" + error +
            "). Missing records are unknown, not zero."
        )
        return
    if not items:
        st.info("No records in the returned sample. This does not prove inactivity.")
        return
    st.dataframe(
        pd.DataFrame(_as_table(items, label)),
        hide_index=True, use_container_width=True, height=300,
        column_config={"GitHub": st.column_config.LinkColumn("Source")},
    )


def _chart(title: str, series: list[dict], *, color: str):
    st.markdown("**" + title + "**")
    if not series:
        st.info("No comparable sample chart is available from this source.")
        return
    labels = [item["label"] for item in series]
    counts = [item["count"] for item in series]
    fig = go.Figure(go.Bar(
        x=counts, y=labels, orientation="h",
        text=counts, textposition="auto",
        marker={"color": color},
        hovertemplate="%{y}: %{x} observed records<extra></extra>",
    ))
    fig.update_layout(
        height=max(220, 66 * len(series) + 68),
        margin=dict(l=10, r=14, t=12, b=22),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(size=12),
        xaxis=dict(title="Observed records", rangemode="tozero",
                   showgrid=True, zeroline=False),
        yaxis=dict(autorange="reversed", title=None),
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})


def _retry_control(repo_name: str):
    """Manual retry with a per-session cooldown; cache is 5 minutes otherwise."""
    last = st.session_state.get("public_inspector_last_retry", 0.0)
    elapsed = time.monotonic() - last
    disabled = elapsed < 60
    if st.button(
        "Refresh this inspection",
        key="refresh_public_inspection",
        disabled=disabled,
        help="For one-time updates; wait at least 60 seconds between retries.",
    ):
        st.session_state["public_inspector_last_retry"] = time.monotonic()
        _cached_public_preview.clear(repo_name)
        st.rerun()
    if disabled:
        st.caption("Manual refresh cooldown is active to reduce unnecessary GitHub API calls.")


def render_public_inspector(reports: list[dict]):
    st.markdown("### Inspect a public GitHub project")
    st.info(
        "**External inspection · separate from the 50-project dataset.** "
        "The dashboard's Verified 50/50 badge applies to the tracked sample, "
        "**not** to the URL entered here. Search results never change its members."
    )
    st.caption(
        "Paste a public GitHub repository link to examine recent Issues, "
        "pull requests (PRs), and automated checks (CI/CD)."
    )

    with st.form("public_repository_inspector_form"):
        entered = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/owner/repository",
            help="The public repository root, not a link to an Issue or file.",
        )
        submitted = st.form_submit_button(
            "Inspect public project", type="primary",
            use_container_width=False,
        )

    if submitted:
        try:
            requested = parse_public_repo(entered)
        except PublicLookupError as exc:
            st.session_state.pop("public_inspector_repo", None)
            st.error(str(exc))
            return
        st.session_state["public_inspector_repo"] = requested

    repo_name = st.session_state.get("public_inspector_repo")
    if not repo_name:
        st.caption(
            "No project selected yet. Enter a GitHub URL to see its latest "
            "publicly observed activity; this is not a complete history."
        )
        return

    tracked = {r["repository"]["full_name"].casefold(): r for r in reports}
    if repo_name.casefold() in tracked:
        st.caption(
            "This repository also exists in the curated dataset. "
            "The inspector below remains a separate, newer but limited preview."
        )
        if st.button(
            "Open this project's saved Verified evidence instead",
            key="switch_to_curated_record",
        ):
            st.session_state["active_repo"] = tracked[
                repo_name.casefold()]["repository"]["full_name"]
            st.session_state["v2_repo_explorer_mode"] = "Tracked dataset"
            st.rerun()

    with st.spinner("Retrieving recent public GitHub evidence..."):
        try:
            data = _cached_public_preview(repo_name)
        except PublicLookupError as exc:
            st.error(str(exc))
            st.caption(
                "If the GitHub API is rate-limited, wait for access to recover "
                "before retrying. The 50-project tracked dataset is unaffected."
            )
            _retry_control(repo_name)
            return

    analysis = inspection_summary(data)
    st.subheader(data["name"])
    if data.get("description"):
        st.caption(data["description"])
    st.link_button("Open original GitHub repository", data["html_url"])
    st.caption(
        "External API observation: " +
        data["observed_at"][:19].replace("T", " ") +
        " UTC · 5-minute cache · not the tracked snapshot timestamp."
    )

    gaps = analysis["source_gaps"]
    if gaps:
        st.warning(
            f"{gaps} source(s) could not be read. A missing API response is "
            "not evidence of zero Issues, PRs, or CI runs."
        )
    else:
        st.caption(
            "All three sample endpoints responded. This does not certify "
            "full 28-day source coverage."
        )

    first, second = st.columns(2, gap="medium")
    with first:
        st.metric(
            "Open Issues · observed sample",
            data["sample_open_issues"] if not data.get("issues_error") else "—",
            help="Open issues among the latest returned records, not total backlog.",
        )
        st.metric(
            "Failed CI runs · observed sample",
            data["sample_ci_failed"] if not data.get("ci_error") else "—",
            help="Failures/timeouts among sampled completed GitHub Actions runs.",
        )
    with second:
        st.metric(
            "PRs · observed sample",
            analysis["pr_observed"] if not data.get("prs_error") else "—",
            help="Up to 30 recently updated PR records, not a 28-day total.",
        )
        st.metric(
            "Last repository push",
            (data.get("pushed_at") or "Unknown")[:10],
            help="GitHub metadata, not evidence of a completed milestone.",
        )

    st.markdown("### What should the project manager inspect?")
    st.caption(
        "Inspection order reflects evidence available from this request; "
        "it is **not** a project-health score or a deadline assessment."
    )
    for index, finding in enumerate(analysis["review_plan"], 1):
        with st.container(border=True):
            st.markdown(
                f"**{index}. {finding['title']}** · {finding['tag']}"
            )
            st.write(finding["explanation"])
            if finding.get("url"):
                st.link_button("Check original GitHub evidence", finding["url"])

    st.markdown("### Sample activity breakdown")
    st.caption(
        "Charts count only returned records, including pending and skipped "
        "checks where present. They do not extrapolate missing history."
    )
    left, right = st.columns(2, gap="large")
    with left:
        _chart(
            f"CI/CD · {analysis['ci_observed']} runs observed",
            analysis["ci"], color="#6940BB",
        )
    with right:
        _chart(
            f"Pull requests · {analysis['pr_observed']} PRs observed",
            analysis["prs"], color="#3B7198",
        )

    tabs = st.tabs(["Issues", "Pull requests", "CI/CD runs", "Evidence limits"])
    with tabs[0]:
        _table("Issues", data["sample_issues"], data["issues_error"])
    with tabs[1]:
        _table("Pull requests", data["sample_prs"], data["prs_error"])
    with tabs[2]:
        _table("CI/CD runs", data["sample_runs"], data["ci_error"])
    with tabs[3]:
        st.markdown("**What do these labels mean?**")
        st.write(
            "**Issue:** task, bug report, or discussion logged in a repository. "
            "**PR (Pull Request):** proposed code change. "
            "**CI/CD:** automated workflow checks, not a delivery acceptance test."
        )
        st.write(analysis["limitations"])
        st.caption(
            "Read-only lookup: at most four bounded unauthenticated GitHub "
            "REST API calls. Results are never stored as new curated projects "
            "or used to change portfolio-wide KPIs. Private repositories are "
            "not supported. GitHub API rate limits may apply."
        )
    st.download_button(
        "Download this inspection (CSV)",
        data=inspection_csv(data, analysis),
        file_name="github-public-inspection-" +
                  repo_name.replace("/", "-").lower() + ".csv",
        mime="text/csv",
        help="Includes sampled data, UTC timestamp, evidence and limitations; "
             "does not add this project to the 50 tracked repositories.",
    )
    _retry_control(repo_name)
