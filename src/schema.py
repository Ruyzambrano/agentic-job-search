from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class WorkSetting(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "On-site"
    UNKNOWN = "Unknown"


class SeniorityLevel(str, Enum):
    JUNIOR = "Junior"
    MID = "Mid"
    MID_SENIOR = "Mid-Senior level"
    SENIOR = "Senior"
    LEAD = "Lead"
    EXECUTIVE = "Executive"
    NOT_SPECIFIED = "Not specified"


class JobBase(BaseModel):
    """Shared fields for both Raw and Analysed jobs to maintain consistency."""
    model_config = ConfigDict(populate_by_name=True)
    title: str = Field(..., min_length=1)
    company: str = Field(..., alias="company_name")
    location: str = Field(description="The location of the role")
    job_url: str = Field(description="The url for applicants to apply")
    salary_min: Optional[int] = Field(
        default=None, description="The minimum salary offered, if it is available"
    )
    salary_max: Optional[int] = Field(
        default=None, description="The maximum salary offered, if it is available"
    )
    qualifications: List[str] = Field(
        default_factory=list, description="Qualifications needed for the role"
    )
    responsibilities: List[str] = Field(
        default_factory=list, description="Job responsibilities"
    )
    benefits: List[str] = Field(
        default_factory=list, description="Benefits offered for employees"
    )
    seniority_level: SeniorityLevel = Field(
        SeniorityLevel.NOT_SPECIFIED, description="The seniority level of the role"
    )
    description: str = Field(description="Summarized or original job text", default="")
    is_contract: bool = False
    work_setting: WorkSetting = Field(
        default=WorkSetting.UNKNOWN, description="Remote/Hybrid/On Site"
    )
    schedule_type: str = "Unknown"


class RawJobMatch(JobBase):
    salary_string: str = "Not specified"
    raw_description: Optional[str] = Field(
        default="", description="The full, unedited text"
    )
    posted_at: str = ""


class RawJobMatchList(BaseModel):
    jobs: List[RawJobMatch] = Field("A list of raw job match objects")


class AnalysedJobMatch(JobBase):
    job_summary: str = Field(
        description="A concise 2-3 sentence overview of the role, focus on value proposition."
    )
    attributes: List[str] = Field(
        description="A list of key attributes of the role, like 'full-time', 'hybrid', 'permanent'"
    )
    office_days: Optional[str] = Field(
        description="The number of days in the office per week/month/year",
        default="Not specified",
    )
    key_skills: List[str] = Field(
        default_factory=list,
        description="Hard technical skills or certifications explicitly mentioned or strongly implied.",
    )
    top_applicant_score: int = Field(
        ge=0,
        le=100,
        description="A score from 0-100 representing how well the candidate matches this specific job.",
    )
    top_applicant_reasoning: str = Field(
        ...,
        description="A detailed explanation of why the candidate received their score, highlighting gaps and strengths.",
    )

    @field_validator("top_applicant_score", mode="before")
    @classmethod
    def validate_score(cls, v):
        try:
            val = int(v)
            return max(0, min(100, val))
        except (ValueError, TypeError):
            return 0


class AnalysedJobMatchWithMeta(AnalysedJobMatch):

    analysed_at: Optional[str] = Field(
        description="Timestamp of analysis",
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
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
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    full_name: str = Field(..., description="The candidate's legal name")
    job_titles: List[str] = Field(
        default_factory=list, 
        description="List of roles the candidate has held or is targeting"
    )
    key_skills: List[str] = Field(
        default_factory=list, 
        description="Core technical and soft skills"
    )
    years_of_experience: int = Field(
        0, ge=0, 
        description="Total years of professional experience"
    )
    current_location: Optional[str] = Field(
        None, 
        description="City and country of residence"
    )
    seniority_level: SeniorityLevel = Field(
        default=SeniorityLevel.NOT_SPECIFIED,
        description="Target seniority level (e.g., Mid-Senior, Lead)"
    )
    summary: str = Field(
        "A summary of the candidate's profile",
        description="Professional biography or executive summary"
    )
    industries: List[str] = Field(
        default_factory=list, 
        description="Sectors the candidate has worked in (e.g., Fintech, E-commerce)"
    )
    work_preference: WorkSetting = Field(
        default=WorkSetting.UNKNOWN,
        description="Preference for Remote, Hybrid, or On-site"
    )

class SearchStep(BaseModel):
    title_stems: List[str] = Field(
        description="The root/stem of the job titles to maximize matches."
    )
    must_have_skills: List[str] = Field(
        description="The 1-2 non-negotiable tools or skills for this segment."
    )
    reasoning: str = Field(
        description="Think step-by-step about the talent segment you are targeting here."
    )

class SearchQueryPlan(BaseModel):
    steps: List[SearchStep] = Field(description="3-4 distinct search strategies.")


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

    models: dict = Field(
        default_factory=lambda: {
            "gemini": {
                "reader": "gemini-2.5-flash-lite",
                "researcher": "gemini-2.5-flash",
                "writer": "gemini-3-flash-preview",
            },
            "openai": {
                "reader": "gpt-4o-mini",
                "researcher": "gpt-5",
                "writer": "gpt-4o",
            },
            "claude": {
                "reader": "claude-3-5-haiku",
                "researcher": "claude-3-5-sonnet",
                "writer": "claude-3-5-sonnet",
            },
        }
    )


class PipelineSettings(BaseModel):
    weights: AgentWeights = Field(default_factory=AgentWeights)
    scraper_settings: ScraperSettings = Field(default_factory=ScraperSettings)
    api_settings: ApiSettings = Field(default_factory=ApiSettings)


class LocationData(BaseModel):
    """SOP: A universal location container for all job APIs."""
    city: str      
    state_full: Optional[str] 
    country_full: str     
    country_code: str   
    
    @property
    def linkedin_string(self) -> str:
        """Full hierarchy: 'London, England, United Kingdom'"""
        parts = [self.city, self.state_full, self.country_full]
        return ", ".join([p for p in parts if p])

    @property
    def google_string(self) -> str:
        """City level as per SerpApi docs: 'London'"""
        return self.city