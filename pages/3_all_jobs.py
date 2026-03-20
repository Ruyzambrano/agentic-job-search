"""Displays all job matches across all of a user's profiles."""
from json import loads

import streamlit as st

from src.ui.components import jobs_filter_sidebar, display_job_matches
from src.ui.controllers import init_app
from src.ui.streamlit_cache import get_cached_all_jobs_for_user
from src.schema import AnalysedJobMatchWithMeta


def all_jobs_page():
    init_app()
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.storage_service

    sidebar = st.sidebar
    sort_by = sidebar.selectbox(
        label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
    )

    st.title("📂 All Market Matches")
    st.write("Browse every job analysis generated across all your uploaded CVs.")
    with st.spinner("Loading your career library..."):
        all_matches = get_cached_all_jobs_for_user(storage, user_id)

    if not all_matches:
        st.info( 
            "No job matches found yet. Upload a CV and run a search to get started!"
        )
    else:
        all_matches = [AnalysedJobMatchWithMeta(**loads(m)) for m in all_matches]
        filtered_jobs = jobs_filter_sidebar(all_matches)

        if not filtered_jobs:
            st.warning("No jobs match your current sidebar filters.")
        else:
            st.write(f"Showing {len(filtered_jobs)} total jobs.")
            display_job_matches(filtered_jobs, sort_by)


if __name__ == "__main__":
    all_jobs_page()
