"""Upload a CV and Find Jobs"""
from io import BytesIO

import streamlit as st

from src.utils.document_handler import save_findings_to_docx
from src.utils.streamlit_utils import process_new_cv, sidebar_handler, display_profile, display_job_matches

new_cv = sidebar_handler()

if new_cv:
    with st.sidebar:
        st.success("CV read successfully!")
        st.session_state.desired_role = st.text_input(label="Desired Role", placeholder="A Role Like 'Data Engineer'") or "Data Engineer"
        st.session_state.desired_location = st.text_input(label="Desired Location", placeholder="A Location Like 'London'") or "London"

        st.session_state["job_analysis"] = process_new_cv(st.session_state.desired_role, st.session_state.desired_location)
    st.title("Your CV")
    st.write(st.session_state.raw_cv_text)

    if st.session_state.get("job_analysis"):
        st.session_state.raw_cv_text = ""
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
        display_job_matches(st.session_state["job_analysis"].get("writer_data").jobs, True)