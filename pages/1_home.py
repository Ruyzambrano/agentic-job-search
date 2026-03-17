"""
Home Page: The primary workspace for the user.
"""

import streamlit as st
from src.ui.navigation import sidebar_handler, profile_selector
from src.ui.components import (
    display_profile,
    display_job_matches,
    display_profile_management,
)
from src.ui.controllers import process_new_cv, search_for_new_jobs


def home_page():
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.storage_service
    sidebar_handler()
    st.session_state.active_profile = profile_selector(storage, user_id)
    display_profile_management(storage, st.session_state.active_profile)

    st.title("🚀 Career Discovery Dashboard")

    if st.session_state.get("raw_cv_text"):
        st.subheader("New CV Detected")
        role = st.text_input("Target Role", value="Data Engineer")
        loc = st.text_input("Target Location", value="London / Remote")

        if st.button("Start Full Research Pipeline", type="primary"):
            with st.status("🤖 Running Agents...", expanded=True) as status:
                result = process_new_cv(st.session_state.raw_cv_text, role, loc)
                status.update(label="Research Complete!", state="complete")

    elif st.session_state.active_profile:
        display_profile(st.session_state.active_profile)

        if st.button("Refresh Market Research", use_container_width=True):
            search_for_new_jobs(st.session_state.active_profile, user_id)

        col1, _, col3 = st.columns([3, 3, 2])
        with col1:
            st.subheader("🎯 Top Market Matches")
        with col3:
            sort_by = st.selectbox(
                label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
            )
        matches = storage.find_job_matches_for_profile(
            st.session_state.active_profile["profile_id"]
        )
        if matches:
            display_job_matches(matches, sort_by)
        else:
            st.info("Refresh Market Reserach to see more jobs")

    else:
        st.info("Please upload a CV in the sidebar to begin your job search.")


if __name__ == "__main__":
    home_page()
