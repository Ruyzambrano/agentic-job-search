"""
Home Page: The primary workspace for the user.
"""
from json import loads

import streamlit as st
from src.ui.navigation import sidebar_handler, profile_selector
from src.ui.components import (
    display_profile,
    display_job_matches,
    display_profile_management,
)
from src.utils.geo import resolve_location
from src.ui.controllers import process_new_cv, search_for_new_jobs, init_app
from src.ui.streamlit_cache import generate_docx, get_cached_profile_matches
from src.schema import AnalysedJobMatchWithMeta

def home_page():
    init_app()
    user_id = st.user.sub if st.user else "local-user"
    region = st.session_state.pipeline_settings.scraper_settings.region
    storage = st.session_state.storage_service
    sidebar_handler()
    st.session_state.desired_role = st.sidebar.text_input("Target Role", value="Data Engineer")
    st.session_state.loc = st.sidebar.text_input("Target Location", value="London")
    cv_button = st.sidebar.empty()
    st.sidebar.divider()
    st.session_state.active_profile = profile_selector(storage, user_id)
    display_profile_management(storage, st.session_state.active_profile)
    st.title("🚀 Career Discovery Dashboard")
    if st.session_state.get("raw_cv_text"):
        cv_button.subheader("New CV Detected")
        
        if cv_button.button("Find jobs with your new CV", type="primary"):
            with st.spinner("Validating location..."):
                geo_obj = resolve_location(st.session_state.loc, region)
                st.session_state.desired_location = geo_obj
            with st.status("🤖 Running Agents...", expanded=True) as status:
                result = process_new_cv(st.session_state.raw_cv_text, st.session_state.desired_role, st.session_state.desired_location)
                st.session_state.active_profile = loads(result.get("cv_data"))
                status.update(label="Research Complete!", state="complete")

    if st.session_state.active_profile:
        display_profile(st.session_state.active_profile)

        if st.button(f"Seach for new {st.session_state.desired_role} roles in {st.session_state.loc}", use_container_width=True):
            with st.spinner("Validating location..."):
                geo_data = resolve_location(st.session_state.loc, region)
                st.session_state.desired_location = geo_data
            with st.status("🔍 Scraping Market...", expanded=False):
                search_for_new_jobs(st.session_state.active_profile, user_id)
            get_cached_profile_matches.clear()
            st.rerun()


        if getattr(st.session_state.pipeline_settings.api_settings, "free_tier"):
            st.warning(f"You are using a free tier, the pipeline will be slower to prevent throttling by {st.session_state.pipeline_settings.api_settings.ai_provider}")

        col1, _, col3 = st.columns([3, 3, 2])
        with col1:
            st.subheader("🎯 Top Market Matches")
        with col3:
            sort_by = st.selectbox(
                label="Sort by", options=["Score", "Analysis Date", "Company", "Role"]
            )
        raw_matches = get_cached_profile_matches(storage,
            st.session_state.active_profile["profile_id"]
        )
        if raw_matches:
            matches = [AnalysedJobMatchWithMeta(**loads(m)) for m in raw_matches]
            display_job_matches(matches, sort_by)
            # TODO: Implement Generate Docx to download the research report using result
        else:
            st.info("Refresh Market Research to see more jobs")

    else:
        st.info("Please upload a CV in the sidebar to begin your job search.")


if __name__ == "__main__":
    home_page()
