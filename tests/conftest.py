from pytest import fixture
from schema import CandidateProfile, ListRawJobMatch, RawJobMatch, JobAttributes


@fixture
def mock_python_dev_raw_match():
    """Creates a basic python dev raw match"""
    return RawJobMatch(
        title="Python Dev",
        company_name="Tech Co",
        job_url="url_1",
        description="Coding",
        attributes={"salary": "competitive"},
        location="London",
    )


@fixture
def mock_ai_eng_raw_match():
    return RawJobMatch(
        title="AI Eng",
        company_name="AI Labs",
        job_url="url_2",
        description="Agents",
        attributes={"salary": "high"},
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
                attributes=JobAttributes(salary="£80k", qualifications=["Python"]),
                description="Building cool AI stuff.",
                job_url="https://example.com/job1",
                location="London",
            )
        ]
    )
