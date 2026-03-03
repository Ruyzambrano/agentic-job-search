import logging
import json
from os import environ as ENV
from typing import Literal

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

class APIKeyError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class ModelTypeError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class ProviderError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model=ENV.get("EMBEDDING_MODEL"))

def get_llm_model(model_type: str) -> ChatGoogleGenerativeAI:
    """Allows user to define different models for each step of the pipeline"""
    provider = get_provider()
    api_key = get_active_api_key()
    ai_model = get_model(model_type, provider)
    # TODO: Add options for OpenAI / Claude 
    return ChatGoogleGenerativeAI(model=ai_model,
                                  api_key=api_key)


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

def get_provider() -> str:
    user_override = st.session_state.get("PROVIDER")
    if user_override:
        return user_override
    
    provider = st.secrets.get("PROVIDER")
    if provider:
        return provider
    
    fallback_provider = ENV.get("PROVIDER")
    if fallback_provider:
        return fallback_provider
    raise ProviderError("No provider set")


def get_serpapi_key() -> str:
    user_override = st.session_state.get("SERPAPI_KEY")
    if user_override:
        return user_override
    
    api_key = st.secrets.get("SERPAPI_KEY")
    if api_key:
        return api_key
    
    fallback_key = ENV.get("SERPAPI_KEY")
    if fallback_key:
        return fallback_key
    raise APIKeyError("No serpAPI key!")