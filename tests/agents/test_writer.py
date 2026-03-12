import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.agents.writer import writer_node
from src.schema import AnalysedJobMatch

@pytest.mark.asyncio
@patch("src.agents.writer.get_embeddings") 
@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.check_analysis_cache")
@patch("src.agents.writer.save_job_analyses")
@patch("src.agents.writer.log_message")
async def test_writer_node_cache_hit_only(
    mock_log,
    mock_save,
    mock_check,
    mock_store,
    mock_embed,
    mock_state,
    mock_agent,
    mock_config,
    mock_analysed_job_match_with_meta,
    mock_settings,
):
    mock_config["configurable"]["pipeline_settings"] = mock_settings
    mock_embed.return_value = MagicMock()
    cached_job = mock_analysed_job_match_with_meta
    mock_check.return_value = ([cached_job], [])

    result = await writer_node(mock_state, mock_agent, mock_config)

    assert "writer_data" in result
    assert len(result["writer_data"].jobs) == 1


@pytest.mark.asyncio
@patch("src.agents.writer.get_embeddings")
@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.check_analysis_cache")
@patch("src.agents.writer.save_job_analyses")
async def test_writer_node_cache_miss_triggers_llm(
    mock_save,
    mock_check,
    mock_store,
    mock_embed,
    mock_state,
    mock_agent,
    mock_config,
    mock_settings
):
    mock_config["configurable"]["pipeline_settings"] = mock_settings
    mock_embed.return_value = MagicMock()

    missed_jobs = mock_state["research_data"].jobs
    mock_check.return_value = ([], missed_jobs)


    mock_agent.ainvoke = AsyncMock(return_value={
        "structured_response": MagicMock(jobs=[]) 
    })

    result = await writer_node(mock_state, mock_agent, mock_config)

    assert "writer_data" in result