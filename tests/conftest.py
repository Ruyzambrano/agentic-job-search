from os import environ as ENV, path

from pytest import fixture
from shutil import rmtree

from src.utils.vector_handler import get_global_jobs_store, get_user_analysis_store
from src.schema import CandidateProfile, ListRawJobMatch, RawJobMatch


@fixture(autouse=True)
def test_db_env():
    """Sets up a clean temp DB for every test run"""

    ENV["CHROMA_PATH"] = "./test_chroma_db"
    yield

    if path.exists("./test_chroma_db"):
        rmtree("./test_chroma_db")

@fixture
def mock_config():
    return  {"configurable": {"user_id": "test_001", "location": "A place", "role": "Theif", "profile_id": "testtest"}}


@fixture
def mock_python_dev_raw_match():
    """Creates a basic python dev raw match"""
    return RawJobMatch(
        title="Python Dev",
        company_name="Tech Co",
        job_url="url_1",
        description="Coding",
        location="London",
        salary_string="Alot",
        schedule_type="Full-time",
        qualifications=["something"],
        posted_at="Yesterday"
    )


@fixture
def mock_ai_eng_raw_match():
    return RawJobMatch(
        title="AI Eng",
        company_name="AI Labs",
        job_url="url_2",
        description="Agents",
        salary_string="Alot",
        schedule_type="Full-time",
        qualifications=["something"],
        posted_at="Yesterday",
        location="Nunya",
    )


@fixture
def mock_state(mock_python_dev_raw_match, mock_ai_eng_raw_match):
    """Provides a basic state with two jobs."""
    return {
        "messages": [],
        "research_data": ListRawJobMatch(
            jobs=[mock_python_dev_raw_match, mock_ai_eng_raw_match]
        ),
    }


@fixture
def mock_candidate_profile():
    return CandidateProfile(
        full_name="Ruy Zambrano",
        job_titles=["Senior Python Developer"],
        key_skills=["Python", "LangChain", "FastAPI"],
        years_of_experience=6,
        current_location="London, UK",
        seniority_level="Senior",
        summary="Expert AI Engineer specializing in agentic workflows.",
        industries=["Fintech", "AI"],
        work_preference="Hybrid",
    )


@fixture
def mock_raw_jobs():
    return ListRawJobMatch(
        jobs=[
            RawJobMatch(
                title="AI Engineer",
                company_name="TechCorp",
                salary_string="Alot",
                schedule_type="Full-time",
                qualifications=["something"],
                posted_at="Yesterday",
                description="Building cool AI stuff.",
                job_url="https://example.com/job1",
                location="London",
            )
        ]
    )

@fixture
def mock_vector_candidate_profile():
    return {
        "ids": ["profile_test_001"],
        "metadatas": [{
            "full_name": "Ruy",
            "job_titles": '["Dev"]',
            "key_skills": '["Python"]',
            "years_of_experience": "5",
            "industries": '[]',
            "summary": "Expert",
            "current_location": "London",
            "work_preference": "Remote"
        }]
    }

@fixture(params=[
    ({"link": "https://google.com/search", "apply_options": [{"link": "https://direct.com"}]}, "https://direct.com"),    
    ({"link": "https://google.com/search", "apply_options": []}, "https://google.com/search"),    
    ({"link": "https://google.com/search"}, "https://google.com/search"),
    ({"link": "https://google.com/search", "apply_options": None}, "https://google.com/search"),
    ({}, "Not specified"),
])
def url_test_case(request):
    """Fixture providing a tuple of (input_data, expected_output)"""
    return request.param
