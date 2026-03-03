import pytest
import json
from unittest.mock import patch, MagicMock

from rich.panel import Panel
from rich.text import Text
from langchain_google_genai import ChatGoogleGenerativeAI

from src.utils.func import get_llm_model, log_message, pretty_print_jobs_with_rich

# --- Tests for get_llm_model ---


def test_get_llm_model():
    model_name = "gemini-1.5-flash"
    with patch("src.utils.func.ChatGoogleGenerativeAI") as mock_chat:
        get_llm_model(model_name)
        # Verify it initializes with the right string
        mock_chat.assert_called_once_with(model=model_name)


# --- Tests for log_message ---


@patch("src.utils.func.get_script_run_ctx")
@patch("src.utils.func.logging.info")
def test_log_message_terminal_only(mock_logging, mock_get_ctx):
    # Simulate being outside Streamlit
    mock_get_ctx.return_value = None

    log_message("Hello Terminal")

    mock_logging.assert_called_once_with("Hello Terminal")
    # If we got here without a crash, the 'if ctx' logic worked


@patch("src.utils.func.st.write")
@patch("src.utils.func.get_script_run_ctx")
def test_log_message_streamlit_context(mock_get_ctx, mock_st_write):
    # Simulate being inside Streamlit
    mock_get_ctx.return_value = MagicMock()

    log_message("Hello Streamlit")

    mock_st_write.assert_called_once_with("Hello Streamlit")


# --- Tests for pretty_print_jobs_with_rich ---


def test_pretty_print_invalid_json():
    with patch("rich.console.Console.print") as mock_rich_print:
        pretty_print_jobs_with_rich("not-json")
        # Verify it prints the red error message
        args, _ = mock_rich_print.call_args_list[0]
        assert "Error:" in str(args[0])


def test_pretty_print_valid_data():
    sample_data = {
        "jobs": [
            {
                "title": "Data Engineer",
                "company": "Tech Solutions",
                "location": "London",
                "office_days": "Hybrid",
                "salary_min": 70000,
                "salary_max": 90000,
                "tech_stack": ["Python", "AWS"],
                "attributes": ["Lead"],
                "job_url": "https://jobs.com/1",
                "top_applicant_score": 95,  # Should be green
                "top_applicant_reasoning": "Perfect match.",
            }
        ]
    }
    json_input = json.dumps(sample_data)

    with patch("rich.console.Console.print") as mock_rich_print:
        pretty_print_jobs_with_rich(json_input)

        # Extract the actual objects passed to console.print
        printed_objects = [call.args[0] for call in mock_rich_print.call_args_list]

        # 1. Check for the Score Text style
        # The score text is constructed as score_text.append(..., style="bold green")
        score_text_found = False
        for obj in printed_objects:
            if isinstance(obj, Text):
                # Text objects store styles in their 'spans'
                if "95%" in obj.plain and any(
                    "green" in str(span.style) for span in obj.spans
                ):
                    score_text_found = True

        # 2. Check for the Panel border style
        # Panel(..., border_style=score_color)
        panel_border_found = any(
            isinstance(obj, Panel) and obj.border_style == "green"
            for obj in printed_objects
        )

        assert score_text_found, "Score should be rendered with green style"
        assert panel_border_found, "Panel border should be green"
