import streamlit as st
from src.utils.streamlit_utils import (
    get_raw_job_data,
    display_full_job,
    find_all_candidate_profiles,
    cached_jobs_all_user_profiles,
    get_cached_user_store,
    get_cached_global_store,
    render_sidebar_feed,
    init_app
)


def show_specific_job():
    init_app()
    store = get_cached_user_store()
    global_job_store = get_cached_global_store()

    subheader = st.sidebar.empty()
    sort_by = st.sidebar.selectbox(
        label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
    )

    jobs = cached_jobs_all_user_profiles(store, st.user.sub)
    profile = find_all_candidate_profiles(store, st.user.sub)[0]
    render_sidebar_feed(jobs, subheader, sort_by)

    if st.session_state.get("current_job"):
        current_job = st.session_state.current_job
    else:
        st.title("Select a job")
        st.stop()

    full_job = get_raw_job_data(global_job_store, current_job.job_url)

    display_full_job(full_job, current_job, profile)


if __name__ == "__main__":
    show_specific_job()
