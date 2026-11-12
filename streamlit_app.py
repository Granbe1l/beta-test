"""Project Delivery Monitor · visual-first, evidence-based Streamlit app.

Read only: opening a dashboard does not trigger GitHub collection.
The underlying snapshots, collectors and metric formulas are unchanged.
"""
from __future__ import annotations

import os
import streamlit as st

from src.config.settings import Settings
from src.database.store import make_engine, session_factory
from src.analytics.read import load_reports, selection_info
from src.analytics.snapshot import read_snapshot, SNAPSHOT_PATH
from src.ui.theme_v2 import apply_theme_v2, brand
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
    "◫  Dashboard": overview,
    "▣  Explore repositories": project_details,
    "◷  Open issues": issues_backlog,
    "⇄  Changes & reviews": pull_request_review,
    "✓  Build activity": cicd_activity,
    "◎  Key findings": risks_recommendations,
}

with st.sidebar:
    brand()
    st.caption("WORKSPACE")
    nav = st.radio("Explore sections", list(MENU),
                   label_visibility="collapsed", key="main_nav")
    st.divider()
    st.caption("DATA STATUS")
    status_slot = st.empty()
    st.caption("Public GitHub records · view cache: 10 minutes")
    if st.button("↻  Refresh dashboard view", use_container_width=True,
                 help="Reloads stored records, never starts GitHub ingestion."):
        get_data.clear()
        st.rerun()
    st.markdown(
        '<div class="side-footer">Candy Ristyan<br>Open-source delivery analytics</div>',
        unsafe_allow_html=True,
    )

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

if data_info["mode"] == "snapshot":
    when = data_info["generated_at"].strftime("%d %b %Y · %H:%M UTC")
    st.caption(
        f"**PUBLIC GITHUB SNAPSHOT** · Captured {when} · read-only · "
        f"{'stale / refresh needed' if data_info['stale'] else 'recent snapshot'} · "
        "not a live API connection. "
        "[Data notes](https://github.com/Granbe1l/beta-test#data-snapshot)"
    )
else:
    st.caption(
        "**PERSISTENT DATA MODE** · PostgreSQL records · collection runs separately")

status = status_for(reports)
status_slot.caption({
    "complete": "● Sources verified/current",
    "partial": "● Data partially collected",
    "stale": "● Data needs refresh",
    "failed": "● Collection issue",
    "unavailable": "○ Awaiting first sync",
}.get(status, status.title()))

if nav == "◫  Dashboard":
    overview(reports, selection)
elif nav == "◎  Key findings":
    risks_recommendations(reports, selection)
else:
    MENU[nav](reports)
