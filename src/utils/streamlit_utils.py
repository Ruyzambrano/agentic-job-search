from datetime import datetime
import tempfile
from os import remove

from markitdown import MarkItDown
import streamlit as st

from src.schema import AnalysedJobMatch
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
        with st.expander(label="## Previous roles", expanded=False):
            st.write(f"- {"\n- ".join(profile.get("job_titles"))}")
    with col2:
        with st.expander(label="## Key Skills", expanded=False):
            st.write(f"- {"\n- ".join(profile.get('key_skills'))}")
    with col3:
        with st.expander(label="## Industries", expanded=False):
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


def display_job_matches(job_matches: list[AnalysedJobMatch]):
    col1, col2 = st.columns(2)
    for i in range(1, len(job_matches)+1, 2):
        with col1:
            display_job_match(job_matches[i-1])
        with col2:
            if len(job_matches) > i:
                display_job_match(job_matches[i])

def display_job_match(job: AnalysedJobMatch):
    with st.container(border=5):
        st.write(f"### {job.title}")
        st.write(f"#### {job.company}")
        st.write(job.location)
        st.write(format_salary_as_range(job.salary_min, job.salary_max))
        st.link_button(label="Apply for job", url=job.job_url)
        st.write(job.job_summary)

def format_salary_as_range(salary_min: int, salary_max:int):
    if salary_min and salary_max:
        return f"£{salary_min} - £{salary_max}"
    if salary_max:
        return f"£{salary_max}"
    if salary_min:
        return f"{salary_min}"
    return "Salary not specified"