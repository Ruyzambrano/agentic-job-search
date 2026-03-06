import pytest
import respx
import httpx
from src.utils.tools import (
    extract_best_url,
    format_results,
    batch_scrape_jobs,
    sanitize_query,
    filter_redundant_queries,
)
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
    result = await batch_scrape_jobs(["Python"], "London", 40)

    assert isinstance(result, ListRawJobMatch)
    assert len(result.jobs) > 0


@pytest.mark.asyncio
@respx.mock
async def test_batch_scrape_jobs_empty_results():
    respx.get("https://serpapi.com/search?").mock(
        return_value=httpx.Response(200, json={"jobs_results": []})
    )

    result = await batch_scrape_jobs(["NicheRoleThatDoesntExist"], "Mars")

    assert len(result.jobs) == 0


def test_sanitize_basic_cleanup():
    assert sanitize_query("  data engineer  ") == "DATA ENGINEER"
    assert sanitize_query("Data Engineer-") == "DATA ENGINEER"


def test_sanitize_boolean_reordering():
    q1 = sanitize_query("Python OR SQL")
    q2 = sanitize_query("SQL OR Python")
    assert q1 == q2
    assert q1 == "PYTHON OR SQL"


def test_sanitize_parentheses_removal():
    q1 = sanitize_query("(SQL OR Python) OR Java")
    q2 = sanitize_query("Java OR SQL OR Python")
    assert q1 == q2
    assert q1 == "JAVA OR PYTHON OR SQL"


def test_sanitize_duplicate_terms_within_query():
    assert sanitize_query("SQL OR SQL OR Python") == "PYTHON OR SQL"


def test_filter_exact_duplicates():
    queries = ["DATA ENGINEER", "DATA ENGINEER"]
    assert len(filter_redundant_queries(queries)) == 1


def test_filter_fuzzy_near_matches():
    queries = ["Data Engineer London", "Data Engineering London"]
    result = filter_redundant_queries(queries, threshold=85)
    assert len(result) == 1
    assert result[0] == "Data Engineer London"


def test_filter_distinct_queries():
    queries = ["Python Developer", "Accountant"]
    assert len(filter_redundant_queries(queries)) == 2


def test_full_optimization_pipeline():
    raw_input = [
        "(SQL OR Python) London",
        "Python OR SQL London",
        "Python OR SQL  London ",
        "Data Scientist Manchester",
        "Data Science Manchester",
    ]

    clean_pool = list(set(sanitize_query(q) for q in raw_input))
    final = filter_redundant_queries(clean_pool, threshold=85)

    assert len(final) == 2
