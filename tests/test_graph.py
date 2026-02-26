from unittest.mock import patch

from nodes.utils.tools import scrape_for_jobs


@patch("serpapi.Client.search")
def test_scrape_for_jobs_tool(mock_search):
    mock_search.return_value = {
        "jobs_results": [
            {
                "title": "Software Engineer",
                "company_name": "Google",
                "share_link": "https://google.com/careers",
                "description": "Coding...",
                "location": "London",
                "detected_extensions": {"salary": "£100,000"},
            }
        ]
    }

    result = scrape_for_jobs.invoke({"role_keywords": "Python", "location": "London"})

    assert result.jobs[0].company_name == "Google"
    assert result.jobs[0].attributes.salary == "£100,000"
