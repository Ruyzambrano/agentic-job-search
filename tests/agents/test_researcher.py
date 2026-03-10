import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from src.agents.researcher import researcher_node
from src.schema import SearchQueryPlan, RawJobMatch, ListRawJobMatch

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from src.agents.researcher import researcher_node
from src.schema import ListRawJobMatch, RawJobMatch, SearchQueryPlan

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
    
    mock_index = MagicMock()
    mock_global.return_value.get_pinecone_index.return_value = mock_index
    mock_global.return_value._namespace = "global_raw_jobs"

    mock_vector = MagicMock()
    mock_vector.metadata = {
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        "job_url": "url_1",
        "title": "Python Dev"
    }
    
    mock_response = MagicMock()
    mock_response.vectors = {"url_1_Python Dev": mock_vector}
    mock_index.fetch.return_value = mock_response

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={"structured_response":mock_search_query_plan }
    )

    # 4. Setup Scraper Mock
    mock_batch_scrape.return_value = ListRawJobMatch(jobs=[
        RawJobMatch(
            title="Python Dev",
            job_url="url_1",
            company_name="TestCo",
            description="Agents and stuff",
            location="Remote",
            posted_at="2024-01-01"
        )
    ])

    result = await researcher_node(mock_state, mock_agent, mock_config)

    assert "research_data" in result
    assert isinstance(result["research_data"], list)
    assert len(result["research_data"]) > 0
    mock_log.assert_any_call("Research complete! Found a total of 1 jobs")