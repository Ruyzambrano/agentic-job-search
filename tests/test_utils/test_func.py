import pytest
import json
from unittest.mock import patch, MagicMock

from rich.panel import Panel
from rich.text import Text
from langchain_google_genai import ChatGoogleGenerativeAI

from src.utils.func import (log_message, 
                            pretty_print_jobs_with_rich,
                            get_active_api_key, 
                            get_model, 
                            get_provider, 
                            get_serpapi_key, 
                            APIKeyError, 
                            ModelTypeError, 
                            ProviderError
                        )




def test_get_api_key_priority(mock_streamlit, mock_env):
    session, secrets, env = mock_streamlit[0], mock_streamlit[1], mock_env
    
    # 1. Test ENV fallback
    env["GEMINI_API_KEY"] = "env_key"
    assert get_active_api_key() == "env_key"
    
    # 2. Test Secrets override Env
    secrets["GEMINI_API_KEY"] = "secret_key"
    assert get_active_api_key() == "secret_key"
    
    # 3. Test Session State override everything
    session["CUSTOM_API_KEY"] = "user_key"
    assert get_active_api_key() == "user_key"

def test_get_api_key_raises_error(mock_streamlit, mock_env):
    # Ensure it raises APIKeyError when nothing is set
    with pytest.raises(APIKeyError, match="No AI API key!"):
        get_active_api_key()

# --- TESTS FOR get_model ---

def test_get_model_logic(mock_streamlit, mock_env):
    session, secrets, env = mock_streamlit[0], mock_streamlit[1], mock_env
    
    # Testing dynamic string construction: RESEARCH_GEMINI_MODEL
    env["RESEARCH_GEMINI_MODEL"] = "gemini-pro"
    assert get_model("RESEARCH", "GEMINI") == "gemini-pro"
    
    # User override in session state
    session["CUSTOM_RESEARCH_MODEL"] = "gemini-ultra"
    assert get_model("RESEARCH", "GEMINI") == "gemini-ultra"

def test_get_model_raises_error(mock_streamlit, mock_env):
    with pytest.raises(ModelTypeError):
        get_model("WRITER", "OPEN_AI")

# --- TESTS FOR get_provider ---

def test_get_provider_priority(mock_streamlit, mock_env):
    session, secrets, env = mock_streamlit[0], mock_streamlit[1], mock_env
    
    env["PROVIDER"] = "ENV_P"
    assert get_provider() == "ENV_P"
    
    session["PROVIDER"] = "USER_P"
    assert get_provider() == "USER_P"

# --- TESTS FOR get_serpapi_key ---

def test_get_serpapi_key_logic(mock_streamlit, mock_env):
    session, secrets, env = mock_streamlit[0], mock_streamlit[1], mock_env
    
    secrets["SERPAPI_KEY"] = "serp_secret"
    assert get_serpapi_key() == "serp_secret"
    
    with pytest.raises(APIKeyError):
        # Clear them to test error
        secrets.clear()
        get_serpapi_key()


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
