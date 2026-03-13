from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


class WorkSetting(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "On-site"
    UNKNOWN = "Unknown"

class SeniorityLevel(str, Enum):
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"
    EXECUTIVE = "Executive"
    NOT_SPECIFIED = "Not specified"

# --- Base Models ---

class JobBase(BaseModel):
    """Shared fields for both Raw and Analysed jobs to maintain consistency."""
    title: str = Field(..., min_length=1)
    company: str = Field(..., alias="company_name") # Handles 'company' vs 'company_name'
    location: str
    job_url: str 
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    class Config:
        populate_by_name = True

class RawJobMatch(JobBase):
    salary_string: str = "Not specified"
    work_setting: WorkSetting = WorkSetting.UNKNOWN
    schedule_type: str = "Unknown"
    is_contract: bool = False
    qualifications: List[str] = Field(default_factory=list)
    description: str = Field(description="Summarized or original job text")
    raw_description: Optional[str] = Field(default="", description="The full, unedited text")
    posted_at: str = ""

class ListRawJobMatch(BaseModel):
    jobs: List[RawJobMatch] = Field("A list of raw job match objects")
class AnalysedJobMatch(JobBase):
    job_summary: str
    qualifications: List[str]
    attributes: List[str]
    key_skills: List[str] = Field(default_factory=list)
    top_applicant_score: int = Field(ge=0, le=100)
    top_applicant_reasoning: str
    
    @field_validator('top_applicant_score')
    @classmethod
    def validate_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v
class AnalysedJobMatchWithMeta(AnalysedJobMatch):

    analysed_at: Optional[str] = Field(
        description="Timestamp of analysis",
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_role: Optional[str] = Field(description="The role that the agent was prioritising", default="")
    target_location: Optional[str] = Field(description="The location the agent was prioritising", default="")

class AnalysedJobMatchList(BaseModel):
    jobs: List[AnalysedJobMatch] = Field(description="A list of job matches")

class AnalysedJobMatchListWithMeta(BaseModel):
    jobs: List[AnalysedJobMatchWithMeta] = Field(description="A list of job matches with metada")
class CandidateProfile(BaseModel):
    full_name: str
    job_titles: List[str]
    key_skills: List[str]
    years_of_experience: int = Field(ge=0)
    current_location: Optional[str] = None
    seniority_level: SeniorityLevel = SeniorityLevel.NOT_SPECIFIED
    summary: str
    industries: List[str]
    work_preference: WorkSetting = WorkSetting.UNKNOWN


class SearchQueryPlan(BaseModel):
    queries: list[str] = Field(description="A list of 5-10 optimized Google Jobs search strings")
class AgentWeights(BaseModel):
    key_skills: int = Field(default=75)
    experience: int = Field(default=50)
    location: int = Field(default=25)
    seniority_weight: int = Field(default=75)
    retention_risk: bool = Field(default=True)


class ScraperSettings(BaseModel):
    distance_param: int = Field(default=40)
    region: str = Field(default="uk")
    max_jobs: int = 20


class ApiSettings(BaseModel):
    ai_provider: str = ""

    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    serpapi_key: str = ""
    rapidapi_key: str = ""

    use_google: bool = False
    use_linkedin: bool = False
    free_tier: bool = True

    models: dict = Field(default_factory=lambda: {
        "gemini": {"reader": "gemini-2.5-flash-lite","researcher": "gemini-2.5-flash", "writer": "gemini-3-flash-preview"},
        "openai": {"reader": "gpt-4o-mini", "researcher": "gpt-5", "writer": "gpt-4o"},
        "claude": {"reader": "claude-3-5-haiku", "researcher": "claude-3-5-sonnet", "writer": "claude-3-5-sonnet"}
    })


class PipelineSettings(BaseModel):
    weights: AgentWeights = Field(default_factory=AgentWeights)
    scraper_settings: ScraperSettings = Field(default_factory=ScraperSettings)
    api_settings: ApiSettings = Field(default_factory=ApiSettings)


