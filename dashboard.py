"""Displays CandidateProfile and allows user to update CV. Maybe view previous profiles?"""

import streamlit as st

from src.utils.streamlit_utils import login_screen
from src.schema import AnalysedJobMatch

if __name__ =="__main__":
    st.set_page_config(page_title="CV Job Searcher", layout="wide")
    
    if not st.user.is_logged_in:
        login_screen()
        st.stop()

    pages = {
        "Your Job Search": [
            st.Page(page="pages/home.py", title="Home", default=True),
            st.Page(page="pages/page1.py", title="Upload a new CV"),
            st.Page(page="pages/page2.py", title="Page 2 Placeholder"),
            st.Page(page="pages/page3.py", title="Page 3 Placeholder")
        ],
        "Settings": [
            st.Page(page="pages/settings.py", title="Settings"),
            st.Page(page="pages/logout.py", title="Log out")
        ]
    }

    nav_bar = st.navigation(pages, position="top")
    if nav_bar:
        nav_bar.run()

        

    


