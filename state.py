from langchain_core.messages import BaseMessage

from typing import TypedDict, Annotated, Sequence, Optional, List
from operator import add

from schema import CandidateProfile, ListRawJobMatch, AnalysedJobMatchList

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]
    cv_data: Optional[CandidateProfile]
    research_data: Optional[ListRawJobMatch]
    writer_data: Optional[AnalysedJobMatchList]
