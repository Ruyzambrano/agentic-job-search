"""Parses a CV and returns a CandidateProfile while also writing the profile to a DB"""

from typing import Dict, Any
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import CandidateProfile
from src.services.storage_service import StorageService
from src.utils.func import log_message


def create_cv_parser_agent(cv_parser_llm):
    """Creates a research agent that can read a cv and get relevant jobs"""
    system_prompt = """### ROLE
You are a precise HR Data Extraction Engine. Your sole purpose is to transform raw text into a structured JSON schema. You operate with 100% fidelity to the source text.

### OPERATIONAL CONSTRAINTS
- NO PLACEHOLDERS: Never use names like "John Doe", "Jane Smith", or "N/A" unless they are explicitly written in the CV.
- ESCAPE HATCH: If a specific data point is missing, return an empty string (""). 
- NO CREATIVITY: Do not infer skills. 
- SOURCE ONLY: Your knowledge base is ONLY the provided text.

### EXTRACTION GUIDELINES
1. **Name Extraction**: Find the candidate name associated with contact info.
2. **Title Normalization**: Map to standard industry terms.
3. **Skill Prioritization**: Focus on technical "Hard Skills".
4. **Seniority Logic**: 0-3: Junior, 4-8: Mid, 9+: Senior, Mgmt: Lead/Executive.

### FORMATTING
Return ONLY the JSON object."""

    return create_agent(
        model=cv_parser_llm,
        system_prompt=system_prompt,
        response_format=CandidateProfile,
    )


async def cv_parser_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Orchestrates:
    1. Retrieval of existing profile (if ID provided)
    2. LLM Parsing of raw CV text
    3. Storage of new profile via StorageService
    """
    cfg = config.get("configurable", {})
    user_id = cfg.get("user_id")

    agent = cfg.get("cv_parser_agent")
    storage: StorageService = cfg.get("storage_service")

    if not user_id:
        raise ValueError("User ID required to process CV.")

    active_id = state.get("active_profile_id") or cfg.get("active_profile_id")

    if active_id:
        log_message(f"Using existing profile: {active_id}")
        profile = storage.fetch_candidate_profile(active_id)
        return {"cv_data": profile, "active_profile_id": active_id}

    log_message("Starting CV Extraction...")

    result = await agent.ainvoke(state)
    cv_data: CandidateProfile = result["structured_response"]

    log_message("Parsing complete. Persisting profile...")
    new_id = storage.save_candidate_profile(user_id, cv_data)

    return {"cv_data": cv_data, "active_profile_id": new_id}
