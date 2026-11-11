"""Project Delivery Monitor. No API-wide sync occurs during page visits."""
import os
import streamlit as st
from src.config.settings import Settings
from src.database.store import make_engine, session_factory
from src.analytics.read import load_reports, selection_info
from src.ui.theme import apply_theme
from src.ui.pages import overview, explorer, repository_analysis, comparison, methodology

st.set_page_config(page_title="Project Delivery Monitor",page_icon="📊",layout="wide",initial_sidebar_state="expanded")
try:
    secret_url=st.secrets.get("DATABASE_URL")
    if secret_url: os.environ["DATABASE_URL"] = str(secret_url)
except Exception:
    pass
settings=Settings.from_env()
apply_theme()

@st.cache_data(ttl=600,show_spinner=False)
def get_data(database_url, observation_days, stale_hours):
    engine=make_engine(database_url)
    try:
        # No create_all here: dashboard is read-only, provision with scripts/init_db.py.
        with session_factory(engine)() as session:
            return load_reports(session,observation_days=observation_days,stale_hours=stale_hours), selection_info(session)
    finally: engine.dispose()

with st.sidebar:
    st.markdown("### PROJECT DELIVERY MONITOR")
    st.caption("Open-source analytics · GitHub")
    nav=st.radio("Explore",["Overview","Repository Explorer","Repository Analysis","Cross-Repository Comparison","Findings & Methodology"],label_visibility="collapsed")
    st.divider()
    st.caption("Read-only dashboard · cached up to 10 minutes")
    if st.button("Refresh cached view",use_container_width=True):
        get_data.clear()
        st.rerun()

try:
    reports, selection=get_data(settings.database_url,settings.comparison_days,settings.stale_hours)
except Exception:
    st.error("Database unavailable or not initialized. Configure DATABASE_URL and run 'python scripts/init_db.py' first. No live data is claimed.")
    st.stop()

if nav=="Overview": overview(reports,selection)
elif nav=="Repository Explorer": explorer(reports)
elif nav=="Repository Analysis": repository_analysis(reports)
elif nav=="Cross-Repository Comparison": comparison(reports)
else: methodology(reports,selection)
