import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.graph import create_workflow
from src.schema import (
    RawJobMatchList, 
    SearchQueryPlan, 
    AnalysedJobMatchList, 
)
from src.services.storage_service import StorageService
from src.services.job_scraper import JobScraperService

def fetch_profile_side_effect(ids, namespace):
    """Mocks Pinecone fetch: Returns a Profile, but forces a Miss for jobs."""
    mock_res = MagicMock()
    if not ids:
        mock_res.vectors = {}
        return mock_res
        
    requested_id = ids[0]
    
    if "profile" in requested_id:
        mock_res.vectors = {
            requested_id: MagicMock(
                metadata={
                    "full_name": "Ruy Zambrano",
                    "job_titles": '["Senior Developer"]',
                    "key_skills": '["Python", "AWS"]',
                    "years_of_experience": 6,
                    "current_location": "London",
                    "summary": "Expert dev.",
                    "industries": '["Fintech"]'
                }
            )
        }

    else:
        mock_res.vectors = {}
        
    return mock_res

@pytest.mark.asyncio
async def test_full_graph_execution(
    mock_settings, 
    mock_pinecone, 
    mock_agent, 
    mock_raw_job, 
    mock_candidate_profile,
    mock_analysed_job,
    mock_location_data,
    mock_search_query_plan
):
    """
    INTEGRATION: Run the entire LangGraph with real service logic 
    but mocked external infrastructure.
    """
    _, index = mock_pinecone
    index.fetch.side_effect = fetch_profile_side_effect
    index.query.return_value = {"matches": []}
    
    mock_emb = MagicMock()
    real_storage = StorageService(index_name="test-index", embeddings=mock_emb)
    
    mock_store = MagicMock()
    mock_store.get_pinecone_index.return_value = index
    real_storage._get_store = MagicMock(return_value=mock_store)
    
    real_scraper = JobScraperService(mock_settings)
    real_scraper.run_research = AsyncMock(return_value=RawJobMatchList(jobs=[mock_raw_job]))

    mock_agent.ainvoke.side_effect = [
        {"structured_response": mock_candidate_profile}, 
        {"structured_response": mock_search_query_plan}, 
        {"structured_response": AnalysedJobMatchList(jobs=[mock_analysed_job])} 
    ]

    initial_state = {
        "cv_raw_text": "Experienced Python Dev",
        "messages": []
    }
    
    config = {
        "configurable": {
            "user_id": "test_user",
            "storage_service": real_storage,
            "job_scraper": real_scraper,
            "cv_parser_agent": mock_agent,
            "researcher_agent": mock_agent,
            "writer_agent": mock_agent,
            "pipeline_settings": mock_settings,
            "location": mock_location_data
        }
    }

    app = create_workflow()
    final_state = await app.ainvoke(initial_state, config=config)

    assert "cv_data" in final_state
    assert "research_data" in final_state
    assert "writer_data" in final_state
    
    assert len(final_state["writer_data"]) > 0