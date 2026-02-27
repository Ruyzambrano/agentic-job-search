import json

import streamlit as st

from markitdown import MarkItDown
from src.utils.vector_handler import get_user_analysis_store, get_global_jobs_store
from src.utils.streamlit_utils import iso_formatter, display_profile

"""
View CandidateProfile

Upload CV

Sidebar - choose profile (if multiple)

Top Job Matches for profile


"""

def main_page():
    user_vector_store = get_user_analysis_store()
    global_jobs_store = get_global_jobs_store()

    profiles = user_vector_store.get(ids=[f"profile_Ruy001"]).get("metadatas")
    with st.sidebar:
        selected_timestamp = st.selectbox(
            label="Choose your CV version",
            options=[m["created_at"] for m in profiles], 
            format_func=iso_formatter,                     
            key="cv_selection"                        
        )
        new_cv = st.file_uploader("Add a new CV")
    active_profile_meta = next(m for m in profiles if m["created_at"] == selected_timestamp)
    display_profile(profile=active_profile_meta)

    if new_cv:
        writer = MarkItDown()
        st.write(writer.convert(new_cv))


if __name__ == "__main__":
    main_page()