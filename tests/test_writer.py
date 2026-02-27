import json
from unittest.mock import MagicMock, patch

from src.schema import AnalysedJobMatch, AnalysedJobMatchList
from src.agents.writer import writer_node

@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.fetch_candidate_profile")
@patch("src.agents.writer.get_global_jobs_store")
@patch("src.utils.vector_handler.ENV.get")
def test_writer_node_cache_hit( mock_env, mock_get_db, mock_fetch_profile, mock_get_user_db, mock_state, mock_config):
    mock_profile = MagicMock()
    mock_fetch_profile.return_value = mock_profile
    
    mock_user_db = MagicMock()
    mock_get_user_db.return_value = mock_user_db

    mock_env.return_value = "text-embedding-001"
    cached_data = {
        "title": "Python Dev",
        "company": "Tech Co",
        "job_url": "url_1",
        "location": "London",
        "office_days": "3 days",
        "job_summary": "A great role",
        "qualifications": ["Python", "AWS"],
        "attributes": ["Hybrid", "Full-time"],
        "tech_stack": ["FastAPI", "PostgreSQL"],
        "salary_min": 70000,
        "salary_max": 90000,
        "top_applicant_score": 95,
        "top_applicant_reasoning": "Great experience with FastAPI",
    }

    mock_user_db.get.return_value = {
        "metadatas": [{"analysis_json": json.dumps(cached_data)}]
    }
    mock_get_db.return_value = MagicMock()

    mock_agent = MagicMock()
    result = writer_node(mock_state, mock_agent, mock_config)

    assert len(result["writer_data"].jobs) == 2
    assert result["writer_data"].jobs[0].company == "Tech Co"
    mock_agent.invoke.assert_not_called()

@patch("src.agents.writer.get_user_analysis_store")
@patch("src.agents.writer.fetch_candidate_profile")
@patch("src.agents.writer.get_global_jobs_store")
@patch("src.utils.vector_handler.ENV.get")
def test_writer_node_cache_miss(mock_env, mock_get_global_db, mock_fetch_profile, mock_get_user_db, mock_state, mock_config):
    mock_user_db = MagicMock()
    mock_user_db.get.return_value = {"metadatas": [], "ids": []} 
    mock_get_user_db.return_value = mock_user_db

    mock_global_db = MagicMock()
    mock_get_global_db.return_value = mock_global_db

    mock_profile = MagicMock()
    mock_fetch_profile.return_value = mock_profile
    
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "structured_response": AnalysedJobMatchList(
            jobs=[
                AnalysedJobMatch(
                    title="New Job",
                    top_applicant_score=80,
                    top_applicant_reasoning="Reasoning...",
                    office_days="None",
                    tech_stack=["Python"],
                    job_summary="Summary...",
                    job_url="url_1",
                    attributes=["Full-time"],
                    company="New Co",
                    qualifications=["Degree"],
                    location="Miami",
                    salary_max=100,
                    salary_min=10,
                )
            ]
        )
    }

    result = writer_node(mock_state, mock_agent, mock_config)

    assert mock_agent.invoke.called, "The LLM agent should have been called on a cache miss"
    assert len(result["writer_data"].jobs) == 1
    assert result["writer_data"].jobs[0].title == "New Job"
    
    mock_user_db.add_texts.assert_called()