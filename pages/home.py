"""See your profiles and Jobs"""
import streamlit as st


from src.utils.vector_handler import get_user_analysis_store, get_global_jobs_store, find_all_roles_for_profile
from src.utils.streamlit_utils import display_profile, sidebar_handler, filter_for_profiles, display_job_matches
from main import run_job_matcher


def main_page():
    user_vector_store = get_user_analysis_store()
    global_jobs_store = get_global_jobs_store()

    user_id = st.user.sub


    try:
        active_profile_meta = filter_for_profiles(user_vector_store, user_id)

    except ValueError:
        st.write("# Upload a CV to begin.")
        st.stop()
    
    new_run = st.sidebar.button("Find jobs for the current profile")

    if new_run:
        # TODO
        st.balloons()

    display_profile(profile=active_profile_meta)

    jobs = find_all_roles_for_profile(user_vector_store, active_profile_meta.get("profile_id"))
    
    if jobs:
        st.header("Matched Jobs")
        display_job_matches(jobs)
    st.write(jobs)
    st.write(user_id)
    st.write(active_profile_meta.get("profile_id"))

if __name__ == "__main__":
    main_page()