import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.utils.streamlit_utils import (
    iso_formatter,
    format_salary_as_range,
    filter_jobs_by_keywords,
    display_profile,
)


def test_iso_formatter_valid_date():
    date_str = "2026-03-02T10:00:00"
    assert iso_formatter(date_str) == "02 Mar 10:00"


def test_iso_formatter_invalid_date():
    assert iso_formatter("not-a-date") == "not-a-date"


def test_format_salary_range_both_values():
    assert format_salary_as_range(50000, 70000) == "£50,000 - £70,000"


def test_format_salary_range_missing_min():
    assert format_salary_as_range(None, 80000) == "£80,000"


@patch("src.utils.streamlit_utils.st")
def test_login_screen_triggers_login(mock_st):
    from src.utils.streamlit_utils import login_screen

    login_screen()
    # Verify button was created with the right callback
    mock_st.button.assert_called_once()
    args, kwargs = mock_st.button.call_args
    assert kwargs["on_click"] == mock_st.login


@patch("src.utils.streamlit_utils.st")
def test_display_profile_renders_headers(mock_st):
    mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
    profile = {
        "full_name": "Ruy Zambrano",
        "summary": "AI Engineer",
        "job_titles": ["Dev"],
        "key_skills": ["Python"],
        "industries": ["Tech"],
    }
    display_profile(profile)

    mock_st.title.assert_called_with("Ruy Zambrano")
    mock_st.write.assert_any_call("AI Engineer")



def test_filter_jobs_by_keywords(mock_analysed_job_match_with_meta):

    jobs = [mock_analysed_job_match_with_meta]

    assert len(filter_jobs_by_keywords(jobs, ["Python"])) == 1

    assert len(filter_jobs_by_keywords(jobs, ["Java"])) == 0
