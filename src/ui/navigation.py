import streamlit as st
from src.ui.streamlit_cache import get_cv_text
from src.ui.components import display_profile
from src.ui.streamlit_cache import get_cached_user_profiles
from src.schema import CandidateProfile

def login_screen():
    """Renders the initial authentication interface."""
    with st.container(border=True):
        st.title("🤖 Agentic Job Auditor")
        st.subheader("Login to access your personalized job research")
        st.button("Log in with Google", on_click=st.login, use_container_width=True)


def sidebar_handler():
    """
    Handles the global sidebar interface for CV uploads.
    Returns the uploaded file object if a new one is provided.
    """
    with st.sidebar:
        st.header("📄 CV Management")
        st.caption("Upload a new CV.")

        new_cv = st.file_uploader(
            "Upload CV (PDF, DOCX)",
            type=["pdf", "docx"],
            help="Your CV will be parsed and matched against live job markets.",
        )

        if new_cv:
            try:
                with st.spinner("🔍 Extracting text..."):
                    st.session_state["raw_cv_text"] = get_cv_text(new_cv)
                    st.success("CV Read successfully!")
            except Exception as e:
                st.error(f"Failed to convert CV: {e}")

        return new_cv


def profile_selector(storage, user_id):
    """
    Sidebar component to browse and select previously saved CV versions.
    """
    with st.sidebar:
        st.subheader("🕒 Saved Profiles")

        profiles = get_cached_user_profiles(storage, user_id)

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
