import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agents.cv_parser import cv_parser_node
from src.schema import CandidateProfile

@pytest.mark.asyncio
async def test_cv_parser_node_fetches_existing(
    mock_agent,
    mock_state,
    mock_candidate_profile,
    mock_storage_service,
):
    """
    If an active_profile_id is provided, we fetch from StorageService
    and skip the LLM entirely.
    """
    config = {
        "configurable": {
            "user_id": "user1",
            "active_profile_id": "prof_123",
            "storage_service": mock_storage_service,
            "agent": mock_agent,
        }
    }

    mock_storage_service.fetch_candidate_profile.return_value = mock_candidate_profile

    result = await cv_parser_node(mock_state, config)

    assert result["cv_data"] == mock_candidate_profile
    mock_agent.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_cv_parser_node_parses_new(
    mock_agent,
    mock_state,
    mock_storage_service,
    mock_candidate_profile
):
    """
    SOP: If NO profile ID is provided, we use the LLM to parse raw text
    and save the result via StorageService.
    """
    mock_state["cv_raw_text"] = "Experienced Python Developer from London..."

    mock_agent.ainvoke = AsyncMock(return_value={
        "structured_response": mock_candidate_profile
    })
    
    mock_storage_service.save_candidate_profile.return_value = "new_prof_id"

    config = {
        "configurable": {
            "user_id": "user1",
            "storage_service": mock_storage_service,
            "cv_parser_agent": mock_agent,
        }
    }

    result = await cv_parser_node(mock_state, config)

    assert result["cv_data"] == mock_candidate_profile
    assert result["active_profile_id"] == "new_prof_id"
    
    mock_agent.ainvoke.assert_called_once()
    mock_storage_service.save_candidate_profile.assert_called_once()


@pytest.mark.asyncio
async def test_cv_parser_node_missing_user_id(mock_agent, mock_state, mock_storage_service):
    """
    Ensure the node raises ValueError if critical config keys are missing.
    """
    config = {
        "configurable": {
            "storage_service": mock_storage_service,
            "cv_parser_agent": mock_agent,
        }
    }

    with pytest.raises(ValueError, match="User ID required to process CV."):
        await cv_parser_node(mock_state, config)
