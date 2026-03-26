import re
from datetime import datetime

import streamlit as st
from streamlit_tags import st_tags
from streamlit_local_storage import LocalStorage
from html2text import html2text

from src.utils.text_processing import extract_base_locations
from src.utils.local_storage import get_local_storage, set_new_key, save_provider_config
from src.ui.streamlit_cache import get_cv_text, get_cached_stats
from src.ui.controllers import handle_profile_deletion, set_models_for_pipeline
from src.utils.func import (
    sort_analysed_job_matches_with_meta,
    format_salary_as_range,
    sort_raw_job_matches_with_meta,
    get_job_val,
    normalize,
    filter_jobs_by_keywords,
    get_weight_map,
)
from src.services.storage_service import StorageService
from src.schema import AnalysedJobMatchWithMeta, RawJobMatch, AgentWeights


def display_profile(profile):
    st.title(f"👤 {profile.get('full_name')}")
    st.info(profile.get("summary"))
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.expander("Previous Roles", expanded=False):
            st.write(f"- {'\n- '.join(profile.get('job_titles', []))}")
    with col2:
        with st.expander("Key Skills", expanded=False):
            st.write(f"- {'\n- '.join(profile.get('key_skills', []))}")
    with col3:
        with st.expander("Industries", expanded=False):
            st.write(f"- {'\n- '.join(profile.get('industries', []))}")


def display_job_matches(job_matches, sort_by="Score"):
    job_matches = sort_analysed_job_matches_with_meta(job_matches, sort_by)
    col1, col2 = st.columns(2)
    for i, job in enumerate(job_matches):
        with col1 if i % 2 == 0 else col2:
            display_job_match(job)


def display_job_match(job: AnalysedJobMatchWithMeta):
    with st.container(border=True):
        col_header, col_score = st.columns([4, 2])
        with col_header:
            st.markdown(f"### {job.title}")
            role_string = f"**{job.company}** | {job.location}"
            if job.work_setting.value != "Remote Unknown":
                role_string += f" | {job.work_setting.value}"
            st.markdown(role_string)
            meta_labels = []
            if job.is_contract:
                meta_labels.append(":red[Contract]")
            if job.seniority_level != "Not specified":
                meta_labels.append(f"_{job.seniority_level.value}_")

            if meta_labels:
                st.markdown(" · ".join(meta_labels))

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
            chips = " · ".join([f"_{tech}_" for tech in job.key_skills[:5]])
            st.markdown(f":blue[{chips}]")

        if st.button(
            "View Full Analysis & Details",
            key=f"view_{job.job_url}",
            use_container_width=True,
        ):
            st.session_state.current_job = job
            st.switch_page("pages/4_job_view.py")
        st.link_button("Apply for this role", url=job.job_url, use_container_width=True)


def display_full_job(full_job: AnalysedJobMatchWithMeta, current_job: RawJobMatch):
    col_header, col_score = st.columns([3, 1])
    
    with col_header:
        st.markdown(f"<h1>{current_job.title}</h1>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='color: #94A3B8; font-size: 16px; font-family: Inter, sans-serif; letter-spacing: 0.05em;'>"
            f"{current_job.company.upper()} &nbsp; | &nbsp; {current_job.location.upper()}</p>", 
            unsafe_allow_html=True
        )

    with col_score:
        score = current_job.top_applicant_score
        
        # 🎨 THE DISTINCT METALLIC RAG
        if score >= 85:
            # High: Deep Polished Gold
            color = "#D4AF37" 
            label = "EXCEPTIONAL"
            bg_tint = "rgba(212, 175, 55, 0.1)"
        elif score >= 70:
            # Mid: Cold Platinum / Champagne Silver (VERY DISTINCT FROM GOLD)
            color = "#E5E7EB" 
            label = "COMPATIBLE"
            bg_tint = "rgba(229, 231, 235, 0.08)"
        else:
            # Low: Deep Oxidized Copper (Vivid enough to see 'Red')
            color = "#FF7654" 
            label = "LOW MATCH"
            bg_tint = "rgba(255, 118, 84, 0.05)"

        st.markdown(
            f"""
            <div style="
                text-align: center; 
                border: 1px solid {color}; 
                background-color: {bg_tint};
                backdrop-filter: blur(10px);
                border-radius: 2px; 
                padding: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            ">
                <div style="font-size: 10px; letter-spacing: 2px; color: #94A3B8; font-weight: 700; text-transform: uppercase; margin-bottom: 8px;">
                    {label}
                </div>
                <div style="font-size: 46px; font-weight: 400; font-family: 'Playfair Display', serif; color: {color}; text-shadow: 0 2px 10px rgba(0,0,0,0.8);">
                    {score}%
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown("### 📝 Job Summary")
        st.info(current_job.job_summary)

        reasoning = current_job.top_applicant_reasoning

        parts = re.split(r"(?i)gap[s]?:", reasoning)

        with st.container(border=True):
            if len(parts) >= 2:
                why_text = re.sub(r"(?i)why:", "", parts[0]).strip()
                gap_text = parts[1].strip()

                st.markdown("### ✅ Why You're a Great Fit")
                st.write(why_text)

                st.divider()

                st.markdown("### 🚨 Gaps In Your Profile")
                st.write(gap_text)

            elif "Why:" in reasoning or "WHY:" in reasoning:
                why_text = re.sub(r"(?i)why:", "", reasoning).strip()

                st.markdown("#### ✅ Why You're a Great Fit")
                st.write(why_text)

                st.divider()
                st.markdown("#### 🚨 Gaps In Your Profile")
                st.success("No significant gaps detected for this role.")

            else:
                st.write("### 📝 Profile Analysis")
                st.write(reasoning)

        st.markdown("### 🛠 Skill Stack")
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
            current_job.job_url,
            use_container_width=True,
            type="primary",
        )
        with st.expander("💰 Financials & Schedule", expanded=True):
            st.write(
                f"**Salary Range:** {format_salary_as_range(current_job.salary_min, current_job.salary_max)}"
            )
            st.write(f"**Contract Type:** {" | ".join(current_job.attributes)}")
            st.write(f"**In-Office Policy:** {current_job.office_days}")

        with st.expander("📍 Requirements Checklist", expanded=True):
            for q in current_job.qualifications:
                st.write(f"✅ {q}")

        st.caption(
            f"Job found at: {datetime.fromisoformat(current_job.analysed_at).strftime("%d/%m/%Y %H:%M")}"
        )

    if hasattr(full_job, "description") and full_job.description:
        st.subheader("Job Description")
        with st.container(border=True):
            st.write(format_raw_job_description(full_job))


def format_raw_job_description(raw_job: RawJobMatch) -> str:
    """
    Standardizes raw text or HTML into clean, high-fidelity Markdown.
    Optimized for Reed/LinkedIn 'noisy' descriptions.
    """
    description = raw_job.description or ""
    
    if any(tag in description for tag in ["<p>", "<h1>", "<li>", "<ul>"]):
        return html2text(description)
    
    lines = [
        line.strip()
        for line in description.split("\n")
        if line.strip() and not re.match(r"^#J-\d+-[A-Za-z]+$", line.strip())
    ]

    company_clean = raw_job.company.lower()
    title_clean = raw_job.title.lower()
    formatted_output = []

    header_keywords = [
        "responsibilities", "nice to have", "required skills",
        "practical information", "the role", "about us", "soft skills",
        "about the role", f"about {company_clean.split()[0]}",
        "requirements", "benefits", "environment", "who you are"
    ]
    formatted_output.append(f"### {lines.pop(0)}")

    for line in lines:        
        lower_line = line.lower()
        st.write(line)
        is_header = (
            (any(key == lower_line for key in header_keywords)) or
            (any(key in lower_line for key in header_keywords) and len(line) < 40) or
            (company_clean in lower_line and len(line) < 50) or
            (title_clean in lower_line and len(line) < 25)
        )

        if is_header:
            formatted_output.append(f"\n#### {line.upper() if len(line) < 20 else line.title()}")
            
        elif line.startswith(("•", "·", "-", "*", "–")):
            content = re.sub(r"^[•·\-\*–]\s*", "", line).strip()
            formatted_output.append(f"* {content}")
            
        elif ":" in line and len(line.split(":")[0]) < 15:
            key, val = line.split(":", 1)
            formatted_output.append(f"**{key.strip()}:** {val.strip()}")
            
        else:
            formatted_output.append(line)

    return "\n\n".join(formatted_output)

def render_sidebar_feed(jobs: list[AnalysedJobMatchWithMeta], subheader, sort_by: str):
    jobs = sort_analysed_job_matches_with_meta(jobs, sort_by)
    
    current_selection = st.session_state.get("current_job")
    selected_url = current_selection.job_url if current_selection else None

    with st.sidebar:
        st.subheader("🎯 Matched Roles")
        st.caption(f"Showing {len(jobs)} opportunities")

        for job in jobs:
            is_selected = "secondary"
            if selected_url == job.job_url:
                is_selected = "primary"
            
            button_label = f"{job.title} \n\n {job.company} \n\n {job.top_applicant_score}% Match"
            if st.button(
                button_label,
                key=f"btn_{job.job_url}_{job.analysed_at}",
                use_container_width=True,
                type=is_selected,
            ):
                st.session_state.current_job = job
                st.rerun()


def display_raw_job_matches(jobs, sort_by):
    jobs = sort_raw_job_matches_with_meta(jobs, sort_by)
    col1, col2 = st.columns(2)
    for i, job in enumerate(jobs):
        with col1 if i % 2 == 0 else col2:
            display_raw_job_card(job)


def display_raw_job_card(job: RawJobMatch):
    """Displays a single raw job listing with metadata badges."""
    with st.container(border=True):
        card_id = f"{job.job_url}"
        col_title, col_meta = st.columns([4, 2])

        with col_title:
            st.markdown(f"### {job.title}")
            st.markdown(f"**{job.company}** | {job.location}")

            setting_emoji = "🏠" if job.work_setting.value == "Remote" else "🏢"
            badges = f"{setting_emoji} `{job.work_setting.value}` · 📅 `{job.schedule_type}`".title().replace(
                "_", "-"
            )
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

        salary_display = "Not Specified"
        if job.salary_min and job.salary_max:
            salary_display = f"£{job.salary_min:,} - £{job.salary_max:,}"
        elif job.salary_string:
            salary_display = job.salary_string
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


def jobs_filter_sidebar(jobs: list):
    with st.sidebar:
        keywords = st_tags(
            label="Keyword Match", suggestions=["Data", "AI", "Langchain", "Python"]
        )

        all_base_cities = set()
        for job in jobs:
            all_base_cities.update(extract_base_locations(job.location))
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

        UI_STABLE_MAX = 500_000
        stable_options = list(range(0, UI_STABLE_MAX + 5000, 5000))

        st.select_slider(
            label="Salary Range",
            options=stable_options,
            value=(0, UI_STABLE_MAX),
            key="salary_range",
            format_func=lambda x: f"£{x:,}"
        )
        
        min_salary, max_salary = st.session_state.salary_range

        all_tech = set()
        for job in jobs:
            skill_data = get_job_val(job, ["key_skills", "qualifications"], [])
            if isinstance(skill_data, list):
                all_tech.update(skill_data)
        selected_tech = st.multiselect("Tech Stack", options=sorted(list(all_tech)))

        filtered = filter_jobs_by_keywords(jobs, keywords)

        if selected_cities:
            filtered = [
                j for j in filtered
                if any(c.lower() in (j.location or "").lower() for c in selected_cities)
            ]

        if selected_companies:
            filtered = [
                j for j in filtered
                if get_job_val(j, ["company", "company_name"]) in selected_companies
            ]

        if selected_attributes:
            norm_sel = [normalize(a) for a in selected_attributes]
            filtered = [
                j for j in filtered
                if any(normalize(v) in norm_sel for v in (
                    getattr(j, "attributes", []) or 
                    [getattr(j, "schedule_type", ""), getattr(j, "work_setting", "")]
                ))
            ]

        if selected_tech:
            filtered = [
                j for j in filtered
                if all(t in get_job_val(j, ["key_skills", "qualifications"], []) for t in selected_tech)
            ]

        final = []
        for j in filtered:
            if j.salary_min is None and j.salary_max is None:
                final.append(j) 
                continue

            j_min = j.salary_min if j.salary_min is not None else 0
            j_max = j.salary_max if j.salary_max is not None else j_min
            
            if j_max >= min_salary and j_min <= max_salary:
                final.append(j)

        return final

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
    depth_labels = {
        5: "Light",
        10: "Balanced",
        20: "Moderate",
        30: "Deep",
        50: "Exhaustive",
    }
    new_params["max_jobs"] = st.select_slider(
        label="Search Depth (Total Jobs)",
        options=depth_labels,
        format_func=depth_labels.get,
        value=current_params.max_jobs,
    )
    save_settings(new_params, "scraper_settings", storage)


def vector_storage_setting_tab(storage: LocalStorage):
    st.subheader("Vector Store Management")
    st.warning("Pruning the database is permanent. Use with caution.")

    stats = get_cached_stats(storage, st.session_state.last_updated)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="Global Raw Jobs", 
            value=f"{stats['global_count']:,}", 
            help="Total unique job descriptions cached in the global library."
        )
        if st.button("Refresh Library Stats", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with col2:
        st.metric(
            label="Total AI Analyses", 
            value=f"{stats['analysis_count']:,}",
            help="Total number of jobs analyzed across all candidate profiles."
        )
        if st.button("Clear App Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Local cache cleared.")

    if st.user and st.user.email == st.secrets.admin.root:
        st.divider()
        st.markdown("### 👑 Admin Infrastructure Tools")
        st.caption("These actions affect the shared Pinecone Index (Global).")

        admin_col1, admin_col2 = st.columns(2)
        
        with admin_col1:
            st.number_input("How many months?", min_value=0, format="%d")
            if st.button("🗑️ Purge Stale Jobs", use_container_width=True, type="secondary"):
                with st.spinner("Deleting old global records..."):
                    result = storage.cleanup_stale_jobs(months_old=6)
                    if result:
                        st.success(f"{len(result)} stale jobs purged successfully.")
                    else:
                        st.info("No stale jobs found")
        
        with admin_col2:
            st.space("large")
            if st.button("🧹 Scrub Contaminated URLs", use_container_width=True, type="secondary"):
                with st.spinner("Scanning for ID/URL mismatches..."):
                    msg = storage.scrub_id_contaminated_urls(storage.NS_GLOBAL_JOBS)
                    st.toast(msg)
                    
                    msg_user = storage.scrub_id_contaminated_urls(storage.NS_USER_DATA)
                    st.success(f"Global: {msg} | User Data: {msg_user}")


@st.fragment
def render_api_settings(storage: LocalStorage):
    st.subheader("Secrets & API Keys")
    api = st.session_state.pipeline_settings.api_settings

    all_providers = list(st.session_state.provider_config.keys())
    idx = (
        all_providers.index(api.ai_provider) if api.ai_provider in all_providers else 0
    )
    new_provider = st.selectbox("AI Provider", all_providers, index=idx)

    config = st.session_state.provider_config[new_provider]
    new_api_key = st.text_input(
        f"{new_provider} API Key",
        type="password",
        value=getattr(api, config["key"]),
        help=f"Get your key from {config['url']}",
    ).strip()

    if st.button("Save API Key to Browser", key="set_api_keys", type="primary"):
        st.session_state.changed_api_key = set_new_key(
            config["key"], new_api_key, storage, "api_settings"
        )
        st.session_state.changed_provider = set_new_key(
            "ai_provider", new_provider, storage, "api_settings"
        )

    st.divider()
    st.subheader("Search Provider Settings")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            new_use_reed = st.toggle("Enable Reed", value=api.use_reed)
            new_reed_key = st.text_input(
                "Reed API Key",
                type="password",
                value=api.reed_key,
                disabled=not new_use_reed,
            ).strip()

        with st.container(border=True):
            new_use_google = st.toggle("Enable Google (SerpAPI)", value=api.use_google)
            new_serpapi_key = st.text_input(
                "SerpAPI Key",
                type="password",
                value=api.serpapi_key,
                disabled=not new_use_google,
            ).strip()

        with st.container(border=True):
            new_use_theirstack = st.toggle("Enable TheirStack", value=api.use_theirstack)
            new_theirstack_key = st.text_input(
                "TheirStack Key",
                type="password",
                value=api.theirstack_key,
                disabled=not new_use_theirstack,
            ).strip()

    with col2:
        with st.container(border=True):
            new_use_linkedin = st.toggle(
                "Enable LinkedIn (RapidAPI)", value=api.use_linkedin
            )
            new_rapidapi_key = st.text_input(
                "RapidAPI Key",
                type="password",
                value=getattr(api, "rapidapi_key", ""),
                disabled=not new_use_linkedin,
                help="Get from 'LinkedIn Job Search API' on RapidAPI",
            ).strip()

        with st.container(border=True):
            new_use_indeed = st.toggle(
                "Enable Indeed (HasData)", value=api.use_indeed
            )
            new_hasdata_key = st.text_input(
                "HasData API Key",
                type="password",
                value=getattr(api, "indeed_key", ""),
                disabled=not new_use_indeed,
                help="Get from 'LinkedIn Job Search API' on RapidAPI",
            ).strip()

    if st.button("Save Settings to Browser", key="set_keys", type="primary"):
        st.session_state.changed_serpapi = set_new_key(
            "serpapi_key", new_serpapi_key, storage, "api_settings"
            )

        st.session_state.changed_rapid_api = set_new_key(
            "rapidapi_key", new_rapidapi_key, storage, "api_settings"
            )
        st.session_state.changed_reed = set_new_key(
            "reed_key", new_reed_key, storage, "api_settings"
        )
        st.session_state.changed_indeed = set_new_key(
            "indeed_key", new_hasdata_key, storage, "api_settings"
        )
        st.session_state.changed_theirstack = set_new_key(
            "theirstack_key", new_theirstack_key, storage, "api_settings"
        )

        st.session_state.changed_use_google = set_new_key("use_google", new_use_google, storage, "api_settings")
        st.session_state.changed_use_linkedin = set_new_key("use_linkedin", new_use_linkedin, storage, "api_settings")
        st.session_state.changed_use_reed = set_new_key("use_reed", new_use_reed, storage, "api_settings")
        st.session_state.changed_use_indeed = set_new_key("use_indeed", new_use_indeed, storage, "api_settings")
        st.session_state.changed_use_theirstack = set_new_key("use_theirstack", new_use_theirstack, storage, "api_settings")

        if any([
            st.session_state.get("changed_serpapi"),
            st.session_state.get("changed_rapid_api"),
            st.session_state.get("changed_reed"),
            st.session_state.get("changed_theirstack"),
            st.session_state.get("changed_use_google"),
            st.session_state.get("changed_use_linkedin"),
            st.session_state.get("changed_use_reed"),
            st.session_state.get("changed_use_theirstack")]
        ):
            st.success("Configuration saved! Some changes may require a refresh.")

    st.divider()
    st.write(":red[To see a full list of models, enter your API Key]")
    active_key = getattr(api, config["key"])
    if active_key:
        st.subheader("Select Models")
        free_tier = st.toggle("Show only free tier models", value=api.free_tier)
        model_map = set_models_for_pipeline(new_provider, free_tier)
        if st.button("Save Model Configuration", type="primary"):
            save_provider_config(new_provider, model_map, storage)
            set_new_key("free_tier", free_tier, storage, "api_settings")
            api.models[new_provider.lower()] = model_map
            st.session_state.updated_models = True


def render_settings_page():
    storage = get_local_storage()
    storage_service = st.session_state.storage_service
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🧠 Logic", "📡 Scraping", "💾 Database", "🔑 API"]
    )
    with tab1:
        scoring_weights_setting_tab(storage)
    with tab2:
        scraping_settings_tab(storage)
    with tab3:
        vector_storage_setting_tab(storage_service)
    with tab4:
        render_api_settings(storage)


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

    with col_reset:
        if st.button("Reset to Default", width="stretch", key=f"reset_{setting_type}"):
            reset_setting_to_default_values(setting_type, storage)
            st.session_state.reset_settings = True


def reset_setting_to_default_values(setting: str, storage: LocalStorage):
    if setting == "weights":
        weights = AgentWeights().model_dump()
        for key, value in weights.items():
            set_new_key(key, value, storage, setting)


@st.dialog("New CV")
def cv_handler():
    file = st.file_uploader("Upload CV", type=["pdf", "docx"])
    if file:
        st.session_state.raw_cv_text = get_cv_text(file, st.session_state.last_updated)
        st.success("CV Loaded!")


@st.dialog("Delete Profile")
def delete_profile_dialogue(store, profile_id):
    if st.button("Confirm Deletion"):
        store.delete_profile(profile_id)
        st.rerun()


def display_profile_management(storage, active_profile):
    """Component: UI for profile actions like deletion."""
    if not active_profile:
        return
    with st.sidebar:
        with st.expander("⚠️ Profile Management"):
            st.warning("Deleting this profile is permanent.")
            if st.button(
                f"Delete {active_profile['full_name']}",
                use_container_width=True,
                type="primary",
            ):
                if handle_profile_deletion(storage, active_profile["profile_id"]):
                    st.rerun()

def add_sidebar_support():
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 0px;">
                <p style="font-size: 0.85rem; color: #888; margin-bottom: 0px;">Enjoying the Pipeline?</p>
                <a href="https://ko-fi.com/yourusername" target="_blank" style="padding-bottom:12px">
                    <img src="https://ko-fi.com/img/githubbutton_sm.svg" style="height: 32px;" alt="Support me on Ko-fi" />
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

def show_how():
    """Redirects users to setup or info pages if keys are missing."""
    st.image("https://img.icons8.com/layers/100/000000/empty-box.png", width=100)
    st.title("Ready to start your research?")
    st.subheader("The pipeline is currently dormant.")
    
    st.info("""
    **Notice:** This is a **Bring Your Own Key (BYOK)** tool. 
    To protect your privacy and ensure dedicated performance, you must provide your own LLM and Search API keys.
    """)

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("### 📖 New here?")
            st.write("Learn how the 'Auditor' logic works and what keys you'll need to get started.")
            if st.button("Read the Guide", width="stretch"):
                st.switch_page("pages/2_about.py")
                
    with col2:
        with st.container(border=True):
            st.markdown("### ⚙️ Already have keys?")
            st.write("Jump straight to the settings to input your API keys and initialize the engine.")
            if st.button("Go to Settings", type="primary", width="stretch"):
                st.switch_page("pages/7_settings.py")

    st.divider()
    
    with st.expander("Why do I need my own keys?", expanded=False):
        st.write("""
        1. **Privacy:** Your CV data stays within your own API logs.
        2. **Cost:** You only pay for what you use directly to providers like Google, OpenAI or Anthropic.
        3. **Reliability:** You don't share rate limits with other users of this tool.
        """)