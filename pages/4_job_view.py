"""Detailed View: Combines AI Analysis with Raw Job Data."""

import streamlit as st
from src.ui.components import display_full_job, render_sidebar_feed
from src.ui.controllers import init_app

def show_specific_job():
    init_app()
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.storage_service

    jobs = storage.find_all_jobs_for_user(user_id)
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
        raw_job = storage.find_raw_job_by_url(current_job.job_url)
    try:
        display_full_job(raw_job, current_job)
    except Exception as e:
        st.error(f"Display Error: {e}")
        if st.button("Back to Home"):
            st.switch_page("dashboard.py")


if __name__ == "__main__":
    show_specific_job()
