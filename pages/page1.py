"""Upload a CV and Find Jobs"""
import streamlit as st

from src.utils.streamlit_utils import sidebar_handler

new_cv = sidebar_handler()

if new_cv:
    st.success("CV read successfully!")
    desired_role = st.text_input("Role")
    desired_location = st.text_input("Location")
    analyse = st.button("Analyse CV and search for jobs")

    if analyse:
        with st.status("Getting you jobs"):
            config = {
                "configurable": {
                    "user_id": user_id, 
                    "location": desired_location, 
                    "role": desired_role
                    }
                }
            try:
                run_job_matcher(st.session_state["raw_cv_text"], config)
            except Exception as e:
                st.error(str(e))
            finally:
                new_cv = None