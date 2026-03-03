from langchain_core.messages import BaseMessage

from typing import TypedDict, Annotated, Sequence, Optional
from operator import add

from src.schema import CandidateProfile, ListRawJobMatch, AnalysedJobMatchListWithMeta


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]
    cv_data: Optional[CandidateProfile]
    research_data: Optional[ListRawJobMatch]
    writer_data: Optional[AnalysedJobMatchListWithMeta]
    active_profile_id: str
