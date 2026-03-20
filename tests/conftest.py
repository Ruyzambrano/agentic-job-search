import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from src.schema import (
    CandidateProfile, 
    RawJobMatch, 
    RawJobMatchList, 
    AnalysedJobMatchWithMeta, 
    WorkSetting, 
    SeniorityLevel,
    PipelineSettings,
    ApiSettings,
    AgentWeights,
    SearchQueryPlan,
    SearchStep,
    LocationData
)
from src.services.job_scraper import JobScraperService

@pytest.fixture
def mock_streamlit(monkeypatch):
    mock_session = {
        "messages": [],
        "storage_service": MagicMock(),
        "pipeline_settings": PipelineSettings()
    }
    mock_secrets = {"PINECONE_NAME": "test-index", "PINECONE_API_KEY": "fake-key"}
    monkeypatch.setattr("streamlit.session_state", mock_session)
    monkeypatch.setattr("streamlit.secrets", mock_secrets)
    return mock_session, mock_secrets

@pytest.fixture
def mock_settings():
    settings = PipelineSettings()
    settings.api_settings = ApiSettings(gemini_api_key="test_key", ai_provider="Gemini")
    settings.weights = AgentWeights(key_skills=80, experience=50)
    return settings

@pytest.fixture
def mock_search_query_plan():
    return SearchQueryPlan(
        steps=[SearchStep(title_stems=["Data Engin"], 
                         must_have_skills=["Python"], 
                         reasoning="Because")
        ])

@pytest.fixture(autouse=True)
def silent_embeddings():
    with patch("src.core.embeddings_handler.get_embeddings") as mock:
        embedding_mock = MagicMock()
        embedding_mock.embed_query.return_value = [0.0] * 3072
        mock.return_value = embedding_mock
        yield mock

@pytest.fixture
def mock_raw_job():
    return RawJobMatch(
        title="Python Developer",
        company_name="Tech Co",
        location="London",
        job_url="https://example.com/1",
        description="Coding in Python.",
        qualifications=["Python", "SQL"],
        responsibilities=["Build APIs"],
        benefits=["Remote work"],
        work_setting=WorkSetting.HYBRID,
        seniority_level=SeniorityLevel.MID,
        salary_string="£50k"
    )

@pytest.fixture
def mock_analysed_job(mock_raw_job):
    return AnalysedJobMatchWithMeta(
        **mock_raw_job.model_dump(),
        job_summary="A Python role.",
        attributes=["Proactive"],
        key_skills=["FastAPI"],
        top_applicant_score=85,
        top_applicant_reasoning="Good skills.",
        analysed_at=datetime.now(timezone.utc).isoformat(),
        target_role="Developer",
        target_location="London"
    )

@pytest.fixture
def mock_candidate_profile():
    return CandidateProfile(
        full_name="Ruy Zambrano",
        job_titles=["Senior Developer"],
        key_skills=["Python", "AWS"],
        years_of_experience=6,
        current_location="London",
        seniority_level=SeniorityLevel.SENIOR,
        summary="Expert dev.",
        industries=["Fintech"],
        work_preference=WorkSetting.REMOTE
    )

@pytest.fixture
def mock_state(mock_raw_job):
    return {
        "messages": [],
        "research_data": RawJobMatchList(jobs=[mock_raw_job]),
    }

@pytest.fixture
def mock_pinecone():
    store = MagicMock()
    index = MagicMock()
    store.get_pinecone_index.return_value = index
    store.NS_USER_DATA = "user_data"
    store.NS_GLOBAL_JOBS = "global_raw_jobs"
    
    index.query.return_value = {"matches": []}
    index.fetch.return_value = MagicMock(vectors={})
    
    return store, index

@pytest.fixture
def mock_config():
    return {
        "configurable": {
            "user_id": "user_001",
            "profile_id": "prof_001",
        }
    }

@pytest.fixture
def mock_storage_service():
    """
    Returns a MagicMock that mimics StorageService.
    This allows us to use .return_value on its methods in Agent tests.
    """
    service = MagicMock()
    
    service.save_candidate_profile = MagicMock()
    service.fetch_candidate_profile = MagicMock()
    service.check_analysis_cache = MagicMock()
    service.save_job_analyses = MagicMock()
    service.sync_global_library = MagicMock()
    service.find_all_candidate_profiles = MagicMock()
    service.find_all_jobs_for_user = MagicMock()
    
    service.NS_USER_DATA = "user_data"
    service.NS_GLOBAL_JOBS = "global_jobs"
    
    return service

@pytest.fixture
def scraper_service(mock_settings):
    return JobScraperService(mock_settings)

@pytest.fixture
def mock_agent():
    """Mocks the LangChain agent/LLM used by nodes."""
    agent = MagicMock()
    agent.invoke.return_value = {"structured_response": MagicMock()}

    agent.ainvoke = AsyncMock(return_value={"structured_response": MagicMock()})
    return agent

@pytest.fixture
def mock_location_data():
    return LocationData(
        city="London",
        state_full="Greater London",
        country_code="gb",
        country_full="United Kingdon"
    )