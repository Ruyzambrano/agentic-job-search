"""See your profiles and Jobs"""
import streamlit as st

from src.utils.streamlit_utils import display_profile, filter_for_profiles, display_job_matches, get_cached_global_store, get_cached_user_store, get_cached_jobs, run_job_matcher

def main_page():
    user_vector_store = get_cached_user_store()
    global_jobs_store = get_cached_global_store()

    user_id = st.user.sub


    try:
        active_profile_meta = filter_for_profiles(user_vector_store, user_id)

    except ValueError:
        st.write("# Upload a CV to begin.")
        st.stop()
    
    if st.sidebar.button("Find jobs for the current profile"):
        selected_profile_id = active_profile_meta.get("profile_id")
        
        config = {
            "configurable": {
                "user_id": user_id,
                "active_profile_id": selected_profile_id,
                "location": st.session_state.get("desired_location", ""),
                "role": st.session_state.get("desired_role", "")
            }
        }
        with st.status("Searching for jobs using existing profile..."):
            st.session_state["job_analysis"] = run_job_matcher("", config)

    display_profile(profile=active_profile_meta)

    jobs = get_cached_jobs(user_vector_store, active_profile_meta.get("profile_id"))
    
    if jobs:
        st.header("Matched Jobs")
        display_job_matches(jobs)

if __name__ == "__main__":
    main_page()