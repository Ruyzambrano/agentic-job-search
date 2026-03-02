import pytest
from unittest.mock import MagicMock, patch
from src.agents.writer import writer_node
from src.schema import AnalysedJobMatch

@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.check_analysis_cache")
@patch("src.agents.writer.save_job_analyses")
@patch("src.agents.writer.log_message")
def test_writer_node_cache_hit_only(
    mock_log, mock_save, mock_check, mock_store, 
    mock_state, mock_agent, mock_config, mock_analysed_job_match_with_meta
):
    """
    Scenario: All jobs are already in the cache.
    Expected: Agent is NOT called, writer_data contains cached jobs.
    """
    # 1. Setup Mock for Cache Hit
    cached_job = mock_analysed_job_match_with_meta
    # check_analysis_cache returns (hits, misses)
    mock_check.return_value = ([cached_job], [])
    
    # 2. Execute
    result = writer_node(mock_state, mock_agent, mock_config)
    
    # 3. Assertions
    mock_agent.invoke.assert_not_called()
    assert len(result["writer_data"].jobs) == 1
    assert result["writer_data"].jobs[0].title == "Python Dev"
    assert result["messages"] == []

@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.check_analysis_cache")
@patch("src.agents.writer.save_job_analyses")
def test_writer_node_cache_miss_triggers_llm(
    mock_save, mock_check, mock_store, 
    mock_state, mock_agent, mock_config
):
    # 1. Setup Mock for Cache Miss
    missed_jobs = mock_state["research_data"].jobs 
    mock_check.return_value = ([], missed_jobs)
    
    # 2. CREATE REAL OBJECTS FOR THE MOCK
    # Use your schema so .model_dump() works perfectly
    mock_analysed_job = AnalysedJobMatch(
        title="AI Eng",
        company="AI Labs",
        job_url="url_2",
        location="London",
        job_summary="Great role",
        qualifications=["Python"],
        attributes=["Remote"],
        tech_stack=["PyTorch"],
        top_applicant_score=85,
        top_applicant_reasoning="Matches skills"
    )

    # 3. Setup the Agent Mock
    mock_llm_result = MagicMock()
    mock_llm_result.jobs = [mock_analysed_job] # Real object here
    mock_agent.invoke.return_value = {"structured_response": mock_llm_result}

    # 2. Execute
    result = writer_node(mock_state, mock_agent, mock_config)
    
    # 3. Assertions
    mock_agent.invoke.assert_called_once()
    mock_save.assert_called_once()
    assert len(result["writer_data"].jobs) == 1
    assert "messages" in result