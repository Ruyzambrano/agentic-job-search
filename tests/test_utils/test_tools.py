import pytest
import respx
import httpx
from src.utils.tools import extract_best_url, format_results, batch_scrape_jobs
from src.schema import RawJobMatch, ListRawJobMatch


# --- Tests for extract_best_url ---
def test_extract_best_url(url_test_case):
    """Clean, modular test using the parameterized fixture"""
    job_data, expected_url = url_test_case
    assert extract_best_url(job_data) == expected_url


def test_extract_best_url_with_apply_options():
    job = {
        "apply_options": [{"link": "https://apply.com"}],
        "link": "https://google.com",
    }
    assert extract_best_url(job) == "https://apply.com"


def test_extract_best_url_fallback():
    job = {"link": "https://google.com"}
    assert extract_best_url(job) == "https://google.com"


def test_extract_best_url_none():
    assert extract_best_url(None) == "Not specified"


# --- Tests for format_results ---


def test_format_results_valid_job():
    raw_job = {
        "title": "Software Engineer",
        "company_name": "Tesla",
        "description": "Build rockets.",
        "detected_extensions": {"salary": "100k"},
    }
    result = format_results(raw_job)
    assert isinstance(result, RawJobMatch)
    assert result.title == "Software Engineer"
    assert result.salary_string == "100k"


# --- Tests for batch_scrape_jobs (The Big One) ---
@pytest.mark.asyncio
@respx.mock
async def test_batch_scrape_jobs_success():
    mock_data = {
        "jobs_results": [
            {"title": "DevOps", "description": "Cloud stuff", "link": "url1"}
        ]
    }
    respx.get("https://serpapi.com/search?").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    # Change .invoke to .ainvoke
    result = await batch_scrape_jobs.ainvoke(
        {"queries": ["Python"], "location": "London", "distance": 40}
    )

    assert isinstance(result, ListRawJobMatch)
    assert len(result.jobs) > 0


@pytest.mark.asyncio
@respx.mock
async def test_batch_scrape_jobs_empty_results():
    respx.get("https://serpapi.com/search?").mock(
        return_value=httpx.Response(200, json={"jobs_results": []})
    )

    result = await batch_scrape_jobs.ainvoke(
        {"queries": ["NicheRoleThatDoesntExist"], "location": "Mars"}
    )

    assert len(result.jobs) == 0
