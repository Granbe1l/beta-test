"""Project-manager entry point for an arbitrary PUBLIC GitHub URL.

Explicitly scoped as a live, bounded preview, never as part of the
75-repository auditable cohort or a certified full-backlog measurement.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics.on_demand import (
    PublicLookupError, inspect_public_repository, parse_public_repo,
)


@st.cache_data(ttl=300, show_spinner=False, max_entries=64)
def _cached_public_preview(repository: str):
    return inspect_public_repository(repository)


def _as_table(items, kind):
    if kind == "Issues":
        return [
            {"#": x.get("number"), "Title": x.get("title"),
             "Status": x.get("state"), "GitHub": x.get("html_url")}
            for x in items
        ]
    if kind == "Pull requests":
        return [
            {"#": x.get("number"), "Title": x.get("title"),
             "Status": "Merged" if x.get("merged_at") else x.get("state"),
             "GitHub": x.get("html_url")}
            for x in items
        ]
    return [
        {"Workflow": x.get("name"), "Status": x.get("status"),
         "Outcome": x.get("conclusion") or "Pending",
         "GitHub": x.get("html_url")}
        for x in items
    ]


def _table(label, items, error):
    st.markdown("**" + label + " · latest observed sample**")
    st.caption("Up to 30 latest API records; not a full 28-day source scan.")
    if error:
        st.warning(label + " could not be read: " + error + ". Do not interpret missing results as zero activity.")
    elif items:
        st.dataframe(
            pd.DataFrame(_as_table(items, label)),
            hide_index=True, use_container_width=True,
            column_config={"GitHub": st.column_config.LinkColumn("Source")},
        )
    else:
        st.info("No records returned in this sampled API response. This is not evidence of a complete empty history.")


def render_public_inspector(reports: list[dict]):
    st.markdown("### Inspect a public GitHub project")
    st.caption(
        "Paste a public repository URL to inspect its latest observable activity. "
        "This preview is separate from the 75 audited projects."
    )
    with st.form("public_repository_inspector_form"):
        entered = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/owner/repository",
            help="Public repository root only. No authentication or private repository access.",
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
        st.info("Provide a public GitHub repository URL to see a bounded live preview.")
        return

    tracked = {r["repository"]["full_name"].casefold(): r for r in reports}
    if repo_name.casefold() in tracked:
        if st.button(
            "Use the existing audited snapshot for this tracked repository",
            key="switch_to_curated_record",
        ):
            st.session_state["active_repo"] = tracked[repo_name.casefold()]["repository"]["full_name"]
            st.session_state["v2_repo_explorer_mode"] = "Tracked dataset"
            st.rerun()
        st.caption(
            "This repository is already in your current selected cohort. "
            "The tracked mode offers its saved 28-day evidence and source audit."
        )

    with st.spinner("Reading bounded public GitHub activity..."):
        try:
            data = _cached_public_preview(repo_name)
        except PublicLookupError as exc:
            st.error(str(exc))
            return

    st.subheader(data["name"])
    if data["description"]:
        st.write(data["description"])
    st.link_button("Open project on GitHub", data["html_url"])
    st.caption(
        "Fetched " + data["observed_at"][:19].replace("T", " ") +
        " UTC · cached up to 5 minutes · public GitHub REST API."
    )
    st.warning(
        "Live exploratory preview: not part of the 75-project Verified cohort. "
        "The latest 30 records per source cannot certify a full 28-day window, "
        "a complete issue backlog, missed deadlines or project quality."
    )

    a, b, c, d = st.columns(4)
    with a:
        st.metric("Open issues observed", data["sample_open_issues"],
                  help="Only open Issues in the most recently updated API page, not the entire backlog.")
    with b:
        st.metric("PRs in sample", len(data["sample_prs"]),
                  help="Up to 30 recently updated PRs, open and closed.")
    with c:
        st.metric("Failed CI runs in sample", data["sample_ci_failed"],
                  help="Failures among up to 30 latest workflow runs.")
    with d:
        st.metric("Last push", (data["pushed_at"] or "Not available")[:10],
                  help="Repository metadata, not a delivery milestone.")

    st.markdown("### What should the project manager inspect?")
    notes = []
    if data["ci_error"]:
        notes.append("CI/CD could not be checked: " + data["ci_error"] + ".")
    elif data["sample_ci_failed"]:
        notes.append(
            str(data["sample_ci_failed"]) + " of " +
            str(data["sample_ci_completed"]) + " sampled completed runs with known "
            "outcomes failed; inspect original workflow logs before inferring impact."
        )
    if data["issues_error"]:
        notes.append("Issue history could not be checked: " + data["issues_error"] + ".")
    elif data["sample_old_issues"]:
        notes.append(
            str(data["sample_old_issues"]) +
            " retrieved open Issues are 30+ days old; ask whether each remains relevant. "
            "Age alone does not establish lateness."
        )
    if not notes:
        notes.append(
            "No review signal met these limited sample rules. This does not prove "
            "that the project has no issues or delivery risks."
        )
    for note in notes:
        st.write("• " + note)
    link_a, link_b = st.columns(2)
    if data["last_failed_run_url"]:
        with link_a:
            st.link_button("Inspect a failed GitHub Actions run", data["last_failed_run_url"])
    if data["old_issue_url"]:
        with link_b:
            st.link_button("Inspect an older open Issue", data["old_issue_url"])
    median_hours = data["sample_merged_median_hours"]
    if median_hours is not None:
        st.caption(
            "Sample median merge time: " + f"{median_hours:.1f}" +
            " hours, among recently updated merged PRs only."
        )

    tabs = st.tabs(["Issues", "Pull requests", "CI/CD runs", "Evidence limits"])
    with tabs[0]:
        _table("Issues", data["sample_issues"], data["issues_error"])
    with tabs[1]:
        _table("Pull requests", data["sample_prs"], data["prs_error"])
    with tabs[2]:
        _table("CI/CD runs", data["sample_runs"], data["ci_error"])
    with tabs[3]:
        st.markdown(
            "This is a **read-only preview**: four bounded unauthenticated REST "
            "calls at most; rate limits may apply. A complete 28-day audit "
            "needs paginated, checkpointed collection and strict timestamp "
            "validation. Private repositories are not supported. GitHub activity "
            "does not reveal a client's milestones, SLA, assignments or delivery acceptance."
        )
        st.caption(
            "Preview records are neither saved to the curated snapshot nor used "
            "in portfolio-wide KPIs. No GitHub token is requested from visitors."
        )
