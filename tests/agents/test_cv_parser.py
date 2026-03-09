import pytest
from unittest.mock import patch
from src.agents.cv_parser import cv_parser_node



@patch("src.agents.cv_parser.get_embeddings") # Add this patch!
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


@patch("src.agents.cv_parser.get_user_analysis_store")
@patch("src.agents.cv_parser.save_candidate_profile")
@patch("src.agents.cv_parser.log_message")
def test_cv_parser_node_parses_new(
    mock_log, mock_save, mock_store, mock_agent, mock_state, mock_settings
):
    """Test that if no ID is provided, the LLM is triggered and data is saved."""
    config = {
        "configurable": {
            "user_id": "user1",
            "pipeline_settings": mock_settings
        }
    }
    mock_save.return_value = "new_prof_id"

    result = cv_parser_node(mock_state, mock_agent, config)

    mock_agent.invoke.assert_called_once_with(mock_state)
    mock_save.assert_called_once()
    assert result["active_profile_id"] == "new_prof_id"
    assert result["cv_data"].full_name == "Ruy Zambrano"


def test_cv_parser_node_missing_user_id(mock_agent, mock_state):
    """Test that the node raises ValueError if user_id is missing."""
    config = {"configurable": {}}  # Empty config

    with pytest.raises(ValueError, match="user_id is missing"):
        cv_parser_node(mock_state, mock_agent, config)
