import json
from unittest.mock import MagicMock, patch

from src.schema import RawJobMatch, ListRawJobMatch, AnalysedJobMatch, AnalysedJobMatchList
from nodes.writer import writer_node


@patch("nodes.writer.get_vector_store")
def test_writer_node_cache_hit(mock_get_db, mock_state):
    mock_db = MagicMock()

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

    mock_db.get.return_value = {
        "metadatas": [{"analysis_json": json.dumps(cached_data)}]
    }
    mock_get_db.return_value = mock_db

    mock_agent = MagicMock()
    result = writer_node(mock_state, mock_agent)

    assert len(result["writer_data"].jobs) == 2
    assert result["writer_data"].jobs[0].company == "Tech Co"
    mock_agent.invoke.assert_not_called()


@patch("nodes.writer.get_vector_store")
def test_writer_node_cache_miss(mock_get_db, mock_state):
    mock_db = MagicMock()
    mock_db.get.return_value = {"metadatas": []}  # Simulate empty DB
    mock_get_db.return_value = mock_db

    mock_agent = MagicMock()
    # Ensure the structured_response returns the correct type
    mock_agent.invoke.return_value = {
        "structured_response": AnalysedJobMatchList(
            jobs=[
                AnalysedJobMatch(
                    title="New Job",
                    top_applicant_score=80,
                    top_applicant_reasoning="...",
                    office_days="",
                    tech_stack=["..."],
                    job_summary="...",
                    job_url="url_1",
                    attributes=["..."],
                    company="...",
                    qualifications=["..."],
                    location="Miami",
                    salary_max=100,
                    salary_min=10,
                )
            ]
        )
    }

    result = writer_node(mock_state, mock_agent)

    assert mock_agent.invoke.called
    assert len(result["writer_data"].jobs) == 1
    mock_db.add_texts.assert_called()
