"""
Main Entry Point: Handles authentication, navigation, and global service initialization.
"""

import streamlit as st
from st_social_media_links import SocialMediaIcons

from src.ui.controllers import init_app
from src.ui.navigation import login_screen

if __name__ == "__main__":
    st.set_page_config(page_title="Agentic Job Auditor", page_icon="🤖", layout="wide")
    if not st.user.is_logged_in:
        login_screen()
    else:
        init_app()
        pages = {
            "Jobs":
                [
                    st.Page(page="pages/1_home.py", title="Home", icon="🏠", default=True),
                    st.Page(page="pages/3_all_jobs.py", title="Your Matches", icon="🎯"),
                    st.Page(page="pages/4_job_view.py", title="Job Analysis", icon="🔬"),
                ],
            "Global": 
                [
                    st.Page(page="pages/6_market_views.py", title="Market Trends", icon="📊"),
                    st.Page(page="pages/5_global_jobs.py", title="Global Library", icon="🌐")
                ],
            "Settings": 
                [
                    st.Page(page="pages/2_about.py", title="About", icon="ℹ️"),
                    st.Page(page="pages/7_settings.py", title="Pipeline Settings", icon="⚙️"),
                    st.Page(page="pages/8_logout.py", title="Log out", icon="🚪")
                ],
            "Support the Project":
                [
                    st.Page(page="pages/9_support.py", title="Buy Me a Coffee", icon="☕️")
                ]
        }

        nav_bar = st.navigation(pages, position="top")

        if nav_bar:
            nav_bar.run()
    

    st.space("stretch")
    st.divider()
    social_media_icons = SocialMediaIcons(
        [
            "https://github.com/ruyzambrano",
            "https://linkedin.com/in/ruy-zambrano",
            "https://ko-fi.com/ruyzambrano"
        ],
        colors=["grey", None, None]
    )

    social_media_icons.render(sidebar=False)