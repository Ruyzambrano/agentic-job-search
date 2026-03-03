from datetime import datetime
from os import remove
import tempfile
import asyncio
import re

from markitdown import MarkItDown
import streamlit as st
from streamlit_tags import st_tags


from src.schema import AnalysedJobMatch, AnalysedJobMatchWithMeta, RawJobMatch
from main import run_job_matcher
from src.utils.vector_handler import (
    find_all_candidate_profiles,
    get_global_jobs_store,
    get_user_analysis_store,
    find_all_roles_for_profile,
    find_all_roles_for_user,
    fetch_raw_job_data,
    delete_profile,
)
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
            key="cv_selection",
        )
    return next(m for m in profiles if m["created_at"] == selected_timestamp)


def display_job_matches(
    job_matches: list[AnalysedJobMatch], sort_by: str = "top_applicant_score"
):
    job_matches = sort_analysed_job_matches_with_meta(job_matches, sort_by)
    col1, col2 = st.columns(2)
    for i in range(1, len(job_matches) + 1, 2):
        with col1:
            display_job_match(job_matches[i - 1])
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

        if hasattr(job, "tech_stack") and job.tech_stack:
            chips = " | ".join([f":grey[{tech}]" for tech in job.tech_stack[:5]])
            st.markdown(f"**Tech:** {chips}")

        if st.button(
            "View Full Analysis & Details",
            key=f"view_{job.job_url}",
            use_container_width=True,
        ):
            st.session_state.current_job = job
            st.switch_page("pages/4_job_view.py")
        st.link_button("Apply for this role", url=job.job_url, use_container_width=True)


def format_salary_as_range(salary_min: int, salary_max: int):
    if salary_min and salary_max:
        return f"£{salary_min:,} - £{salary_max:,}"
    if salary_max:
        return f"£{salary_max:,}"
    if salary_min:
        return f"{salary_min:,}"
    return "Salary not specified"


def process_new_cv(desired_role: str, desired_location: str):
    analyse = st.button("Analyse CV and search for jobs", type="primary")

    if analyse:
        with st.status("Getting you jobs"):
            config = {
                "configurable": {
                    "user_id": st.user.sub,
                    "location": desired_location,
                    "role": desired_role,
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
            "role": st.session_state.get("desired_role", ""),
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
def cached_jobs_all_user_profiles(_store, user_id):
    return find_all_roles_for_user(_store, user_id)


def normalize(text: str) -> str:
    if not text:
        return ""
    return str(text).title().replace("-", " ").replace("–", " ").strip()


def get_job_val(job, fields: list[str], default=None):
    """Helper to try multiple field names on a Pydantic object."""
    for field in fields:
        val = getattr(job, field, None)
        if val is not None:
            return val
    return default


def jobs_filter_sidebar(jobs: list):
    with st.sidebar:
        keywords = st_tags(
            label="Keyword Match", suggestions=["Data", "AI", "Langchain", "Python"]
        )

        all_base_cities = set()
        for job in jobs:
            cities = extract_base_locations(job.location)
            all_base_cities.update(cities)

        selected_cities = st.multiselect(
            "Filter by City", options=sorted(list(all_base_cities))
        )

        all_companies = sorted(
            list(set(get_job_val(job, ["company", "company_name"]) for job in jobs))
        )
        selected_companies = st.multiselect("Companies", options=all_companies)

        all_attributes = set()
        for job in jobs:
            attrs = getattr(job, "attributes", []) or []
            all_attributes.update([normalize(a) for a in attrs])
            all_attributes.add(normalize(getattr(job, "schedule_type", "")))
            all_attributes.add(normalize(getattr(job, "work_setting", "")))

        all_attributes.discard("")
        selected_attributes = st.multiselect(
            "Attributes", options=sorted(list(all_attributes))
        )

        salaries = [job.salary_min for job in jobs if job.salary_min] + [
            job.salary_max for job in jobs if job.salary_max
        ]
        max_limit = ((max(salaries) // 1000) + 1) * 1000 if salaries else 200_000

        min_choice, max_choice = st.select_slider(
            label="Salary Range",
            options=range(0, max_limit + 5000, 1000),
            value=(0, max_limit),
        )

        col1, col2 = st.columns(2)
        with col1:
            min_choice = st.number_input(
                "Low", value=min_choice, step=1000, label_visibility="collapsed"
            )
        with col2:
            max_choice = st.number_input(
                "High", value=max_choice, step=1000, label_visibility="collapsed"
            )

        all_tech = set()
        for job in jobs:
            tech_data = get_job_val(job, ["tech_stack", "qualifications"], [])
            if isinstance(tech_data, list):
                all_tech.update(tech_data)
        selected_tech = st.multiselect("Tech Stack", options=sorted(list(all_tech)))

        filtered_jobs = jobs
        filtered_jobs = filter_jobs_by_keywords(filtered_jobs, keywords)

        if selected_cities:
            filtered_jobs = [
                job
                for job in filtered_jobs
                if any(
                    city.lower() in (job.location or "").lower()
                    for city in selected_cities
                )
            ]
        if selected_companies:
            filtered_jobs = [
                j
                for j in filtered_jobs
                if get_job_val(j, ["company", "company_name"]) in selected_companies
            ]

        if selected_attributes:
            normalized_selected = [normalize(a) for a in selected_attributes]
            filtered_jobs = [
                j
                for j in filtered_jobs
                if any(
                    normalize(val) in normalized_selected
                    for val in (
                        getattr(j, "attributes", [])
                        or [
                            getattr(j, "schedule_type", ""),
                            getattr(j, "work_setting", ""),
                        ]
                    )
                )
            ]

        if selected_tech:
            filtered_jobs = [
                j
                for j in filtered_jobs
                if all(
                    t in get_job_val(j, ["tech_stack", "qualifications"], [])
                    for t in selected_tech
                )
            ]

        filtered_jobs = [
            j
            for j in filtered_jobs
            if (j.salary_max or 0) >= min_choice and (j.salary_min or 0) <= max_choice
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


def display_full_job(
    full_job: AnalysedJobMatchWithMeta, current_job: RawJobMatch, profile: dict
):
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
            unsafe_allow_html=True,
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
        badge_html = "".join(
            [
                f'<span style="background-color:#e1e4e8; color:#0366d6; padding:4px 12px; margin:4px; border-radius:12px; font-weight:bold; display:inline-block;">{tech}</span>'
                for tech in current_job.tech_stack
            ]
        )
        st.markdown(badge_html, unsafe_allow_html=True)

    with right_col:
        st.link_button(
            "Apply for This Role",
            full_job.job_url,
            use_container_width=True,
            type="primary",
        )
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
    lower_keywords = [kw.lower().strip() for kw in keywords if kw.strip()]

    for job in jobs:
        searchable_text = " ".join(
            [
                str(getattr(job, "title", "")),
                str(getattr(job, "company", "")),
                str(getattr(job, "job_summary", "")),
                str(getattr(job, "location", "")),
                " ".join(getattr(job, "tech_stack", []) or []),
                " ".join(getattr(job, "attributes", []) or []),
            ]
        ).lower()

        if any(kw in searchable_text for kw in lower_keywords):
            filtered.append(job)

    return filtered


def render_sidebar_feed(jobs: list[AnalysedJobMatchWithMeta], subheader, sort_by: str):
    jobs = sort_analysed_job_matches_with_meta(jobs, sort_by)
    with st.sidebar:
        subheader.subheader("🎯 Matched Roles")
        st.caption(f"Showing {len(jobs)} opportunities")

        for job in jobs:
            is_selected = st.session_state.get("current_job") == job
            button_label = (
                f"**{job.title}**\n\n{job.company}\n\n{job.top_applicant_score}% Match"
            )

            if st.button(
                button_label,
                key=f"btn_{job.job_url}_{job.analysed_at}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.current_job = job
                st.rerun()


@st.dialog("Delete Profile")
def delete_profile(store, profile_id):
    if st.button("Are you sure you want to delete this profile?"):
        delete_profile(store, profile_id)
        st.write("Profile deleted")
        return


def display_raw_job_matches(jobs: list[RawJobMatch], sort_by: str):
    """Renders a grid of raw job listings."""
    jobs = sort_raw_job_matches_with_meta(jobs, sort_by)
    col1, col2 = st.columns(2)

    for i in range(0, len(jobs), 2):
        with col1:
            display_raw_job_card(jobs[i])
        with col2:
            if i + 1 < len(jobs):
                display_raw_job_card(jobs[i + 1])


def display_raw_job_card(job: RawJobMatch):
    """Displays a single raw job listing with metadata badges."""
    with st.container(border=True):
        card_id = f"{job.job_url}"
        col_title, col_meta = st.columns([4, 2])

        with col_title:
            st.markdown(f"### {job.title}")
            st.markdown(f"**{job.company_name}** | {job.location}")

            setting_emoji = "🏠" if job.work_setting == "Remote" else "🏢"
            badges = f"{setting_emoji} `{job.work_setting}` · 📅 `{job.schedule_type}`"
            if job.is_contract:
                badges += " · 📑 :red[Contract]"
            st.markdown(badges)

        with col_meta:
            st.button(
                f"🕒 {job.posted_at or 'Recently'}",
                disabled=True,
                use_container_width=True,
                key=card_id,
            )

        st.divider()
        salary_display = job.salary_string or "Not Specified"
        if job.salary_min and job.salary_max:
            salary_display = f"£{job.salary_min:,} - £{job.salary_max:,}"

        st.markdown(f"##### 💰 `{salary_display}`")

        snippet = (
            job.description[:250] + "..."
            if len(job.description) > 250
            else job.description
        )
        st.write(snippet)

        if job.qualifications:

            chips = "  ".join(
                [f":blue-background[{q}]" for q in job.qualifications[:5]]
            )
            st.markdown(chips)

        st.link_button(
            "🌐 View Original Listing", url=job.job_url, use_container_width=True
        )


def match_all_jobs_for_setting_or_schedule(jobs: list[RawJobMatch], attribute: str):
    return [job for job in jobs if matches_setting_or_schedule(job, attribute)]


def matches_setting_or_schedule(job: RawJobMatch, attribute: str) -> bool:
    return job.schedule_type == attribute or job.work_setting


def extract_base_locations(location_str: str) -> list[str]:
    """
    Splits 'London / Hybrid / Telford' into ['London', 'Telford']
    and removes parentheticals like '(Remote)'.
    """
    if not location_str:
        return []

    # 1. Normalize delimiters: change slashes and commas to pipes for easy splitting
    # "London / Hybrid" -> "London | Hybrid"
    normalized = location_str.replace("/", "|").replace(",", "|")

    # 2. Split into parts
    parts = [p.strip() for p in normalized.split("|")]

    clean_cities = []
    for p in parts:
        # 3. Use regex to strip anything inside () or []
        # "London (Flexible" -> "London "
        # "Remote)" -> "Remote"
        p_clean = re.sub(r"[\(\[].*?[\)\]]", "", p)  # Removes content inside brackets
        p_clean = (
            p_clean.replace("(", "").replace(")", "").strip()
        )  # Catches stray brackets

        # 4. Standardize 'Remote' or 'Hybrid' keywords
        if "remote" in p_clean.lower():
            clean_cities.append("Remote")
        elif "hybrid" in p_clean.lower():
            clean_cities.append("Hybrid")
        elif "flexible" in p_clean.lower():
            clean_cities.append("Flexible")
        elif len(p_clean) > 2:
            clean_cities.append(p_clean.title())

    return sorted(list(set(clean_cities)))


def render_settings_page():
    st.title("⚙️ Pipeline Settings")

    tab1, tab2, tab3 = st.tabs(["Agent Logic", "Data Ingestion", "API & Integrations"])

    with tab1:
        st.subheader("Match Scoring Weights")
        st.info("Adjust how the AI ranks candidates against job descriptions.")
        col1, col2 = st.columns(2)
        with col1:
            tech_weight = st.slider("Tech Stack Importance", 0, 100, 70)
            exp_weight = st.slider("Experience Importance", 0, 100, 50)
        with col2:
            loc_weight = st.slider("Location Importance", 0, 100, 30)
            culture_weight = st.slider("Soft Skills Importance", 0, 100, 20)

    with tab2:
        st.subheader("Scraper Configuration")
        st.selectbox(
            "Sync Frequency", ["Real-time", "Every 6 Hours", "Daily", "Weekly"]
        )
        st.toggle("Auto-archive expired listings", value=True)
        if st.button("Force Global Re-index", type="primary"):
            st.warning("This will re-run analysis on all raw jobs. Proceed?")

    with tab3:
        st.subheader("Secrets & Connections")
        st.text_input("GEmini API Key", type="password")
        st.text_input(
            "Slack Webhook URL", placeholder="https://hooks.slack.com/services/..."
        )

    if st.button("Save Configuration"):
        st.success("Settings updated and applied to Agent Pipeline.")


def sort_analysed_job_matches_with_meta(
    jobs: list[AnalysedJobMatchWithMeta], sort_by
) -> list[AnalysedJobMatchWithMeta]:
    sort_map = {
        "Score": "top_applicant_score",
        "Analysis Date": "analysed_at",
        "Company": "company",
        "Role": "title",
    }

    target_attr = sort_map.get(sort_by, sort_by)

    reverse = target_attr in ["top_applicant_score", "analysed_at"]
    jobs.sort(key=lambda x: getattr(x, target_attr), reverse=reverse)
    return jobs


def sort_raw_job_matches_with_meta(
    jobs: list[AnalysedJobMatchWithMeta], sort_by
) -> list[AnalysedJobMatchWithMeta]:
    sort_map = {"Posted Date": "posted_at", "Company": "company_name", "Role": "title"}

    target_attr = sort_map.get(sort_by, sort_by)

    reverse = target_attr == "posted_at"
    jobs.sort(key=lambda x: getattr(x, target_attr), reverse=reverse)
    return jobs
