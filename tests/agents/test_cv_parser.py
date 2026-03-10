import pytest
from unittest.mock import patch, MagicMock
from src.agents.cv_parser import cv_parser_node



@patch("src.agents.cv_parser.get_embeddings") 
@patch("src.agents.cv_parser.get_user_analysis_store")
@patch("src.agents.cv_parser.fetch_candidate_profile")
def test_cv_parser_node_fetches_existing(
    mock_fetch, mock_store, mock_embed, mock_agent, mock_state, mock_candidate_profile, mock_settings
):
    """Test that if an active_profile_id is provided, we skip the LLM."""
    
    config = {
        "configurable": {
            "user_id": "user1",
            "active_profile_id": "prof_123",
            "pipeline_settings": mock_settings
        }
    }

    mock_fetch.return_value = mock_candidate_profile
    
    # Execute
    result = cv_parser_node(mock_state, mock_agent, config)


    assert result["cv_data"] == mock_candidate_profile
    mock_agent.ainvoke.assert_not_called()


# Add this to your patches
@patch("src.agents.cv_parser.get_embeddings") 
@patch("src.agents.cv_parser.get_user_analysis_store")
@patch("src.agents.cv_parser.save_candidate_profile")
@patch("src.agents.cv_parser.log_message")
def test_cv_parser_node_parses_new(
    mock_log, 
    mock_save, 
    mock_store, 
    mock_get_embeddings, 
    mock_agent, 
    mock_state, 
    mock_settings
):
    mock_get_embeddings.return_value = MagicMock() 
    
    config = {
        "configurable": {
            "user_id": "user1",
            "pipeline_settings": mock_settings
        }
    }
    mock_save.return_value = "new_prof_id"
    
    result = cv_parser_node(mock_state, mock_agent, config)
    
    assert result is not None


def test_cv_parser_node_missing_user_id(mock_agent, mock_state):
    """Test that the node raises ValueError if user_id is missing."""
    config = {"configurable": {}}  # Empty config

    with pytest.raises(ValueError, match="user_id is missing"):
        cv_parser_node(mock_state, mock_agent, config)
