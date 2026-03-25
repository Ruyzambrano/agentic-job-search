import pytest
from unittest.mock import AsyncMock
from src.agents.writer import writer_node
from src.schema import AnalysedJobMatchList

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_writer_node_cache_hit_only(
    mock_state,
    mock_agent,
    mock_config,
    mock_analysed_job,
    mock_storage_service,
):
    mock_config["configurable"]["storage_service"] = mock_storage_service
    
    mock_storage_service.check_analysis_cache.return_value = ([mock_analysed_job], [])

    result = await writer_node(mock_state, mock_config)

    assert "writer_data" in result
    assert len(result["writer_data"].jobs) == 1
    mock_agent.ainvoke.assert_not_called()

@pytest.mark.asyncio
async def test_writer_node_cache_miss_triggers_llm(
    mock_state,
    mock_agent,
    mock_config,
    mock_raw_job,
    mock_analysed_job,
    mock_storage_service,
    mock_settings, 
):
    """
    SOP: If jobs are missing from cache, the LLM must be invoked,
    and the new analyses must be saved to the StorageService.
    """
    mock_config["configurable"] = {
        "storage_service": mock_storage_service,
        "writer_agent": mock_agent,     
        "pipeline_settings": mock_settings, 
        "user_id": "user_123",
        "active_profile_id": "prof_123",
    }

    mock_storage_service.check_analysis_cache.return_value = ([], [mock_raw_job])
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": AnalysedJobMatchList(jobs=[mock_analysed_job])
        }
    )

    result = await writer_node(mock_state, mock_config)

    assert "writer_data" in result
    mock_agent.ainvoke.assert_called_once()
    mock_storage_service.save_job_analyses.assert_called_once()