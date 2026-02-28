import logging
import json

import streamlit as st
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm_model(model: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model)

def log_message(message: str):
    """Logs message to terminal or to streamlit depending on context"""
    if st.runtime.exists():
        try:
            st.write(message)
        except Exception as e:
            logging.error(str(e))
            logging.info(f"Errored on: {message}")
    logging.info(message)


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
