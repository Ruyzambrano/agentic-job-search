import streamlit as st
from src.utils.streamlit_utils import (
    get_raw_job_data,
    display_full_job,
    find_all_candidate_profiles,
    render_sidebar_feed,
    init_app
)
from src.utils.streamlit_cache import cached_jobs_all_user_profiles, get_cached_user_store, get_cached_global_store
from src.utils.embeddings_handler import get_embeddings



def show_specific_job():
    init_app()
    embeddings = get_embeddings(st.session_state.pipeline_settings.api_settings)
    store = get_cached_user_store(embeddings)
    global_job_store = get_cached_global_store(embeddings)

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
