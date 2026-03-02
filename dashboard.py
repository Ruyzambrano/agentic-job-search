"""Displays CandidateProfile and allows user to update CV. Maybe view previous profiles?"""

import streamlit as st

from src.utils.streamlit_utils import login_screen
from src.schema import AnalysedJobMatch

if __name__ =="__main__":
    st.set_page_config(page_title="CV Job Searcher", layout="wide")
    
    if not st.user.is_logged_in:
        login_screen()
        st.stop()

    pages = [
            st.Page(page="pages/home.py", title="Home", default=True),
            st.Page(page="pages/cv_uploader.py", title="Upload a new CV"),
            st.Page(page="pages/all_jobs.py", title="Your Jobs"),
            st.Page(page="pages/job_view.py", title="Job Detail"),
            st.Page(page="pages/global_jobs.py", title="All Jobs"),
            st.Page(page="pages/market_views.py", title="Global Market"),
            st.Page(page="pages/settings.py", title="Settings"),
            st.Page(page="pages/logout.py", title="Log out")
    ]

    nav_bar = st.navigation(pages, position="top")
    if nav_bar:
        nav_bar.run()

        

    


