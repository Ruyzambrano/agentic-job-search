import logging
import json
from os import environ as ENV
from typing import Literal
from datetime import datetime
import re

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


from src.schema import AnalysedJobMatch, AnalysedJobMatchWithMeta, RawJobMatch


class APIKeyError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class ModelTypeError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class ProviderError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


def validate_configuration(setting, error_message):
    if not setting:
        st.error(f"🚨 {error_message}")
        if st.button("Go to Settings"):
            st.switch_page("pages/settings.py")
        st.stop()


def log_message(message: str):
    """Logs message to terminal or to streamlit depending on context"""
    logging.info(message)
    ctx = get_script_run_ctx(True)
    if ctx:
        try:
            st.write(message)
        except Exception:
            pass


def pretty_print_jobs_with_rich(json_string):
    """Uses rich library to print to terminal"""
    console = Console()
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError:
        console.print("[bold red]Error:[/bold red] Invalid JSON string.")
        return

    if not data:
        console.print("[bold red]Error:[/bold red] JSON string shape is wrong:")
        console.print_json(data)

    console.print(
        Panel(
            Text(
                "JOB LISTINGS & APPLICANT INSIGHTS", justify="center", style="bold cyan"
            ),
            box=box.DOUBLE_EDGE,
        )
    )

    for job in data.get("jobs", []):
        table = Table(
            title=f"[bold magenta]{job['title']}[/bold magenta]",
            title_justify="left",
            box=box.ROUNDED,
            expand=True,
        )

        table.add_column("Attribute", style="cyan", width=15)
        table.add_column("Details", style="white")

        table.add_row("Company", job["company"])
        table.add_row("Location", f"{job['location']} ({job['office_days']})")
        salary_parts = [
            f"{s:,}"
            for s in [job.get("salary_min"), job.get("salary_max")]
            if s is not None
        ]
        salary_display = (
            f"£{' - £'.join(salary_parts)}" if salary_parts else "Not Specified"
        )
        table.add_row("Salary", salary_display)
        tech_display = (
            ", ".join(job["tech_stack"])
            if isinstance(job["tech_stack"], list)
            else "N/A"
        )
        table.add_row("Tech Stack", tech_display)
        attributes_display = (
            " • ".join(job["attributes"])
            if isinstance(job["attributes"], list)
            else "N/A"
        )
        table.add_row("Attributes", attributes_display)
        link_text = f"[link={job['job_url']}]Click to view job listing[/link]"
        table.add_row("Listing", link_text)

        console.print(table)

        # Applicant Scoring Section
        score = job["top_applicant_score"]
        score_color = "green" if score >= 85 else "yellow" if score >= 70 else "red"

        score_text = Text()
        score_text.append("\nTOP APPLICANT MATCH: ", style="bold")
        score_text.append(f"{score}%", style=f"bold {score_color}")

        console.print(score_text)
        console.print(
            Panel(
                job["top_applicant_reasoning"],
                title="Match Reasoning",
                title_align="left",
                border_style=score_color,
            )
        )

        console.print("\n")


def get_active_api_key() -> str:
    user_override = st.session_state.get("CUSTOM_API_KEY")
    if user_override:
        return user_override

    secret_key = st.secrets.get("GEMINI_API_KEY")
    if secret_key:
        return secret_key

    fallback_api_key = ENV.get("GEMINI_API_KEY")
    if fallback_api_key:
        return fallback_api_key
    raise APIKeyError("No AI API key!")


def get_model(model_type: str, provider: Literal["GEMINI", "OPEN_AI"]) -> str:
    user_override = st.session_state.get(f"CUSTOM_{model_type}_MODEL")
    if user_override:
        return user_override
    model_string = f"{model_type}_{provider}_MODEL".upper()
    secret_key = st.secrets.get(model_string)
    if secret_key:
        return secret_key

    fallback_model = ENV.get(model_string)
    if fallback_model:
        return fallback_model
    raise ModelTypeError("No model set")


def format_salary_as_range(salary_min: int, salary_max: int):
    if salary_min and salary_max:
        return f"£{salary_min:,} - £{salary_max:,}"
    if salary_max:
        return f"£{salary_max:,}"
    if salary_min:
        return f"{salary_min:,}"
    return "Salary not specified"


def iso_formatter(option: datetime):
    """Makes an ISO string human readable"""
    try:
        dt = datetime.fromisoformat(option)
        return dt.strftime("%d %b %H:%M")
    except:
        return option


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


def get_colour_map(score: int) -> str:
    """Not used anymore?"""
    if score > 85:
        return "green"
    if score > 70:
        return "orange"
    return "red"


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


def get_weight_map():
    return {"None": 0, "Minimal": 25, "Moderate": 50, "High": 75, "Critical": 100}


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
    jobs: list[RawJobMatch], sort_by
) -> list[AnalysedJobMatchWithMeta]:
    sort_map = {"Posted Date": "posted_at", "Company": "company_name", "Role": "title"}

    target_attr = sort_map.get(sort_by, sort_by)

    reverse = target_attr == "posted_at"
    jobs.sort(key=lambda x: getattr(x, target_attr), reverse=reverse)
    return jobs


def extract_base_locations(location_str: str) -> list[str]:
    """
    Splits 'London / Hybrid / Telford' into ['London', 'Telford']
    and removes parentheticals like '(Remote)'.
    """
    if not location_str:
        return []

    normalized = location_str.replace("/", "|").replace(",", "|")

    parts = [p.strip() for p in normalized.split("|")]

    clean_cities = []
    for p in parts:
        p_clean = re.sub(r"[\(\[].*?[\)\]]", "", p)
        p_clean = p_clean.replace("(", "").replace(")", "").strip()
        if "remote" in p_clean.lower():
            clean_cities.append("Remote")
        elif "hybrid" in p_clean.lower():
            clean_cities.append("Hybrid")
        elif "flexible" in p_clean.lower():
            clean_cities.append("Flexible")
        elif len(p_clean) > 2:
            clean_cities.append(p_clean.title())

    return sorted(list(set(clean_cities)))


def validate_ai_api_key(api_key: str) -> bool: ...


def get_provider_config() -> dict:
    return {
        "Gemini": {"key": "gemini_api_key", "url": "Google AI Studio"},
        "OpenAI": {"key": "openai_api_key", "url": "OpenAI Dashboard"},
        "Anthropic": {"key": "anthropic_api_key", "url": "Anthropic Console"},
    }


def get_model_roles() -> list[str]:
    return ["reader", "writer", "researcher"]
