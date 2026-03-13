"""See your profiles and Jobs"""
from time import time

import streamlit as st

from src.utils.streamlit_utils import (
    display_profile,
    filter_for_profiles,
    display_job_matches,
    search_for_new_jobs,
    delete_profile_dialogue,
    cv_handler,
    process_new_cv,
    init_app,
)
from src.utils.embeddings_handler import get_embeddings
from src.utils.streamlit_cache import (
    get_cached_global_store,
    get_cached_jobs_for_profile,
    get_cached_user_store,
)

def main_page():
    init_app()
    embedding = get_embeddings()
    user_vector_store = get_cached_user_store(embedding)
    global_jobs_store = get_cached_global_store(embedding)
    user_id = st.user.sub

    sidebar = st.sidebar
    sorting_container = sidebar.container()
    st.session_state.desired_role = (
        sidebar.text_input(
            label="Desired Role", 
            value=st.session_state.get("desired_role", "Data Engineer"),
            placeholder="e.g. Data Engineer"
        )
    )
    st.session_state.desired_location = (
        sidebar.text_input(
            label="Desired Location", 
            value=st.session_state.get("desired_location", "London"),
            placeholder="e.g. London"
        )
    )

    sidebar.divider()

    if sidebar.button("Add New CV", use_container_width=True):
        cv_handler()

    try:
        active_profile_meta = filter_for_profiles(user_vector_store, user_id)
    except ValueError:
        st.write("# Upload a CV to begin.")
        st.stop()


    if sidebar.button("Find jobs for the current profile", use_container_width=True):
        st.session_state.start_searching = True

    if st.session_state.get("start_processing") or st.session_state.get("start_searching"):
        with st.status("Running Agent Pipeline...", expanded=True) as status:
            if st.session_state.get("start_processing"):
                st.write("### Step 1: Profile Analysis")
                st.write("Extracting skills and experience from CV...")
                analysis = process_new_cv(
                    st.session_state.raw_cv_text,
                    st.session_state.desired_role,
                    st.session_state.desired_location,
                )
                st.session_state["job_analysis"] = analysis
                st.session_state.start_processing = False
                st.session_state.raw_cv_text = None

            if st.session_state.get("start_searching"):
                st.write("### Step 2: Job Research")
                st.write("Scouring LinkedIn and Google Jobs for matching roles...")
                st.session_state["job_analysis"] = search_for_new_jobs(
                    active_profile_meta, user_id
                )
                st.session_state.start_searching = False

            st.session_state.last_updated = time()
            status.update(label="Pipeline Complete!", state="complete")
        st.rerun()

    sidebar.divider()
    sidebar.write("### Danger Zone:")
    if sidebar.button("Permanently Delete Current Profile", use_container_width=True, type="primary"):
        delete_profile_dialogue(user_vector_store, active_profile_meta.get("profile_id"))
        st.session_state.last_updated = time()

    display_profile(profile=active_profile_meta)

    jobs = get_cached_jobs_for_profile(
        user_vector_store, 
        active_profile_meta.get("profile_id"),
        st.session_state.get("last_updated", time())
    )

    if jobs:
        with sorting_container:
            sort_by = st.selectbox(
                label="Sort Jobs by", 
                options=["Score", "Analysis Date", "Company", "Role"]
            )
        st.header("Matched Jobs")
        display_job_matches(jobs, sort_by)


if __name__ == "__main__":
    main_page()
