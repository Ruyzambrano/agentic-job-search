import pytest
from nodes.cv_parser import cv_parser_node
from nodes.researcher import researcher_node
from unittest.mock import MagicMock

def test_cv_parser_node_logic(mock_candidate_profile):
    # Setup mock agent
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"structured_response": mock_candidate_profile}
    
    state = {"messages": []}
    
    # Run node
    output = cv_parser_node(state, mock_agent)
    
    # Assertions
    assert output["cv_data"].full_name == "Ruy Zambrano"
    assert "Python" in output["cv_data"].key_skills

def test_researcher_node_logic(mock_raw_jobs):
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"structured_response": mock_raw_jobs}
    
    # Minimal state required by researcher_node
    state = {"messages": [], "cv_data": None} 
    
    output = researcher_node(state, mock_agent)
    
    assert "research_data" in output
    assert len(output["research_data"].jobs) == 1
    assert output["research_data"].jobs[0].company_name == "TechCorp"