import pytest
from unittest.mock import patch, MagicMock

from src.utils.func import iso_formatter, format_salary_as_range
from src.schema import WorkSetting, SeniorityLevel
from src.ui.components import display_profile

def test_iso_formatter_valid_date():
    date_str = "2026-03-02T10:00:00"
    assert iso_formatter(date_str) == "02 Mar 10:00"

def test_iso_formatter_invalid_date():
    assert iso_formatter("not-a-date") == "not-a-date"

def test_format_salary_range_both_values():
    assert format_salary_as_range(50000, 70000) == "£50,000 - £70,000"

def test_format_salary_range_missing_min():
    assert format_salary_as_range(None, 80000) == "Up to £80,000"

def test_format_salary_range_none():
    assert format_salary_as_range(None, None) == "Salary not specified"

@patch("src.ui.components.st")
def test_display_profile_renders_headers(mock_st):
    
    
    mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
    profile = {
        "full_name": "Ruy Zambrano",
        "summary": "AI Engineer",
        "job_titles": ["Dev"],
        "key_skills": ["Python"],
        "industries": ["Tech"],
        "seniority_level": SeniorityLevel.SENIOR,
        "work_preference": WorkSetting.REMOTE
    }
    display_profile(profile)
    
    mock_st.title.assert_called_with("👤 Ruy Zambrano")
    all_calls = [str(c) for c in mock_st.mock_calls]
    assert any("AI Engineer" in call_str for call_str in all_calls)