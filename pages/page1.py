"""Upload a CV and Find Jobs"""
from io import BytesIO

import streamlit as st

from src.utils.document_handler import save_findings_to_docx
from src.utils.streamlit_utils import process_new_cv, sidebar_handler, display_profile, display_job_matches

new_cv = sidebar_handler()

if new_cv:
    st.success("CV read successfully!")
    desired_role = st.text_input("Role")
    desired_location = st.text_input("Location")
    st.session_state["job_analysis"] = process_new_cv(desired_role, desired_location)

    if st.session_state.get("job_analysis"):
        buffer = save_findings_to_docx(st.session_state["job_analysis"])
        if isinstance(buffer, BytesIO):
            st.download_button(
                label="Download Analysis (.docx)",
                data=buffer,
                file_name="job_analysis.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.error(f"Could not prepare download: {buffer}")
        display_profile(st.session_state["job_analysis"].get("cv_data").model_dump())
        st.write("## Matched Jobs")
        display_job_matches(st.session_state["job_analysis"].get("writer_data").jobs)