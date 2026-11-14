"""Project Delivery Monitor · visual-first, evidence-based Streamlit app.

Read only: opening a dashboard does not trigger GitHub collection.
The underlying snapshots, collectors and metric formulas are unchanged.
"""
from __future__ import annotations

import os
from datetime import timedelta, timezone
import streamlit as st

from src.config.settings import Settings
from src.database.store import make_engine, session_factory
from src.analytics.read import load_reports, selection_info
from src.analytics.snapshot import read_snapshot, SNAPSHOT_PATH
from src.ui.theme_v2 import apply_theme_v2, brand
from src.ui.observed import coverage_counts, verified_joint_cohort
from src.ui.reader_guide import TERMS, HOW_TO_READ, NAV_HELP
from src.ui.dashboard_v2 import (
    overview, project_details, issues_backlog, pull_request_review,
    cicd_activity, risks_recommendations, status_for,
)

st.set_page_config(
    page_title="Project Delivery Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

try:
    secret_url = st.secrets.get("DATABASE_URL")
    if secret_url:
        os.environ["DATABASE_URL"] = str(secret_url)
except (FileNotFoundError, KeyError, AttributeError):
    pass

settings = Settings.from_env()
apply_theme_v2()


@st.cache_data(ttl=600, show_spinner=False)
def get_data(database_url, observation_days, stale_hours, snapshot_mtime):
    if database_url:
        engine = make_engine(database_url)
        try:
            with session_factory(engine)() as session:
                return (
                    load_reports(session, observation_days=observation_days,
                                 stale_hours=stale_hours),
                    selection_info(session),
                    {"mode": "database", "generated_at": None, "stale": False},
                )
        finally:
            engine.dispose()
    return read_snapshot(SNAPSHOT_PATH, observation_days=observation_days,
                         stale_hours=stale_hours)


MENU = {
    "Dashboard": overview,
    "Explore repositories": project_details,
    "Open issues": issues_backlog,
    "Changes & reviews": pull_request_review,
    "Build activity": cicd_activity,
    "Key findings": risks_recommendations,
}

# Plain-label vertical buttons replace radio choices; there are no bullet
# selectors beside the feature names. Active state is explicit and accessible.
if st.session_state.get("main_nav") not in MENU:
    st.session_state["main_nav"] = "Dashboard"

NAV_ICONS = {
    "Dashboard": ":material/dashboard:",
    "Explore repositories": ":material/folder_open:",
    "Open issues": ":material/assignment_late:",
    "Changes & reviews": ":material/merge:",
    "Build activity": ":material/monitor_heart:",
    "Key findings": ":material/insights:",
}

with st.sidebar:
    brand()
    st.caption("NAVIGATION")
    for label in MENU:
        if st.button(
            label, key="nav_" + label.lower().replace(" ", "_").replace("&", "and"),
            use_container_width=True,
            type="primary" if st.session_state["main_nav"] == label else "secondary",
            icon=NAV_ICONS[label], help=NAV_HELP[label],
        ):
            st.session_state["main_nav"] = label
            st.rerun()
    st.divider()
    st.caption("DATA SOURCE")
    status_slot = st.empty()
    if st.button("Reload stored data", icon=":material/refresh:", use_container_width=True,
                 help="Reload saved records only; ingestion runs in GitHub Actions."):
        get_data.clear()
        st.rerun()
    with st.expander("Reading guide · 1 minute"):
        st.caption("Public GitHub activity, not private client deadlines.")
        for title, meaning in TERMS:
            st.markdown(f"**{title}:** {meaning}")
        st.divider()
        for instruction in HOW_TO_READ:
            st.caption(instruction)

nav = st.session_state["main_nav"]

database_url = os.getenv("DATABASE_URL") or None
snapshot_mtime = SNAPSHOT_PATH.stat().st_mtime_ns if SNAPSHOT_PATH.is_file() else 0
try:
    reports, selection, data_info = get_data(
        database_url, settings.comparison_days, settings.stale_hours, snapshot_mtime)
except Exception:
    with st.sidebar:
        status_slot.warning("Data source unavailable")
    if database_url:
        st.error("Configured database is unavailable. Check DATABASE_URL and schema.")
    else:
        st.error("No verified GitHub snapshot. Run the snapshot workflow or configure PostgreSQL.")
    st.stop()

# P0 verified-first global scope: all six pages use the SAME cohort.
# Original tracked source records remain untouched and can be explored
# by explicitly selecting the labelled exploratory option.
all_reports = reports
verified_28 = verified_joint_cohort(all_reports, days=28)
verified_7 = verified_joint_cohort(all_reports, days=7)
options = [
    "Verified · 28 days",
    "Verified · 7 days",
    "All tracked · exploratory",
]
initial_scope = 0 if verified_28 else 1 if verified_7 else 2
with st.sidebar:
    st.caption("ANALYSIS EVIDENCE SCOPE")
    selected_scope = st.selectbox(
        "Data for all pages", options, index=initial_scope,
        key="global_evidence_scope",
        help=("Verified mode requires full Issue, PR and CI/CD source scans "
              "for the same selected period. Tracked partial sources remain "
              "accessible in exploratory mode and are never deleted."),
    )
    st.caption(
        f"Verified all three sources: {len(verified_28)}/{len(all_reports)} "
        f"for 28 days · {len(verified_7)}/{len(all_reports)} for 7 days."
    )
    st.caption(
        "Verified means the chosen period was fully scanned for "
        "Issues, PR and CI checks. It does not certify the full "
        "open-Issue backlog or project quality."
    )
    st.markdown(
        '<div class="side-footer">Candy Ristyan · Public GitHub data</div>',
        unsafe_allow_html=True,
    )
if selected_scope.startswith("Verified · 28"):
    reports = verified_28
elif selected_scope.startswith("Verified · 7"):
    reports = verified_7
else:
    reports = all_reports
st.caption(
    f"**ANALYSIS COHORT:** {len(reports)}/{len(all_reports)} tracked public "
    f"projects · {selected_scope}. Unverified projects are not counted as inactive."
)
if selected_scope.startswith("All tracked"):
    st.warning(
        "Exploratory source scope: some Issues, PR or CI/CD histories "
        "are incomplete. Unverified sources are retained for exploration. "
        "Treat counts as retrieved samples, not full "
        "project totals or confirmed backlog changes."
    )

if data_info["mode"] == "snapshot":
    # Keep exact UTC stamp for independent public demo verification; include
    # WIB for Indonesian reviewers. Snapshot age and source coverage differ.
    when_utc = data_info["generated_at"].strftime("%d %b %Y · %H:%M UTC")
    when_wib = data_info["generated_at"].astimezone(
        timezone(timedelta(hours=7))
    ).strftime("%d %b %Y · %H:%M WIB")
    st.caption(
        f"**PUBLIC GITHUB SNAPSHOT:** Captured {when_utc} ({when_wib}) · "
        f"{'snapshot older than 12h — refresh needed' if data_info['stale'] else 'snapshot recent; check source verification below'} · "
        "read-only, not a live connection · "
        "[Data notes](https://github.com/Granbe1l/beta-test/blob/main/docs/REVIEWER_QUICK_GUIDE.md)"
    )
    if data_info["stale"]:
        st.warning(
            "The stored snapshot is older than the 12-hour freshness limit. "
            "Some previously Verified sources may no longer qualify. "
            "Reload stored data only rereads the saved file; it does not collect from GitHub."
        )
else:
    st.caption(
        "**PERSISTENT DATA MODE** · PostgreSQL records · collection runs separately")

# Sidebar source health describes the entire tracked population,
# not only the currently filtered verified analysis cohort.
status = status_for(all_reports)
counts = coverage_counts(all_reports)
total = len(all_reports)
complete_open = sum(
    r.get("open_backlog_status") == "complete" for r in all_reports
)
source_status = {
    "complete": "Sources verified",
    "partial": "Partial source scans",
    "stale": "Some sources are older",
    "failed": "Collection needs review",
    "unavailable": "Awaiting first sync",
}.get(status, "Source status unavailable")
if data_info.get("stale"):
    source_status = "Snapshot needs refresh"
status_slot.markdown(
    '<div class="side-health-card">'
    '<div class="side-health-head">COLLECTED RECORDS</div>'
    f'<div class="side-health-status">{source_status}</div>'
    f'<div class="side-health-small">Issues {counts["issues"]}/{total} · '
    f'PRs {counts["pull_requests"]}/{total} · '
    f'CI {counts["workflow_runs"]}/{total}</div>'
    f'<div class="side-health-small">Full open-Issue inventory {complete_open}/{total}</div>'
    '</div>',
    unsafe_allow_html=True,
)

if nav == "Dashboard":
    overview(reports, selection, all_reports=all_reports)
elif nav == "Key findings":
    risks_recommendations(reports, selection)
else:
    MENU[nav](reports)
