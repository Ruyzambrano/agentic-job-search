"""Displays a single user's job matches"""
from time import time

import streamlit as st

from src.utils.streamlit_utils import display_job_matches, jobs_filter_sidebar, init_app
from src.utils.streamlit_cache import (
    get_cached_user_store,
    cached_jobs_all_user_profiles,
)
from src.utils.embeddings_handler import get_embeddings


def all_jobs_page():
    init_app()
    store = get_cached_user_store(
        get_embeddings()
    )
    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
    )
    jobs = cached_jobs_all_user_profiles(store, st.user.sub, st.session_state.last_updated)

    filtered_jobs = jobs_filter_sidebar(jobs)
    st.title("All Jobs Matched to You")
    if not filtered_jobs:
        st.info("No job matches found yet. Run a search from the Home page!")
    else:
        display_job_matches(filtered_jobs, sort_by)


if __name__ == "__main__":
    all_jobs_page()
