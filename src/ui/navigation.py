import base64
from datetime import datetime, timezone

import streamlit as st

from src.ui.streamlit_cache import get_cv_text
from src.ui.streamlit_cache import get_cached_user_profiles

def login_screen():
    """Renders the high-fidelity Slate authentication interface."""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
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


def render_sidebar_subscription_logic():
    status = st.session_state.get("user_status", {})
    tier = status.get("tier")
    
    with st.sidebar:
        # --- ◈ FREE TIER VIEW ◈ ---
        if tier == "free":
            remaining = status.get("remaining_searches", 0)
            percent_left = remaining / 3
            st.progress(value=percent_left, text=f"{remaining}/3 searches left")
            st.caption("Free access is limited to 1 CV and 3 daily searches.")
            
            st.link_button(
                "Unlock Unlimited Access", 
                st.secrets.STRIPE_LINK,
                use_container_width=True,
                type="primary"
            )
        
        elif tier == "trial":
            end_date_str = status.get("trial_end") 
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                delta = end_date - now
                days_left = max(0, delta.days)

                countdown_text = f"{days_left} Days Remaining" if days_left > 0 else "Expires Today"

                st.markdown(f"""
                    <div style="border-left: 3px solid #C5A267; padding-left: 15px; margin: 20px 0 10px 0;">
                        <p style="color: #C5A267; font-size: 11px; letter-spacing: 0.1em; margin: 0; font-weight: 600;">PREMIUM ACCESS</p>
                        <p style="font-size: 18px; font-weight: 400; margin: 0; color: #E2E8F0;">{countdown_text}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                if days_left <= 2:
                    st.caption("Your trial period is concluding. Lock in Pro access below.")
                
                st.link_button(
                    "Upgrade to Pro", 
                    st.secrets.STRIPE_LINK, 
                    use_container_width=True,
                    type="primary"
                )

        # --- ◈ PRO TIER VIEW ◈ ---
        elif tier == "pro":
            st.markdown("""
                <div style="border: 1px solid #C5A267; padding: 10px; border-radius: 2px; text-align: center; background-color: rgba(197, 162, 103, 0.05);">
                    <p style="color: #C5A267; font-size: 11px; letter-spacing: 0.2em; margin: 0; font-weight: 700;">◈ PRO MEMBER ◈</p>
                </div>
            """, unsafe_allow_html=True)

def sidebar_handler():
    """
    Handles the global sidebar interface for CV uploads.
    Returns the uploaded file object if a new one is provided.
    """
    render_sidebar_subscription_logic()
    status = st.session_state.get("user_status", {"tier": "free", "has_cv": False})
    tier = status.get("tier")
    has_full_access = tier in ["pro", "trial"]
    has_cv = status.get("has_cv", False)

    with st.sidebar:
        st.header("CV Management")

        if has_full_access or not has_cv:
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
        else:
            st.write("Upgrade to The Slate PRO to add more CVs")

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
