import pytest
from unittest.mock import MagicMock, AsyncMock

from src.agents.researcher import researcher_node
from src.schema import SearchQueryPlan, RawJobMatchList

@pytest.mark.asyncio
async def test_researcher_node_success(
    mock_agent,
    mock_state,
    mock_config,
    mock_search_query_plan,
    mock_storage_service,
    mock_raw_job,
    mock_settings,
    mock_location_data
):
    mock_scraper = MagicMock()
    mock_scraper.run_research = AsyncMock(return_value=RawJobMatchList(jobs=[mock_raw_job]))

    mock_config["configurable"] = {
        "storage_service": mock_storage_service,
        "job_scraper": mock_scraper,
        "researcher_agent": mock_agent,
        "pipeline_settings": mock_settings,
        "user_id": "user_123",
        "location": mock_location_data,
        "role": "Wizard"
    }
    mock_state["active_profile_id"] = "test"
    mock_agent.ainvoke = AsyncMock(return_value={"structured_response": mock_search_query_plan})
    mock_storage_service.sync_global_library.return_value = [mock_raw_job]

    result = await researcher_node(mock_state, mock_config)

    assert "research_data" in result
    assert len(result["research_data"].jobs) == 1


@pytest.mark.asyncio
async def test_researcher_node_no_queries_found(
    mock_agent, 
    mock_state, 
    mock_config, 
    mock_storage_service,
    mock_settings,
    mock_location_data
):
    """
    If the LLM fails to generate queries, the node should exit gracefully.
    """
    mock_config["configurable"] = {
        "storage_service": mock_storage_service,
        "researcher_agent": mock_agent,
        "pipeline_settings": mock_settings,
        "user_id": "user_123",
        "location": mock_location_data
    }
    mock_state["active_profile_id"] = "test"
    empty_plan = SearchQueryPlan(steps=[])
    mock_agent.ainvoke = AsyncMock(
        return_value={"structured_response": empty_plan}
    )

    result = await researcher_node(mock_state, mock_config)

    assert "research_data" in result
    assert len(result["research_data"].jobs) == 0