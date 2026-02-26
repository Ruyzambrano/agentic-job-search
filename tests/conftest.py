import pytest
from schema import CandidateProfile, ListRawJobMatch, RawJobMatch, JobAttributes

@pytest.fixture
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
        work_preference="Hybrid"
    )

@pytest.fixture
def mock_raw_jobs():
    return ListRawJobMatch(jobs=[
        RawJobMatch(
            title="AI Engineer",
            company_name="TechCorp",
            attributes=JobAttributes(salary="£80k", qualifications=["Python"]),
            description="Building cool AI stuff.",
            job_url="https://example.com/job1",
            location="London"
        )
    ])