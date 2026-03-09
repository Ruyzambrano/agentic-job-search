import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from src.agents.researcher import researcher_node
from src.schema import SearchQueryPlan, RawJobMatch, ListRawJobMatch

@pytest.mark.asyncio
@patch("src.agents.researcher.get_embeddings")
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
    mock_embed,
    mock_state,
    mock_config,
    mock_candidate_profile,
    mock_search_query_plan,
    mock_settings,
):
    mock_config["configurable"]["pipeline_settings"] = mock_settings
    
    mock_fetch.return_value = mock_candidate_profile
    mock_embed.return_value = MagicMock()
    
    mock_global_instance = mock_global.return_value
    mock_global_instance.get.return_value = {
        "metadatas": [
            [{"last_synced_at": datetime.now().isoformat(), "job_id": "some_id"}]
        ]
    }

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={"structured_response": mock_search_query_plan}
    )

    mock_batch_scrape.return_value = ListRawJobMatch(jobs=[
        RawJobMatch(
            title="Python Dev",
            job_url="url_1",
            company_name="TestCo",
            description="...",
            location="OOOO",
        )
    ])

    result = await researcher_node(mock_state, mock_agent, mock_config)

    assert "research_data" in result
    assert "messages" in result
    mock_batch_scrape.assert_called_once()
    mock_fetch.assert_called_once()