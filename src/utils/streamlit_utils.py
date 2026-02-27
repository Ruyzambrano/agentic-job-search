from datetime import datetime
import tempfile
from os import remove

from markitdown import MarkItDown
import streamlit as st

from src.utils.vector_handler import find_all_candidate_profiles

def login_screen():
    st.button("Log in with Google", on_click=st.login)

def iso_formatter(option: datetime):
    """Makes an ISO string human readable"""
    try:
        dt = datetime.fromisoformat(option)
        return dt.strftime("%d %b %H:%M")
    except:
        return option
    
def display_profile(profile: dict):
    st.title(f"{profile.get("full_name")}")
    st.write(profile.get("summary"))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("## Previous roles")
        st.write(f"- {"\n- ".join(profile.get("job_titles"))}")
    with col2:
        st.write("## Key Skills")
        st.write(f"- {"\n- ".join(profile.get('key_skills'))}")
    with col3:
        st.write("## Industries")
        st.write(f"- {"\n- ".join(profile.get("industries"))}")

def sidebar_handler():
    with st.sidebar:
        st.header("📄 CV Management")
        new_cv = st.file_uploader("Upload a new CV (PDF, DOCX)", type=["pdf", "docx"])
        if new_cv:
            try:
                with st.spinner("Converting CV to text..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{new_cv.name}") as tmp_file:
                        tmp_file.write(new_cv.getvalue())
                        tmp_path = tmp_file.name
                    
                    md = MarkItDown()
                    result = md.convert(tmp_path)
                    cv_text = result.text_content

                    remove(tmp_path)

                    st.session_state["raw_cv_text"] = cv_text
            except Exception as e:
                st.error(f"Failed to convert CV: {e}")
        return new_cv
    
def filter_for_profiles(user_vector_store, user_id):
        profiles = find_all_candidate_profiles(user_vector_store, user_id)

        with st.sidebar:
            selected_timestamp = st.selectbox(
                label="Or choose your CV version",
                options=[m["created_at"] for m in profiles], 
                format_func=iso_formatter,                     
                key="cv_selection"                        
            )
        return next(m for m in profiles if m["created_at"] == selected_timestamp)


def display_job_matches(job_matches: dict):
    for job in job_matches:
        st.write(f"### {job.title}")