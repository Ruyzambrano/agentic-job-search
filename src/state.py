from typing import TypedDict, Annotated, Sequence, Optional
from operator import add

from langchain_core.messages import BaseMessage
from src.schema import (
    CandidateProfile,
    RawJobMatchList,
    AnalysedJobMatchListWithMeta,
    PipelineSettings,
)


class AgentState(TypedDict):
    """
    Represents the unified state of the job research pipeline.

    Attributes:
        messages: A history of messages between the user and agents, appended via 'add'.
        cv_data: Structured candidate profile extracted from a CV.
        research_data: The raw job listings found during the research phase.
        writer_data: The final, audited job matches with fit analysis and metadata.
        active_profile_id: The unique database ID for the current candidate session.
        pipeline_settings: Configuration for scrapers, weights, and LLM providers.
    """

    messages: Annotated[Sequence[BaseMessage], add]
    cv_data: Optional[CandidateProfile]
    research_data: Optional[RawJobMatchList]
    writer_data: Optional[AnalysedJobMatchListWithMeta]
    active_profile_id: str
    pipeline_settings: PipelineSettings
