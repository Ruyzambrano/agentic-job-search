import streamlit as st
from src.utils.streamlit_utils import get_raw_job_data, display_full_job, find_all_candidate_profiles, cached_jobs_all_user_profiles, get_cached_user_store, get_cached_global_store, render_sidebar_feed




store = get_cached_user_store()
global_job_store = get_cached_global_store()

jobs = cached_jobs_all_user_profiles(store, st.user.sub, "company", False)
profile = find_all_candidate_profiles(store, st.user.sub)[0]

render_sidebar_feed(jobs)

if st.session_state.get("current_job"):
    current_job = st.session_state.current_job
else:
    st.title("Select a job")
    st.stop()

full_job = get_raw_job_data(global_job_store, current_job.job_url)
raw_job = full_job
analysis = current_job

display_full_job(full_job, current_job, profile)

