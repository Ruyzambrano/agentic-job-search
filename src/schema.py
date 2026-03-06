from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class RawJobMatch(BaseModel):
    job_url: str = Field(description="The unique URL (Primary Key)")
    title: str = Field(description="Job title")
    company_name: str = Field(default="Unknown", description="Company name")
    location: str = Field(description="Geographic location")

    salary_min: Optional[int] = Field(
        default=None, description="Annualized min salary (e.g. 60000)"
    )
    salary_max: Optional[int] = Field(
        default=None, description="Annualized max salary (e.g. 80000)"
    )
    salary_string: str = Field(
        default="Not specified",
        description="Raw text (e.g. '£500/day' or 'Competitive')",
    )

    work_setting: Literal["Remote", "Hybrid", "On-site", "Unknown"] = "Unknown"
    schedule_type: Optional[str] = Field(
        default="Unknown", description="Full-time, Part-time, Contract"
    )
    is_contract: bool = False

    qualifications: List[str] = Field(
        default_factory=list, description="Extracted tech stack/skills"
    )
    description: str = Field(description="Summarized job text")
    posted_at: str = Field(default="", description="Date string from listing")


class ListRawJobMatch(BaseModel):
    jobs: List[RawJobMatch] = Field("A list of raw job match objects")

class SearchQueryPlan(BaseModel):
    queries: list[str] = Field(description="A list of 5-10 optimized Google Jobs search strings")
    reasoning: str = Field(description="Why these specific terms were chosen")
class AnalysedJobMatch(BaseModel):
    title: str = Field(description="The title of the job listing")
    company: str = Field(
        description="The name of the company")
    job_url: str = Field(description="The URL of the job advert")
    location: str = Field(
        description="The location of the role, as granular as possible"
    )
    office_days: Optional[str] = Field(
        description="The number of days in the office per week/month/year",
        default="Not specified",
    )
    job_summary: str = Field(description="The summarised text of the job description")
    qualifications: List[str] = Field(
        description="A list of qualifications needed for the role"
    )
    attributes: List[str] = Field(
        description="A list of key attributes of the role, like 'full-time', 'hybrid', 'permanent'"
    )
    tech_stack: List[str] = Field(
        description="The key technologies that the job requires"
    )
    salary_min: Optional[int] = Field(
        description="The minimum salary range by yearly salary", default=None
    )
    salary_max: Optional[int] = Field(
        description="The maximum salary range by yearly salary", default=None
    )
    top_applicant_score: int = Field(
        description="A score from 0 to 100 ranking how closesly the applicant matches the role based on their cv"
    )
    top_applicant_reasoning: str = Field(
        description="A rationale why the candidate fits the role"
    )


class AnalysedJobMatchWithMeta(AnalysedJobMatch):
    analysed_at: Optional[str] = Field(
        description="Timestamp of analysis",
        default_factory=lambda: datetime.now().isoformat(),
    )
    target_role: Optional[str] = Field(
        description="The role that the agent was prioritising", default=""
    )
    target_location: Optional[str] = Field(
        description="The location the agent was prioritising", default=""
    )


class AnalysedJobMatchList(BaseModel):
    jobs: List[AnalysedJobMatch] = Field(description="A list of job matches")


class AnalysedJobMatchListWithMeta(BaseModel):
    jobs: List[AnalysedJobMatchWithMeta] = Field(
        description="A list of job matches with metada"
    )


class CandidateProfile(BaseModel):
    full_name: str = Field(description="The candidate's full name")
    job_titles: List[str] = Field(
        description="Target job titles (e.g., ['Senior Python Developer', 'Backend Engineer'])"
    )
    key_skills: List[str] = Field(
        description="Top 5-10 technical or soft skills found in the CV"
    )
    years_of_experience: int = Field(
        description="Total years of relevant professional experience"
    )
    current_location: Optional[str] = Field(description="City and country of residence")
    seniority_level: str = Field(
        description="e.g., Junior, Mid, Senior, Lead, or Executive",
        default="Not spefified",
    )
    summary: str = Field(
        description="A 2-3 sentence professional summary of the candidate's career"
    )
    industries: List[str] = Field(
        description="Industries they have worked in (e.g., ['Fintech', 'Healthcare'])"
    )
    work_preference: str = Field(description="Remote, Hybrid, or On-site if specified")


class AgentWeights(BaseModel):
    tech_stack: int = Field(default=75)
    experience: int = Field(default=50)
    location: int = Field(default=25)
    seniority_weight: int = Field(default=75)
    retention_risk: bool = Field(default=True)

class ScraperSettings(BaseModel):
    distance_param: int = Field(default=40)
    max_results: int = Field(default=10)
    region: str = Field(default="uk")

class ApiSettings(BaseModel):
    ai_provider: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    serpapi_key: str = ""
    slack_webhook: str = ""
    gemini_reader: str = "gemini-2.5-flash-lite"
    gemini_writer: str = "gemini-3-flash-preview"
    gemini_researcher: str = "gemini-2.5-flash"
    gemini_embedding: str = "gemini-embedding-001"

    openai_reader: str = "gpt-4o-mini"
    openai_writer: str = "gpt-4o"
    openai_researcher: str = "gpt-5"
    
    anthropic_api_key: str = ""
    claude_reader: str = "claude-3-5-haiku"
    claude_writer: str = "claude-3-5-sonnet"
    claude_researcher: str = "claude-3-5-sonnet"
    
class PipelineSettings(BaseModel):
    weights: AgentWeights = Field(default_factory=AgentWeights)
    scraper_settings: ScraperSettings = Field(default_factory=ScraperSettings)
    api_settings: ApiSettings = Field(default_factory=ApiSettings)