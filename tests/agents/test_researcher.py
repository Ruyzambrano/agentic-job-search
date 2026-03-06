import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from pytest import mark

from src.agents.researcher import researcher_node
from src.schema import RawJobMatch, ListRawJobMatch


@mark.asyncio
@patch("src.agents.researcher.batch_scrape_jobs", new_callable=AsyncMock)
@patch("src.agents.researcher.get_user_analysis_store")
@patch("src.agents.researcher.get_global_jobs_store")
@patch("src.agents.researcher.fetch_candidate_profile")
@patch("src.agents.researcher.log_message")
async def test_researcher_node_success(
    mock_log,
    mock_fetch,
    mock_global,
    mock_user_store,
    mock_batch_scrape,
    mock_state,
    mock_config,
    mock_candidate_profile,
    mock_search_query_plan,
):
    # Setup fetch profile
    mock_fetch.return_value = mock_candidate_profile

    # Setup global store
    mock_global_instance = mock_global.return_value
    mock_global_instance.get.return_value = {
        "metadatas": [
            [{"last_synced_at": datetime.now().isoformat(), "job_id": "some_id"}]
        ]
    }

    # Setup Agent mock to behave like a coroutine
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={"structured_response": mock_search_query_plan}
    )

    # Setup Scraper mock
    mock_batch_scrape.return_value = ListRawJobMatch(
        jobs=[
            RawJobMatch(
                title="Python Dev",
                job_url="url_1",
                company_name="TestCo",
                description="...",
                location="OOOO",
            )
        ]
    )

    # EXECUTE
    result = await researcher_node(mock_state, mock_agent, mock_config)

    # ASSERTIONS
    assert "research_data" in result
    # Access via the .jobs attribute of your Pydantic model
    assert result["research_data"][0].title == "Python Dev"
