"""Project Delivery Monitor · read-only Streamlit operational dashboard.

Six compact sections inspired by the supplied UI reference.  The former
Repository Explorer and cross-repository analysis remain in Project details.
The dashboard reads persisted records; it NEVER runs GitHub collection on view.
"""
from __future__ import annotations

import os
import streamlit as st

from src.config.settings import Settings
from src.database.store import make_engine, session_factory
from src.analytics.read import load_reports, selection_info
from src.ui.theme import apply_theme, brand
from src.ui.pages import (
    overview, project_details, issues_backlog, pull_request_review,
    cicd_activity, risks_recommendations, status_for,
)

st.set_page_config(
    page_title="Project Delivery Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    # Streamlit-managed secrets are only read at runtime; never logged.
    secret_url = st.secrets.get("DATABASE_URL")
    if secret_url:
        os.environ["DATABASE_URL"] = str(secret_url)
except (FileNotFoundError, KeyError, AttributeError):
    pass

settings = Settings.from_env()
apply_theme()


@st.cache_data(ttl=600, show_spinner=False)
def get_data(database_url, observation_days, stale_hours):
    engine = make_engine(database_url)
    try:
        # Do not auto-create a database from a dashboard view.
        with session_factory(engine)() as session:
            return (
                load_reports(session, observation_days=observation_days, stale_hours=stale_hours),
                selection_info(session),
            )
    finally:
        engine.dispose()


MENU = {
    "◫  Overview": overview,
    "▣  Project details": project_details,
    "☷  Issues & backlog": issues_backlog,
    "⇄  Pull request review": pull_request_review,
    "◎  CI/CD activity": cicd_activity,
    "△  Risks & recommendations": risks_recommendations,
}

with st.sidebar:
    brand()
    st.caption("WORKSPACE")
    nav = st.radio("Explore sections", list(MENU), label_visibility="collapsed", key="main_nav")
    st.divider()
    st.caption("DATA STATUS")
    status_slot = st.empty()
    st.caption("Collection is read-only · cache TTL 10 minutes")
    if st.button("↻  Refresh data view", use_container_width=True, help="Refresh the database view. Does not call GitHub API."):
        get_data.clear()
        st.rerun()
    st.markdown('<div class="side-footer">Candy Ristyan<br>Open-source delivery analytics</div>', unsafe_allow_html=True)

try:
    reports, selection = get_data(settings.database_url, settings.comparison_days, settings.stale_hours)
except Exception:
    with st.sidebar:
        status_slot.warning("Database unavailable")
    st.error("Database unavailable or not initialized. Set DATABASE_URL and run python scripts/init_db.py. Live data is not claimed.")
    st.stop()

status = status_for(reports)
status_slot.caption({
    "complete": "● Verified / current",
    "partial": "● Partial coverage",
    "stale": "● Source is stale",
    "failed": "● Collection failed",
    "unavailable": "○ Awaiting first sync",
}.get(status, status.title()))

if nav == "◫  Overview":
    overview(reports, selection)
elif nav == "△  Risks & recommendations":
    risks_recommendations(reports, selection)
else:
    MENU[nav](reports)
