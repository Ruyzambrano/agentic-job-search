import base64

import streamlit as st

from src.ui.streamlit_cache import get_cv_text
from src.ui.streamlit_cache import get_cached_user_profiles

def login_screen():
    """Renders the high-fidelity Slate authentication interface."""
    
    try:
        with open("assets/icon.svg", "rb") as f:
            icon_b64 = base64.b64encode(f.read()).decode()
            icon_url = f"data:image/svg+xml;base64,{icon_b64}"
    except FileNotFoundError:
        icon_url = "" 
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:
        st.markdown(f"""
            <div style="text-align: center; padding: 40px 0px;">
                <img src="{icon_url}" width="80" style="margin-bottom: 20px;">
                <h1 style="
                    font-family: 'Playfair Display', serif; 
                    color: #C5A267; 
                    font-size: 32px; 
                    letter-spacing: 0.15em;
                    margin-bottom: 10px;
                ">THE SLATE</h1>
                <h2 style="
                    font-family: 'Playfair Display', serif; 
                    color: #8A847A; 
                    font-size: 20px; 
                    letter-spacing: 0.1em;
                    margin-top: 5px;
                    margin-bottom: 30px;
                    font-weight: 400;
                ">Job Curator</h2>
                <p style="
                    font-family: 'Inter', sans-serif; 
                    color: #64748B; 
                    font-size: 10px; 
                    letter-spacing: 0.4em; 
                    text-transform: uppercase;
                    margin-bottom: 40px;
                ">System Authentication Required</p>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
                <p style='font-size: 13px; color: #E2E8F0; text-align: center; margin-bottom: 20px;'>
                    Authorize with your Google identity to access the research pipeline.
                </p>
            """, unsafe_allow_html=True)
            
            st.button(
                "Log In via Google", 
                on_click=st.login, 
                use_container_width=True,
                type="primary"
            )

        st.markdown("""
            <p style='text-align: center; color: #1C2128; font-size: 9px; margin-top: 20px; letter-spacing: 0.1em;'>
                PRIVATE INTELLIGENCE // ENCRYPTION ACTIVE
            </p>
        """, unsafe_allow_html=True)

def sidebar_handler():
    """
    Handles the global sidebar interface for CV uploads.
    Returns the uploaded file object if a new one is provided.
    """
    with st.sidebar:
        st.header("CV Management")
        st.caption("Upload a new CV.")

        new_cv = st.file_uploader(
            "Upload CV (PDF, DOCX)",
            type=["pdf", "docx"],
            help="Your CV will be parsed and matched against live job markets.",
        )

        if new_cv:
            try:
                with st.spinner("Extracting text..."):
                    st.session_state["raw_cv_text"] = get_cv_text(new_cv, st.session_state.last_updated)
                    st.success("CV Read successfully!")
            except Exception as e:
                st.error(f"Failed to convert CV: {e}")

        return new_cv


def profile_selector(storage, user_id):
    """
    Sidebar component to browse and select previously saved CV versions.
    """
    with st.sidebar:
        st.subheader("Saved Profiles")

        profiles = get_cached_user_profiles(storage, user_id, st.session_state.last_updated)

        if not profiles:
            st.info("No saved profiles found. Upload a CV to begin.")
            return None
        options = {}
        for p in profiles:
            raw_date = p.get("created_at", "")
            display_date = raw_date[:16].replace("T", " ")
            display_name = p.get("full_name")
            if display_date and display_name:
                options[p["profile_id"]] = f"{display_date} | {display_name}"

        selected_id = st.selectbox(
            "Select a profile",
            label_visibility="collapsed",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            key="profile_version_selector",
        )

        return next(p for p in profiles if p["profile_id"] == selected_id)


def logout_handler():
    """Simple logout trigger for the sidebar or logout page."""
    if st.sidebar.button("Log out", use_container_width=True):
        st.logout()
