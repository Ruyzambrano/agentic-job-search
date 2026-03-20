"""Detailed View: Combines AI Analysis with Raw Job Data."""
from json import loads

import streamlit as st

from src.ui.components import display_full_job, render_sidebar_feed
from src.ui.controllers import init_app
from src.ui.streamlit_cache import get_cached_all_jobs_for_user, get_cached_raw_job
from src.schema import AnalysedJobMatchWithMeta, RawJobMatch

def show_specific_job():
    init_app()
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.storage_service

    jobs = get_cached_all_jobs_for_user(storage, user_id)
    if not jobs:
        st.info("Upload a CV to find more jobs")
        st.stop()
    
    jobs = [AnalysedJobMatchWithMeta(**loads(j)) for j in jobs]
    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
    )
    subheader = st.sidebar
    render_sidebar_feed(jobs, subheader, sort_by)

    current_job = st.session_state.get("current_job")

    if not current_job:
        st.info(
            "👈 Select a job from the sidebar or Home page to see the full analysis."
        )
        st.stop()

    with st.spinner("Fetching original job details..."):
        raw_job = get_cached_raw_job(storage, current_job.job_url)
    try:
        raw_job = RawJobMatch(**loads(raw_job))
        display_full_job(raw_job, current_job)
    except Exception as e:
        st.error(f"Display Error: {e}")
        if st.button("Back to Home"):
            st.switch_page("dashboard.py")


if __name__ == "__main__":
    show_specific_job()
