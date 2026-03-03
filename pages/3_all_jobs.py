import streamlit as st

from src.utils.streamlit_utils import (
    cached_jobs_all_user_profiles,
    get_cached_user_store,
    display_job_matches,
    jobs_filter_sidebar,
)

if __name__ == "__main__":
    store = get_cached_user_store()
    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
    )
    jobs = cached_jobs_all_user_profiles(store, st.user.sub, sort_by)

    filtered_jobs = jobs_filter_sidebar(jobs)
    st.title("All Jobs Matched to You")
    display_job_matches(filtered_jobs, sort_by)
