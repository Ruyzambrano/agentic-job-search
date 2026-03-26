import streamlit as st
from json import loads
from src.ui.components import (
    display_profile, display_job_matches, display_profile_management, show_how, add_sidebar_support
)
from src.utils.geo import resolve_location
from src.ui.navigation import sidebar_handler, profile_selector
from src.ui.controllers import process_new_cv, search_for_new_jobs, init_app
from src.ui.streamlit_cache import get_cached_profile_matches
from src.schema import AnalysedJobMatchWithMeta

def render_sidebar(storage, user_id):
    """Encapsulates all sidebar inputs and CV detection."""
    with st.sidebar:
        sidebar_handler()
        st.session_state.desired_role = st.text_input("Target Role", value="Data Engineer")
        st.session_state.loc = st.text_input("Target Location", value="London")
        cv_button = st.empty()
        
        st.session_state.active_profile = profile_selector(storage, user_id)
        display_profile_management(storage, st.session_state.active_profile)
        
        return cv_button

def handle_research_actions(cv_placeholder):
    """Logic for triggering the actual AI Agent runs."""
    if st.session_state.get("raw_cv_text"):
        if cv_placeholder.button("Search with your new CV", type="primary", width="stretch"):
            with st.status("🤖 Analyzing CV...", expanded=True) as status:
                geo_obj = resolve_location(st.session_state.loc, st.session_state.loc)
                result = process_new_cv(st.session_state.raw_cv_text, st.session_state.desired_role, geo_obj)
                st.session_state.active_profile = loads(result).get("cv_data")
                status.update(label="Profile Created!", state="complete")
                st.rerun()
            st.cache_data.clear()

    if st.session_state.active_profile:
        if st.button(f"🔍 Search Market for {st.session_state.desired_role} roles in {st.session_state.loc}", use_container_width=True):
            with st.spinner("Geo-locating..."):
                geo_data = resolve_location(st.session_state.loc, st.session_state.loc)
            with st.status("📡 Scraping & Auditing...", expanded=False) as status:
                search_for_new_jobs(st.session_state.active_profile, st.user.sub, geo_data)
                status.update(label="Complete!", state="complete")
            st.cache_data.clear()

def home_page():
    init_app()
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.storage_service
    region = st.session_state.pipeline_settings.scraper_settings.region
    api_settings = st.session_state.pipeline_settings.api_settings

    if not any([api_settings.gemini_api_key, api_settings.anthropic_api_key, api_settings.openai_api_key]):
        show_how()
        return

    cv_alert_area = render_sidebar(storage, user_id)

    st.title("🚀 Career Discovery Dashboard")
    
    handle_research_actions(cv_alert_area)

    if st.session_state.active_profile:
        display_profile(st.session_state.active_profile)
        
        if getattr(api_settings, "free_tier"):
            st.warning(f"Throttling enabled for {api_settings.ai_provider} Free Tier.")

        st.divider()
        render_results_section(storage)
    else:
        st.info("👋 Welcome! Please upload a CV or select a profile to begin.")

def render_results_section(storage):
    """Handles sorting logic and the job grid."""
    header_col, sort_col = st.columns([3, 1])
    header_col.subheader("🎯 Top Market Matches")
    sort_by = sort_col.selectbox("Sort by", options=["Score", "Date", "Company"], label_visibility="collapsed")
    
    raw_matches = get_cached_profile_matches(storage, st.session_state.active_profile["profile_id"])
    
    if raw_matches:
        matches = [AnalysedJobMatchWithMeta(**loads(m)) for m in raw_matches]
        display_job_matches(matches, sort_by)
    else:
        st.info("No matches found for this profile yet. Hit search to start!")

if __name__ == "__main__":
    home_page()
    add_sidebar_support()
