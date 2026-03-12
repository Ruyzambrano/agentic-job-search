from datetime import datetime

import streamlit as st
from streamlit_tags import st_tags
from streamlit_local_storage import LocalStorage


from src.schema import (
    AnalysedJobMatch,
    AnalysedJobMatchWithMeta,
    RawJobMatch,
    PipelineSettings,
    AgentWeights,
)
from src.utils.vector_handler import (
    find_all_candidate_profiles,
    fetch_raw_job_data,
    delete_profile,
)
from src.utils.local_storage import (
    get_browser_key,
    set_new_key,
    save_provider_config,
    get_local_storage,
)
from src.utils.func import (
    format_salary_as_range,
    iso_formatter,
    normalize,
    get_job_val,
    filter_jobs_by_keywords,
    get_weight_map,
    sort_analysed_job_matches_with_meta,
    sort_raw_job_matches_with_meta,
    extract_base_locations,
    get_provider_config,
    get_model_roles,
)
from src.utils.model_functions import (
    get_gemini_text_models,
    get_model_index,
    get_all_gemini_models,
)
from src.utils.embeddings_handler import validate_and_get_models
from src.utils.streamlit_cache import get_job_analysis, get_cv_text


def login_screen():
    st.button("Log in with Google", on_click=st.login)


def display_profile(profile: dict):
    st.title(f"{profile.get("full_name")}")
    st.write(profile.get("summary"))

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.expander(label="Previous roles", expanded=False):
            st.write(f"- {"\n- ".join(profile.get("job_titles"))}")
    with col2:
        with st.expander(label="Key Skills", expanded=False):
            st.write(f"- {"\n- ".join(profile.get('key_skills'))}")
    with col3:
        with st.expander(label="Industries", expanded=False):
            st.write(f"- {"\n- ".join(profile.get("industries"))}")


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

        if hasattr(job, "key_skills") and job.key_skills:
            chips = " | ".join([f":grey[{tech}]" for tech in job.key_skills[:5]])
            st.markdown(f"**Tech:** {chips}")

        if st.button(
            "View Full Analysis & Details",
            key=f"view_{job.job_url}",
            use_container_width=True,
        ):
            st.session_state.current_job = job
            st.switch_page("pages/4_job_view.py")
        st.link_button("Apply for this role", url=job.job_url, use_container_width=True)


def process_new_cv(raw_cv_text: str, desired_role: str, desired_location: str):
    """Pure logic function: No buttons, just execution."""
    config = {
        "configurable": {
            "user_id": st.user.sub if st.user else "local-user",
            "location": desired_location,
            "role": desired_role,
            "pipeline_settings": st.session_state.pipeline_settings,
        }
    }
    models = validate_and_get_models()
    return get_job_analysis(raw_cv_text, config, models)


def search_for_new_jobs(active_profile_meta: dict, user_id):
    selected_profile_id = active_profile_meta.get("profile_id")

    config = {
        "configurable": {
            "user_id": user_id,
            "active_profile_id": selected_profile_id,
            "location": st.session_state.get("desired_location", ""),
            "role": st.session_state.get("desired_role", ""),
            "pipeline_settings": st.session_state.pipeline_settings,
        }
    }
    models = validate_and_get_models()
    with st.status("Searching for jobs using existing profile..."):
        return get_job_analysis("", config, models)


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
            skill_data = get_job_val(job, ["key_skills", "qualifications"], [])
            if isinstance(skill_data, list):
                all_tech.update(skill_data)
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
                    t in get_job_val(j, ["key_skills", "qualifications"], [])
                    for t in selected_tech
                )
            ]

        filtered_jobs = [
            j
            for j in filtered_jobs
            if (j.salary_max or 0) >= min_choice and (j.salary_min or 0) <= max_choice
        ]
        return filtered_jobs


@st.cache_data
def get_raw_job_data(_store, job_url):
    return fetch_raw_job_data(_store, job_url)


def display_full_job(
    full_job: AnalysedJobMatchWithMeta, current_job: RawJobMatch, profile: dict
):
    col_header, col_score = st.columns([3, 1])
    with col_header:
        st.title(f"🏢 {full_job.title}")
        st.subheader(f"{current_job.company} | {full_job.location}")
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
        badge_html = "".join(
            [
                f'<span style="background-color:#e1e4e8; color:#0366d6; padding:4px 12px; margin:4px; border-radius:12px; font-weight:bold; display:inline-block;">{tech}</span>'
                for tech in current_job.key_skills
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
            st.write(f"**Salary Range:** {format_salary_as_range(current_job.salary_min, current_job.salary_max)}")
            st.write(f"**Contract Type:** {" | ".join(current_job.attributes)}")
            st.write(f"**In-Office Policy:** {current_job.office_days}")

        with st.expander("📍 Requirements Checklist", expanded=True):
            for q in full_job.qualifications:
                st.write(f"✅ {q}")

        st.caption(f"Job found at: {datetime.fromisoformat(current_job.analysed_at).strftime("%d/%m/%Y %H:%M")}")

    if hasattr(full_job, "description"):
        st.subheader("Job Description")
        with st.container(border=True):
            parts = full_job.description.split('\n')
            for part in parts:
                if part.strip() in [f"About {current_job.company.split()[0]}", f"About {current_job.company}", "The Role", "Responsibilities", "Person Specification", "You will"]:
                    st.subheader(part.strip())
                elif part.startswith("•"):
                    st.markdown(f"* {part[1:].strip()}")
                else:
                    st.write(part)

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
def delete_profile_dialogue(store, profile_id):
    if st.button("Are you sure you want to delete this profile?"):
        delete_profile(store, profile_id)
        st.write("Profile deleted")
        st.rerun()


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


def scoring_weights_setting_tab(storage: LocalStorage):
    st.subheader("Match Scoring Weights")
    st.caption("Influence how the Critical Recruitment Auditor ranks candidates.")
    weight_map = get_weight_map()
    reversed_weight_map = {v: k for k, v in weight_map.items()}
    weights = st.session_state.pipeline_settings.weights
    new_weights_map = {}
    col1, col2 = st.columns(2)
    with col1:
        new_weights_map["key_skills"] = st.select_slider(
            f"Tech Stack Importance (:blue[Currently {reversed_weight_map.get(weights.key_skills)}])",
            options=reversed_weight_map,
            format_func=reversed_weight_map.get,
            value=weights.key_skills,
        )

        new_weights_map["experience"] = st.select_slider(
            f"Experience Importance (:blue[Currently {reversed_weight_map.get(weights.experience)}])",
            options=reversed_weight_map,
            format_func=reversed_weight_map.get,
            value=weights.experience,
        )

    with col2:
        new_weights_map["seniority_weight"] = st.select_slider(
            f"Seniority Alignment (:blue[Currently {reversed_weight_map.get(weights.seniority_weight)}])",
            options=reversed_weight_map,
            format_func=reversed_weight_map.get,
            value=weights.seniority_weight,
        )

        new_weights_map["retention_risk"] = st.toggle(
            "Enable Retention Risk", value=weights.retention_risk
        )
    save_settings(new_weights_map, "weights", storage)


def scraping_settings_tab(storage: LocalStorage):
    st.subheader("SerpAPI Configuration")
    current_params = st.session_state.pipeline_settings.scraper_settings
    new_params = {}
    new_params["distance_param"] = st.number_input(
        "Search Distance (km)", value=current_params.distance_param, step=5
    )
    regions = ["uk", "us"]
    idx_region = regions.index(current_params.region)
    new_params["region"] = st.selectbox(
        "Search Region",
        options=regions,
        index=idx_region,
        format_func=lambda x: x.upper(),
    )
    save_settings(new_params, "scraper_settings", storage)


def vector_storage_setting_tab(storage: LocalStorage):
    """TODO: Implement GDPR stuff"""
    st.subheader("Vector Store Management")
    st.warning("Pruning the database is permanent. Use with caution.")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Global Raw Jobs", "1,240", delta="+12 today")
        if st.button("Clean Expired Jobs", use_container_width=True):
            st.toast("Checking for expired listings...")

    with col2:
        st.metric(
            "Active User Profiles", f"{len(st.session_state.get('profiles', []))}"
        )
        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("App cache cleared.")


def render_settings_page():
    storage = get_local_storage()
    st.title("⚙️ Pipeline Settings")
    st.markdown("Configure the behavior of the AI agents and data processing pipeline.")
    show_success_toast()
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🧠 Agent Logic", "📡 Scraping", "💾 Database", "🔑 Integrations"]
    )

    with tab1:
        scoring_weights_setting_tab(storage)

    with tab2:
        scraping_settings_tab(storage)

    with tab3:
        vector_storage_setting_tab(storage)

    with tab4:
        render_api_settings(storage)

    st.markdown("---")


def save_settings(new_data: dict, setting_type: str, storage: LocalStorage):
    col_save, col_reset, _ = st.columns([1, 1, 2])
    with col_save:
        if st.button(
            "Save Settings", type="primary", key=f"save_{setting_type}", width="stretch"
        ):
            changes_made = [
                set_new_key(key, value, storage, setting_type)
                for key, value in new_data.items()
            ]
            if any(changes_made):
                st.session_state.updated_setting = True
                st.rerun()

    with col_reset:
        if st.button("Reset to Default", width="stretch", key=f"reset_{setting_type}"):
            reset_setting_to_default_values(setting_type, storage)
            st.session_state.reset_settings = True
            st.rerun()


def show_success_toast():
    if st.session_state.get("changed_api_key"):
        st.toast("Changed AI API Key", icon=":material/api:")
        st.session_state.changed_api_key = False
    if st.session_state.get("changed_provider"):
        st.toast("Changed AI Provider", icon=":material/smart_toy:")
        st.session_state.changed_provider = False
    if st.session_state.get("changed_serpapi"):
        st.toast("Changed SerpAPI API Key", icon=":material/work_alert:")
        st.session_state.changed_serpapi = False
    if st.session_state.get("updated_models"):
        st.toast("Updated Model Configuration", icon=":material/model_training:")
        st.session_state.updated_models = False
    if st.session_state.get("updated_setting"):
        st.toast("Settings Updated", icon=":material/exercise:")
        st.session_state.updated_setting = False

    if st.session_state.get("reset_settings"):
        st.toast("Settings Reset", icon=":material/refresh:")
        st.session_state.reset_settings = False


def hydrate_keys(storage: LocalStorage):
    st.session_state.provider_config = get_provider_config()
    st.session_state.model_roles = get_model_roles()

    new_data_found = False

    keys_to_fetch = ["serpapi_key", "ai_provider", "rapidapi_key", "use_google", "use_linkedin"]
    for provider, item in st.session_state.provider_config.items():
        keys_to_fetch.append(item.get("key"))
        for role in st.session_state.model_roles:
            keys_to_fetch.append(f"{provider.lower()}_{role}")

    for k in keys_to_fetch:
        old_val = getattr(st.session_state.pipeline_settings.api_settings, k, None)
        new_val = get_browser_key(k, storage, "api_settings")

        if new_val and new_val != old_val:
            new_data_found = True

    if new_data_found:
        st.rerun()


def hydrate_settings(setting_type: str, keys: list[str], storage: LocalStorage):
    for key in keys:
        get_browser_key(key, storage, setting_type)


@st.fragment
def render_api_settings(storage: LocalStorage):
    st.subheader("Secrets & API Keys")
    api = st.session_state.pipeline_settings.api_settings

    all_providers = list(st.session_state.provider_config.keys())
    idx = all_providers.index(api.ai_provider) if api.ai_provider in all_providers else 0
    new_provider = st.selectbox("AI Provider", all_providers, index=idx)
    
    config = st.session_state.provider_config[new_provider]
    new_api_key = st.text_input(
        f"{new_provider} API Key",
        type="password",
        value=getattr(api, config["key"]),
        help=f"Get your key from {config['url']}",
    ).strip()

    st.divider()
    st.subheader("Search Provider Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        new_use_google = st.toggle("Enable Google (SerpAPI)", value=api.use_google)
        new_serpapi_key = st.text_input(
            "SerpAPI Key",
            type="password",
            value=api.serpapi_key,
            disabled=not new_use_google,
        ).strip()

    with col2:
        new_use_linkedin = st.toggle("Enable LinkedIn (RapidAPI)", value=api.use_linkedin)
        new_rapidapi_key = st.text_input(
            "RapidAPI Key",
            type="password",
            value=getattr(api, "rapidapi_key", ""),
            disabled=not new_use_linkedin,
            help="Get from 'LinkedIn Job Search API' on RapidAPI",
        ).strip()

    if st.button("Save Settings to Browser", key="set_keys", type="primary"):
        st.session_state.changed_api_key = set_new_key(config["key"], new_api_key, storage, "api_settings")
        st.session_state.changed_provider = set_new_key("ai_provider", new_provider, storage, "api_settings")
        st.session_state.changed_serpapi = set_new_key("serpapi_key", new_serpapi_key, storage, "api_settings")
        
        set_new_key("rapidapi_key", new_rapidapi_key, storage, "api_settings")
        
        set_new_key("use_google", new_use_google, storage, "api_settings")
        set_new_key("use_linkedin", new_use_linkedin, storage, "api_settings")
        
        st.success("Configuration saved! Some changes may require a refresh.")

    st.divider()
    st.write(":red[To see a full list of models, enter your API Key]")
    active_key = getattr(api, config["key"])
    if active_key:
        st.subheader("Select Models")
        free_tier = st.toggle("Show only free tier models", value=api.free_tier)
        model_map = set_models_for_pipeline(new_provider, free_tier)
        if st.button("Save Model Configuration"):
            save_provider_config(new_provider, model_map, storage)
            set_new_key("free_tier", free_tier, storage, "api_settings")
            st.session_state.updated_models = True


def set_models_for_pipeline(new_provider: str, free_tier:bool=False) -> dict:
    api_settings = st.session_state.pipeline_settings.api_settings
    if new_provider == "Gemini" and getattr(api_settings, "gemini_api_key", None):
        all_models = get_model_cache(api_settings.gemini_api_key, free_tier)
        text_models = get_gemini_text_models(all_models, free_tier)
        return get_models_for_pipelines(
            text_models, new_provider.lower()
        )
    # TODO: Implement openai and anthropic
    # if new_provider == "OpenAI" and getattr(api_settings, "openai_api_key", None):
    #     st.header("TODO: Get models")


@st.cache_data
def get_model_cache(api_key: str, free_tier: bool = False):
    return get_all_gemini_models(api_key, free_tier)


def get_models_for_pipelines(
    text_models: list[dict], new_provider: str
):
    api = st.session_state.pipeline_settings.api_settings
    current_reader = getattr(api, f"{new_provider}_reader")
    current_writer = getattr(api, f"{new_provider}_writer")
    current_researcher = getattr(api, f"{new_provider}_researcher")
    if st.toggle("Use different models for the agents?", value=True):
        reader, researcher, writer = st.columns(3)
        with reader:
            reader_model = st.selectbox(
                "Select a CV Parser",
                options=text_models,
                format_func=lambda x: x.get("label").title().replace("-", " "),
                key=f"select_{new_provider}_reader",
                index=get_model_index(text_models, current_reader),
            )
        with researcher:
            researcher_model = st.selectbox(
                "Select a Researcher",
                options=text_models,
                format_func=lambda x: x.get("label").title().replace("-", " "),
                key=f"select_{new_provider}_researcher",
                index=get_model_index(text_models, current_researcher),
            )
        with writer:
            writer_model = st.selectbox(
                "Select an Analyser",
                options=text_models,
                format_func=lambda x: x.get("label").title().replace("-", " "),
                key=f"select_{new_provider}_writer",
                index=get_model_index(text_models, current_writer),
            )
    else:
        reader_model = st.selectbox(
            "Select an Embedder",
            options=text_models,
            format_func=lambda x: x.get("label").title().replace("-", " "),
            key=f"select_{new_provider}_all_nodes",
            index=get_model_index(text_models, current_reader),
        )
        researcher_model = reader_model
        writer_model = researcher_model
    
    return {
        "reader": reader_model.get("id"),
        "writer": writer_model.get("id"),
        "researcher": researcher_model.get("id"),
    }




@st.dialog("New CV")
def cv_handler():
    new_cv = st.file_uploader("Upload a new CV (PDF, DOCX)", type=["pdf", "docx"])

    if new_cv:
        with st.spinner("Extracting text..."):
            text = get_cv_text(new_cv)
            st.session_state.raw_cv_text = text

    if st.session_state.get("raw_cv_text"):
        st.success("CV read successfully!")
        role = st.text_input("Desired Role", value="Data Engineer")
        loc = st.text_input("Desired Location", value="London")

        if st.button("Analyze & Find Jobs"):
            st.session_state.start_processing = True
            st.session_state.desired_role = role
            st.session_state.desired_location = loc
            st.rerun()


def initialise_pipeline_settings():
    """Initializes default settings in session state if not already present."""
    pipeline_settings = st.session_state.get("pipeline_settings")
    if not pipeline_settings or not isinstance(pipeline_settings, PipelineSettings):
        st.session_state.pipeline_settings = PipelineSettings()


def reset_setting_to_default_values(setting: str, storage: LocalStorage):
    if setting == "weights":
        weights = AgentWeights().model_dump()
        for key, value in weights.items():
            set_new_key(key, value, storage, setting)


def init_app():
    initialise_pipeline_settings()
    storage = get_local_storage()
    hydrate_keys(storage)
    hydrate_settings(
        "weights",
        ["key_skills", "seniority_weight", "experience", "retention_risk"],
        storage,
    )
    hydrate_settings(
        "scraper_settings", ["region", "max_results", "distance_param"], storage
    )
    if "last_updated" not in st.session_state:
        st.session_state.last_updated = 0.0
