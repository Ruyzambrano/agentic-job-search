import pytest
from unittest.mock import MagicMock, patch
from src.agents.writer import writer_node
from src.schema import AnalysedJobMatch


@patch("src.agents.writer.get_embeddings") 
@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.check_analysis_cache")
@patch("src.agents.writer.save_job_analyses")
@patch("src.agents.writer.log_message")
def test_writer_node_cache_hit_only(
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

    result = writer_node(mock_state, mock_agent, mock_config)

    assert "writer_data" in result
    assert result["writer_data"].jobs[0] == cached_job
    mock_agent.invoke.assert_not_called()

@patch("src.agents.writer.get_embeddings")
@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.check_analysis_cache")
@patch("src.agents.writer.save_job_analyses")
def test_writer_node_cache_miss_triggers_llm(
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

    mock_analysed_job = AnalysedJobMatch(
        title="AI Eng",
        company="AI Labs",
        job_url="url_2",
        location="London",
        job_summary="Great role",
        qualifications=["Python"],
        attributes=["Remote"],
        key_skills=["PyTorch"],
        top_applicant_score=85,
        top_applicant_reasoning="Matches skills",
    )

    mock_llm_result = MagicMock()
    mock_llm_result.jobs = [mock_analysed_job]
    mock_agent.invoke.return_value = {"structured_response": mock_llm_result}

    result = writer_node(mock_state, mock_agent, mock_config)

    assert "writer_data" in result
    assert result["writer_data"].jobs[0].title == "AI Eng"
    mock_agent.invoke.assert_called_once()
    mock_save.assert_called_once()