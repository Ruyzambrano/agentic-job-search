import streamlit as st

from src.utils.streamlit_utils import cached_jobs_all_user_profiles, get_cached_global_store, get_cached_user_store, display_job_matches, jobs_filter_sidebar


if __name__ == "__main__":
    store = get_cached_user_store()

    jobs = cached_jobs_all_user_profiles(store, st.user.sub)

    filtered_jobs = jobs_filter_sidebar(jobs)
    st.title("All Jobs Matched to You")
    display_job_matches(filtered_jobs, True)
    
