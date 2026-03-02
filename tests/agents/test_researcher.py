import asyncio
from pytest import mark
from unittest.mock import patch, MagicMock

from src.agents.researcher import researcher_node

@mark.asyncio
@patch("src.agents.researcher.get_user_analysis_store")
@patch("src.agents.researcher.get_global_jobs_store")
@patch("src.agents.researcher.fetch_candidate_profile")
@patch("src.agents.researcher.log_message")
async def test_researcher_node_success(
    mock_log, mock_fetch, mock_global, mock_user_store, 
    mock_state, mock_config, mock_candidate_profile, mock_raw_jobs
):
    mock_fetch.return_value = mock_candidate_profile
    
    # --- THE FIX ---
    # Create an awaitable future for the mock
    future = asyncio.Future()
    future.set_result({"structured_response": mock_raw_jobs})
    
    mock_agent = MagicMock()
    mock_agent.ainvoke.return_value = future # This makes it 'awaitable'
    # ----------------

    result = await researcher_node(mock_state, mock_agent, mock_config)

    assert "research_data" in result
    assert result["research_data"].jobs[0].title == "AI Engineer"