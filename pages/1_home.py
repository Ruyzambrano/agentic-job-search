import streamlit as st
from json import loads
from datetime import datetime

from src.ui.components import (
    display_profile, display_job_matches, display_profile_management, show_how, add_sidebar_support
)
from src.utils.geo import resolve_location
from src.ui.navigation import sidebar_handler, profile_selector
from src.ui.controllers import process_new_cv, search_for_new_jobs, init_app
from src.ui.streamlit_cache import get_cached_profile_matches
from src.schema import AnalysedJobMatchWithMeta
from src.services.database import SupabaseStorage

def sync_user_data(user_id):
    """
    Force-pulls fresh data from Supabase to ensure 
    the UI matches the database 'Source of Truth'.
    """
    storage = st.session_state.supabase_service

    st.session_state.user_status = storage.get_user_status(user_id, True)

    saved_cv = storage.client.table("cv_vault") \
        .select("parsed_metadata") \
        .eq("user_id", user_id) \
        .maybe_single().execute()
        
    if saved_cv.data:
        st.session_state.active_profile = saved_cv.data["parsed_metadata"]
    else:
        st.session_state.active_profile = None

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
    """
    Handles AI processing, persistent storage in the CV Vault, 
    search metering, and state synchronization.
    """
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.supabase_service
    
    status = st.session_state.get("user_status", {"tier": "free", "has_cv": False})
    tier = status.get("tier")
    has_full_access = tier in ["pro", "trial"]
    has_cv = status.get("has_cv", False)

    if st.session_state.get("raw_cv_text") and (has_full_access or not has_cv):
        if cv_placeholder.button("Analyze & Create Dossier", type="primary", use_container_width=True):
            try:
                with st.status("Parsing CV...", expanded=True) as s:
                    geo_obj = resolve_location(st.session_state.loc, st.session_state.loc)
                    result = process_new_cv(
                        st.session_state.raw_cv_text, 
                        st.session_state.desired_role, 
                        geo_obj
                    )
                    
                    analysis_output = loads(result)
                    parsed_profile = analysis_output.get("cv_data")
                    
                    st.session_state.active_profile = parsed_profile
                    
                    storage.save_cv(user_id, st.session_state.raw_cv_text, parsed_profile)
                    
                    storage.client.table("user_state").update({
                        "has_active_cv": True
                    }).eq("user_id", user_id).execute()
                    
                    s.update(label="Dossier Created & Vaulted!", state="complete")
                
                st.session_state["raw_cv_text"] = None
                st.session_state.last_updated = datetime.now().timestamp()
                
                st.session_state.user_status = storage.get_user_status(user_id, True)
                st.rerun()
                
            except Exception as e:
                st.error(f"◈ Dossier Creation Failed: {e}")

    if st.session_state.active_profile:
        search_label = f"Search Market for {st.session_state.desired_role} roles"
        
        if st.button(search_label, use_container_width=True):
            access = storage.check_and_increment_search(user_id)
            
            if access["allowed"]:
                try:
                    with st.spinner("Geo-locating target market..."):
                        geo_data = resolve_location(st.session_state.loc, st.session_state.loc)
                    
                    status_msg = f"Auditing Market... ({access['remaining_count']} remaining)"
                    with st.status(status_msg, expanded=False) as s:
                        search_for_new_jobs(st.session_state.active_profile, user_id, geo_data)
                        s.update(label="Market Audit Complete!", state="complete")
                    
                    st.session_state.last_updated = datetime.now().timestamp()
                    
                    st.session_state.user_status['remaining_searches'] = access['remaining_count']
                    st.rerun()

                except Exception as e:
                    st.error(f"◈ Search Failed: {e}")
                    storage.refund_search_credit(user_id)
                    st.info("Your search credit has been restored.")
                    st.session_state.user_status = storage.get_user_status(user_id)
            
            else:
                st.error("◈ Daily Limit Reached")
                st.info(f"The **{access['current_tier']}** tier is capped at 3 searches per day.")
                st.link_button("Upgrade to Pro for Unlimited Access", st.secrets.STRIPE_LINK)

def home_page():
    user_id = st.user.sub if st.user else "local-user"
    storage = st.session_state.storage_service
    api_settings = st.session_state.pipeline_settings.api_settings

    params = st.query_params
    if params.get("session_id") or params.get("success") == "true":
        sync_user_data(user_id)
        status = st.session_state.get("user_status", {}).get("tier")
        if status == "pro":
            st.balloons()
            st.success("◈ Welcome to The Slate Pro. Your limits have been lifted.")
        st.query_params.clear()
        

    if not any([api_settings.gemini_api_key, api_settings.anthropic_api_key, api_settings.openai_api_key]):
        show_how()
        return

    cv_alert_area = render_sidebar(storage, user_id)

    st.title("Your Curated Job Search")
    
    

    if st.session_state.active_profile:
        display_profile(st.session_state.active_profile)
        handle_research_actions(cv_alert_area)
        if getattr(api_settings, "free_tier"):
            st.warning(f"Throttling enabled for {api_settings.ai_provider} Free Tier.")

        st.divider()
        render_results_section(storage)
    else:
        st.info("Welcome! Please upload a CV or select a profile to begin.")
    
def render_results_section(storage):
    """Handles sorting logic and the job grid."""
    header_col, sort_col = st.columns([3, 1])
    header_col.subheader("Top Market Matches")
    sort_by = sort_col.selectbox("Sort by", options=["Score", "Date", "Company"], label_visibility="collapsed")
    raw_matches = get_cached_profile_matches(storage, st.session_state.active_profile, st.session_state.last_updated)
    if raw_matches:
        matches = [AnalysedJobMatchWithMeta(**loads(m)) for m in raw_matches]
        display_job_matches(matches, sort_by)
    else:
        st.info("No matches found for this profile yet. Hit search to start!")

if __name__ == "__main__":
    init_app()
    home_page()
    add_sidebar_support()
