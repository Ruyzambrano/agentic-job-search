"""See your profiles and Jobs"""
import streamlit as st

from src.utils.streamlit_utils import display_profile, filter_for_profiles, display_job_matches, get_cached_global_store, get_cached_user_store, get_cached_jobs_for_profile, search_for_new_jobs

def main_page():
    user_vector_store = get_cached_user_store()
    global_jobs_store = get_cached_global_store()

    user_id = st.user.sub


    try:
        active_profile_meta = filter_for_profiles(user_vector_store, user_id)

    except ValueError:
        st.write("# Upload a CV to begin.")
        st.stop()
    
    with st.sidebar:
        st.session_state.desired_role = st.text_input(label="Desired Role", placeholder="A Role Like 'Data Engineer'") or "Data Engineer"
        st.session_state.desired_location = st.text_input(label="Desired Location", placeholder="A Location Like 'London'") or "London"

        if st.button("Find jobs for the current profile"):
            st.session_state["job_analysis"] = search_for_new_jobs(active_profile_meta, user_id)

    display_profile(profile=active_profile_meta)

    jobs = get_cached_jobs_for_profile(user_vector_store, active_profile_meta.get("profile_id"))
    
    if jobs:
        st.header("Matched Jobs")
        display_job_matches(jobs, True)

if __name__ == "__main__":
    main_page()