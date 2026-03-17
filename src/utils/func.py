import logging
import json
import re
from datetime import datetime
from typing import List, Optional, Any

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.schema import AnalysedJobMatch, RawJobMatch


class APIKeyError(Exception):
    pass


class ModelTypeError(Exception):
    pass


class ProviderError(Exception):
    pass


def validate_configuration(setting, error_message):
    if not setting:
        st.error(f"🚨 {error_message}")
        if st.button("Go to Settings"):
            st.switch_page(
                "pages/7_settings.py"
            )  # Updated to match your folder structure
        st.stop()


def log_message(message: str):
    """Logs message to terminal or to streamlit depending on context."""
    logging.info(message)
    ctx = get_script_run_ctx()
    if ctx:
        try:
            st.write(message)
        except:
            pass


# --- Visualization (CLI/Terminal) ---


def pretty_print_jobs_with_rich(json_data: Any):
    """
    Handles both JSON strings and Pydantic objects for terminal display.
    """
    console = Console()

    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
            jobs = data.get("jobs", [])
        except json.JSONDecodeError:
            console.print("[bold red]Error:[/bold red] Invalid JSON string.")
            return
    else:
        jobs = getattr(json_data, "jobs", [])

    console.print(
        Panel(
            Text("JOB AUDIT INSIGHTS", justify="center", style="bold cyan"),
            box=box.DOUBLE_EDGE,
        )
    )

    for job in jobs:
        get = lambda attr, default=None: (
            getattr(job, attr, default)
            if not isinstance(job, dict)
            else job.get(attr, default)
        )

        title = get("title", "Unknown Title")
        table = Table(
            title=f"[bold magenta]{title}[/bold magenta]", box=box.ROUNDED, expand=True
        )
        table.add_column("Attribute", style="cyan", width=15)
        table.add_column("Details", style="white")

        table.add_row("Company", get("company", "N/A"))
        table.add_row("Location", get("location", "N/A"))

        salary_min = get("salary_min")
        salary_max = get("salary_max")
        table.add_row("Salary", format_salary_as_range(salary_min, salary_max))

        skills = get("key_skills", [])
        table.add_row(
            "Tech Stack", ", ".join(skills) if isinstance(skills, list) else "N/A"
        )

        link = get("job_url", "#")
        table.add_row("Listing", f"[link={link}]View URL[/link]")

        console.print(table)

        score = get("top_applicant_score", 0)
        color = "green" if score >= 85 else "yellow" if score >= 70 else "red"

        score_text = Text()
        score_text.append("\nAUDITOR MATCH SCORE: ", style="bold")
        score_text.append(f"{score}%", style=f"bold {color}")
        console.print(score_text)
        console.print(Panel(get("top_applicant_reasoning", ""), border_style=color))
        console.print("\n")


def format_salary_as_range(salary_min: Optional[int], salary_max: Optional[int]) -> str:
    if salary_min and salary_max:
        return f"£{salary_min:,} - £{salary_max:,}"
    if salary_max:
        return f"Up to £{salary_max:,}"
    if salary_min:
        return f"From £{salary_min:,}"
    return "Salary not specified"


def iso_formatter(option: Any) -> str:
    if not option:
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(option))
        return dt.strftime("%d %b %H:%M")
    except:
        return str(option)


def normalize(text: str) -> str:
    if not text:
        return ""
    return str(text).title().replace("-", " ").strip()


def get_job_val(job: Any, fields: List[str], default: Any = None) -> Any:
    """Helper to try multiple field names on a Pydantic object or dict."""
    for field in fields:
        val = getattr(job, field, None) if not isinstance(job, dict) else job.get(field)
        if val is not None:
            return val
    return default


def filter_jobs_by_keywords(
    jobs: List[AnalysedJobMatch], keywords: List[str]
) -> List[Any]:
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
                " ".join(getattr(job, "key_skills", []) or []),
            ]
        ).lower()

        if any(kw in searchable_text for kw in lower_keywords):
            filtered.append(job)
    return filtered


def sort_analysed_job_matches_with_meta(jobs: List[Any], sort_by: str) -> List[Any]:
    sort_map = {
        "Score": "top_applicant_score",
        "Analysis Date": "analysed_at",
        "Company": "company",
        "Role": "title",
    }
    attr = sort_map.get(sort_by, sort_by)
    reverse = attr in ["top_applicant_score", "analysed_at"]

    is_date_sort = any(word in sort_by for word in ["date", "at"])
    safe_default = "" if is_date_sort else 0

    jobs.sort(
        key=lambda x: get_job_val(x, [attr], default=safe_default), reverse=reverse
    )

    return jobs


def sort_raw_job_matches_with_meta(
    jobs: List[RawJobMatch], sort_by: str
) -> List[RawJobMatch]:
    sort_map = {"Posted Date": "posted_at", "Company": "company_name", "Role": "title"}
    attr = sort_map.get(sort_by, sort_by)
    reverse = attr == "posted_at"
    jobs.sort(
        key=lambda x: (
            (getattr(x, attr) or "") if not isinstance(x, dict) else (x.get(attr) or "")
        ),
        reverse=reverse,
    )
    return jobs


def get_weight_map() -> dict:
    return {"None": 0, "Minimal": 25, "Moderate": 50, "High": 75, "Critical": 100}


def get_provider_config() -> dict:
    return {
        "Gemini": {"key": "gemini_api_key", "url": "https://aistudio.google.com/"},
        "OpenAI": {"key": "openai_api_key", "url": "https://platform.openai.com/"},
        "Anthropic": {
            "key": "anthropic_api_key",
            "url": "https://console.anthropic.com/",
        },
    }


def get_model_roles() -> List[str]:
    return ["reader", "writer", "researcher"]


def show_success_toast():
    """
    Checks session state flags and displays temporary
    success messages to the user.
    """
    if st.session_state.get("changed_api_key"):
        st.toast("API Key Updated", icon="🔑")
        st.session_state.changed_api_key = False

    if st.session_state.get("updated_setting"):
        st.toast("Settings Saved", icon="✅")
        st.session_state.updated_setting = False

    if st.session_state.get("reset_settings"):
        st.toast("Settings Reset to Defaults", icon="🔄")
        st.session_state.reset_settings = False

    if st.session_state.get("updated_models"):
        st.toast("Model Configuration Updated", icon="🤖")
        st.session_state.updated_models = False
