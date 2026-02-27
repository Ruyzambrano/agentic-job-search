from unittest.mock import MagicMock, patch

from src.agents.cv_parser import cv_parser_node
from src.agents.researcher import researcher_node

@patch("src.agents.cv_parser.get_user_analysis_store")
@patch("src.utils.vector_handler.ENV.get")
def test_cv_parser_node_logic(mock_env, mock_store, mock_candidate_profile, mock_config):
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"structured_response": mock_candidate_profile}

    mock_vector_db = MagicMock()
    mock_store.return_value = mock_vector_db

    mock_env.return_value = "text-embedding-001"

    state = {"messages": []}
    output = cv_parser_node(state, mock_agent, mock_config)

    assert output["cv_data"].full_name == "Ruy Zambrano"
    assert "Python" in output["cv_data"].key_skills

@patch("src.agents.researcher.get_global_jobs_store")
@patch("src.agents.researcher.get_user_analysis_store")
@patch("src.utils.vector_handler.ENV.get")
def test_researcher_node_logic(mock_env, mock_analysis_store, mock_global_store, mock_raw_jobs, mock_config, mock_vector_candidate_profile):
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"structured_response": mock_raw_jobs}

    mock_analysis_db = MagicMock()
    mock_analysis_store.return_value = mock_analysis_db

    mock_global_db = MagicMock()
    mock_global_store.return_value = mock_global_db

    mock_env.return_value = "text-embedding-001"

    mock_analysis_db.get.return_value = mock_vector_candidate_profile
    mock_global_db.get.return_value = {"ids": [], "metadatas": []}

    state = {"messages": [], "cv_data": None}

    output = researcher_node(state, mock_agent, mock_config)

    assert "research_data" in output
    assert len(output["research_data"].jobs) == 1
    assert output["research_data"].jobs[0].company_name == "TechCorp"
