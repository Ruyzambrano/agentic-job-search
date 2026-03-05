"""Displays CandidateProfile and allows user to update CV. Maybe view previous profiles?"""

import streamlit as st

from src.utils.streamlit_utils import login_screen, init_app
from src.utils.local_storage import get_local_storage

if __name__ == "__main__":
    st.set_page_config(page_title="CV Job Searcher", layout="wide")

    if not st.user.is_logged_in:
        login_screen()
        st.stop()
    storage = get_local_storage()
    init_app()
    pages = [
        st.Page(page="pages/1_home.py", title="Home", default=True),
        st.Page(page="pages/3_all_jobs.py", title="Your Jobs"),
        st.Page(page="pages/4_job_view.py", title="Job Detail"),
        st.Page(page="pages/5_global_jobs.py", title="All Jobs"),
        st.Page(page="pages/6_market_views.py", title="Global Market"),
        st.Page(page="pages/7_settings.py", title="Settings"),
        st.Page(page="pages/8_logout.py", title="Log out"),
    ]

    nav_bar = st.navigation(pages, position="top")
    if nav_bar:
        nav_bar.run()
