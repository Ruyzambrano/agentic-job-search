import pytest
import respx
import httpx
import re
from src.schema import RawJobMatch, RawJobMatchList, WorkSetting


def test_get_best_apply_link_priority(scraper_service):
    options = [
        {"title": "Indeed", "link": "https://indeed.com"},
        {"title": "LinkedIn", "link": "https://linkedin.com"},
    ]
    assert scraper_service._get_best_apply_link(options) == "https://linkedin.com"

def test_get_best_apply_link_fallback(scraper_service):
    options = [{"title": "UnknownSite", "link": "https://random.com"}]
    assert scraper_service._get_best_apply_link(options) == "https://random.com"


def test_map_google_to_schema_logic(scraper_service):
    raw_google_job = {
        "title": "Software Engineer",
        "company_name": "Tesla",
        "detected_extensions": {"salary": "£100k"},
        "apply_options": [{"link": "https://tesla.com/jobs"}]
    }
    result = scraper_service._map_google_to_schema(raw_google_job)
    assert isinstance(result, RawJobMatch)
    assert result.salary_string == "£100k"
    assert result.company == "Tesla"

def test_map_linkedin_to_schema_work_setting(scraper_service):
    raw_linkedin_job = {
        "title": "Remote Python Developer",
        "organization": "AI Labs",
        "remote_derived": True
    }
    result = scraper_service._map_linkedin_to_schema(raw_linkedin_job)
    assert result.work_setting == WorkSetting.REMOTE


@pytest.mark.asyncio
@respx.mock
async def test_run_research_google_success(scraper_service):
    # Mock SerpAPI
    mock_data = {
        "jobs_results": [
            {"title": "DevOps", "company_name": "CloudCo", "apply_options": [{"link": "url1"}]}
        ]
    }
    respx.get(re.compile(r"https://serpapi\.com/search.*")).mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    scraper_service.api_cfg.use_google = True
    scraper_service.api_cfg.use_linkedin = False

    result = await scraper_service.run_research(["Python"], "London")

    assert isinstance(result, RawJobMatchList)
    assert len(result.jobs) == 1
    assert result.jobs[0].title == "DevOps"

@pytest.mark.asyncio
@respx.mock
async def test_run_research_no_scrapers_enabled(scraper_service):
    scraper_service.api_cfg.use_google = False
    scraper_service.api_cfg.use_linkedin = False

    result = await scraper_service.run_research(["Python"], "London")
    assert len(result.jobs) == 0


def test_process_and_deduplicate(scraper_service):
    # Create two jobs with the same URL
    job1 = RawJobMatch(title="Job 1", job_url="https://same.com", company_name="A", location="L")
    job2 = RawJobMatch(title="Job 2", job_url="https://same.com", company_name="B", location="L")
    
    input_data = [[job1], [job2]]
    
    result = scraper_service._process_and_deduplicate(input_data)
    assert len(result.jobs) == 1