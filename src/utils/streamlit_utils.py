from datetime import datetime
from os import remove
import tempfile
import asyncio

from markitdown import MarkItDown
import streamlit as st
from streamlit_tags import st_tags


from src.schema import AnalysedJobMatch, AnalysedJobMatchWithMeta, RawJobMatch
from main import run_job_matcher
from src.utils.vector_handler import find_all_candidate_profiles, get_global_jobs_store, get_user_analysis_store, find_all_roles_for_profile, find_all_roles_for_user, fetch_raw_job_data
from src.utils.document_handler import save_findings_to_docx

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

def upload_file(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.name}") as tmp_file:
        tmp_file.write(file.getvalue())
        tmp_path = tmp_file.name
    md = MarkItDown()
    result = md.convert(tmp_path)
    file_text = result.text_content

    remove(tmp_path)

    return file_text

def sidebar_handler():
    with st.sidebar:
        st.header("📄 CV Management")
        new_cv = st.file_uploader("Upload a new CV (PDF, DOCX)", type=["pdf", "docx"])
        if new_cv:
            try:
                with st.spinner("Converting CV to text..."):
                    st.session_state["raw_cv_text"] = get_cv_text(new_cv)
                    
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


def display_job_matches(job_matches: list[AnalysedJobMatch], sorted_jobs:bool = False):
    if sorted_jobs:
        job_matches.sort(key=lambda x: x.analysed_at if x.analysed_at else "0", reverse=True)
    col1, col2 = st.columns(2)
    for i in range(1, len(job_matches)+1, 2):
        with col1:
            display_job_match(job_matches[i-1])
        with col2:
            if len(job_matches) > i:
                display_job_match(job_matches[i])

def display_job_match(job: AnalysedJobMatch):
    with st.container(border=True):
        col_header, col_score = st.columns([4, 2])
        with col_header:
            st.markdown(f"### {job.title}")
            st.markdown(f"**{job.company}** | {job.location}")
            if job.attributes:
                attr_chips = " · ".join([f"_{a}_" for a in job.attributes])
                st.markdown(f"{attr_chips}")
        with col_score:
            with st.container(border=5):
                score = job.top_applicant_score
                st.metric("Match Score", f"{score}%")
                
                st.progress(score / 100)
        
        salary_str = format_salary_as_range(job.salary_min, job.salary_max)
        st.markdown(f"##### 💰 `{salary_str}` &nbsp;&nbsp;")
        
        st.write(job.job_summary)
        
        if hasattr(job, 'tech_stack') and job.tech_stack:
            chips = " | ".join([f":grey[{tech}]" for tech in job.tech_stack[:5]])
            st.markdown(f"**Tech:** {chips}")

        if st.button("View Full Analysis & Details", key=f"view_{job.job_url}", use_container_width=True):
            st.session_state.current_job = job
            st.switch_page("pages/job_view.py")
        st.link_button("Apply for this role", url=job.job_url, use_container_width=True)

def format_salary_as_range(salary_min: int, salary_max:int):
    if salary_min and salary_max:
        return f"£{salary_min:,} - £{salary_max:,}"
    if salary_max:
        return f"£{salary_max:,}"
    if salary_min:
        return f"{salary_min:,}"
    return "Salary not specified"


def process_new_cv(desired_role: str, desired_location:str):
    analyse = st.button("Analyse CV and search for jobs", type="primary")

    if analyse:
        with st.status("Getting you jobs"):
            config = {
                "configurable": {
                    "user_id": st.user.sub, 
                    "location": desired_location, 
                    "role": desired_role
                    }
                }
            try:
                return get_job_analysis(st.session_state["raw_cv_text"], config)
                
            except Exception as e:
                st.error(str(e))
        st.success("Success!")


def search_for_new_jobs(active_profile_meta: dict, user_id):
    selected_profile_id = active_profile_meta.get("profile_id")
        
    config = {
        "configurable": {
            "user_id": user_id,
            "active_profile_id": selected_profile_id,
            "location": st.session_state.get("desired_location", ""),
            "role": st.session_state.get("desired_role", "")
        }
    }
    with st.status("Searching for jobs using existing profile..."):
        return asyncio.run(run_job_matcher("", config))

@st.cache_data(show_spinner=False)
def get_job_analysis(cv_text, config):
    return asyncio.run(run_job_matcher(cv_text, config))

@st.cache_data(show_spinner=False)
def generate_docx(state):
    return save_findings_to_docx(state)

st.cache_data(show_spinner=False)
def get_cv_text(uploaded_file):
    return upload_file(uploaded_file)

@st.cache_resource
def get_cached_user_store():
    return get_user_analysis_store()

@st.cache_resource
def get_cached_global_store():
    return get_global_jobs_store()

@st.cache_data(show_spinner="Fetching matched jobs...")
def get_cached_jobs_for_profile(_store, profile_id):
    return find_all_roles_for_profile(_store, profile_id)

@st.cache_data()
def cached_jobs_all_user_profiles(_store, user_id, sort_by="top_applicant_score", reverse:bool = True):
    return find_all_roles_for_user(_store, user_id, sort_by, reverse)

def jobs_filter_sidebar(jobs: list[AnalysedJobMatchWithMeta]) -> list[AnalysedJobMatchWithMeta]:
    with st.sidebar:
        keywords = st_tags(label="Keyword Match", suggestions=["Data", "AI", "Langchain", "Data Scientist", "AWS", "ETL", "Gen AI", "Python"])
        
        all_locations = sorted(list(set(job.location for job in jobs)))
        selected_locations = st.multiselect("Locations", options=all_locations)

        all_companies = sorted(list(set(job.company for job in jobs)))
        selected_companies = st.multiselect("Companies", options=all_companies)

        all_attributess = sorted(list(set(attribute for job in jobs for attribute in job.attributes)))
        selected_attributes = st.multiselect("Attributes", options=all_attributess)

        salaries = [job.salary_min for job in jobs if job.salary_min] + [job.salary_max for job in jobs if job.salary_max]
        max_salary = ((max(salaries) // 1000) + 1) * 1000 if salaries else 1_000_000


        st.session_state.minimum_choice, st.session_state.maximum_choice = st.select_slider(
            label="Salary Range",
            options=range(0, max_salary+5000, 1000),
            value=(0, max_salary)
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.minimum_choice = st.number_input(
                label_visibility="collapsed", 
                label="low salary", 
                value=st.session_state.minimum_choice,
                step=1000)

        with col2:
            st.session_state.maximum_choice = st.number_input(
                label="high salary", 
                label_visibility="collapsed", 
                value=st.session_state.maximum_choice,
                step=1000
                )
        all_tech = sorted(list(set(tech for job in jobs for tech in job.tech_stack)))
        selected_tech = st.multiselect(label="Tech Stack", options=all_tech)

        filtered_jobs = jobs
        filtered_jobs = filter_jobs_by_keywords(filtered_jobs, keywords)

        if selected_locations:
            filtered_jobs = [job for job in jobs if job.location in selected_locations]
        
        if selected_companies:
            filtered_jobs = [job for job in jobs if job.company in selected_companies]

        if selected_attributes:
            filtered_jobs = [job for job in filtered_jobs if all(attribute in job.attributes for attribute in selected_attributes)]        
        
        if selected_tech:
            filtered_jobs = [job for job in filtered_jobs if all(tech in job.tech_stack for tech in selected_tech)]        
        
        filtered_jobs = [
            job for job in filtered_jobs
            if (job.salary_max or 0) >= st.session_state.minimum_choice and (job.salary_min or 0) <= st.session_state.maximum_choice
        ]
        
        return filtered_jobs
    

def get_colour_map(score: int) -> str:
    if score > 85:
        return "green"
    if score > 70:
        return "orange"
    return "red"

@st.cache_data
def get_raw_job_data(_store, job_url):
    return fetch_raw_job_data(_store, job_url)

def display_full_job(full_job: AnalysedJobMatchWithMeta, current_job: RawJobMatch, profile: dict):
    col_header, col_score = st.columns([3, 1])
    with col_header:
        st.title(f"🏢 {full_job.title}")
        st.subheader(f"{full_job.company_name} | {full_job.location}")
    with col_score:
        score = current_job.top_applicant_score
        color = "green" if score > 85 else "orange" if score > 60 else "red"
        st.markdown(
            f"""
            <div style="text-align: center; border: 2px solid {color}; border-radius: 10px; padding: 10px;">
                <span style="font-size: 14px; color: gray;">MATCH SCORE</span><br>
                <span style="font-size: 40px; font-weight: bold; color: {color};">{score}%</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

    st.divider()
    
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown("### 📝 Job Summary")
        st.info(current_job.job_summary)

        st.markdown("### 🤖 Why You're a Great Fit")
        st.write(current_job.top_applicant_reasoning)

        st.markdown("### 🛠 Tech Stack")
        # Visualizing tech stack as badges
        badge_html = "".join([f'<span style="background-color:#e1e4e8; color:#0366d6; padding:4px 12px; margin:4px; border-radius:12px; font-weight:bold; display:inline-block;">{tech}</span>' for tech in current_job.tech_stack])
        st.markdown(badge_html, unsafe_allow_html=True)

    with right_col:
        st.link_button("Apply for This Role", full_job.job_url, use_container_width=True, type="primary")
        with st.expander("💰 Financials & Schedule", expanded=True):
            st.write(f"**Salary Range:** {full_job.salary_string}")
            st.write(f"**Work Setting:** {full_job.work_setting}")
            st.write(f"**Contract Type:** {full_job.schedule_type}")
            st.write(f"**In-Office Policy:** {current_job.office_days}")
        
        with st.expander("📍 Requirements Checklist", expanded=True):
            for q in full_job.qualifications:
                st.write(f"✅ {q}")

        st.caption(f"Posted: {full_job.posted_at}")

def filter_jobs_by_keywords(jobs: list[AnalysedJobMatch], keywords: list[str]):
    if not keywords:
        return jobs
    
    filtered = []
    for job in jobs:
        job_content = job.model_dump_json().lower()

        if any(kw.lower() in job_content for kw in keywords):
            filtered.append(job)
            
    return filtered

def render_sidebar_feed(jobs: list[AnalysedJobMatchWithMeta]):
    with st.sidebar:
        st.subheader("🎯 Matched Roles")
        st.caption(f"Showing {len(jobs)} opportunities")
        
        for job in jobs:
            is_selected = st.session_state.get("current_job") == job
            
            button_label = f"**{job.title}**\n\n{job.company}\n\n{job.top_applicant_score}% Match"
            
            if st.button(
                button_label, 
                key=f"btn_{job.job_url}", 
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.current_job = job
                st.rerun()