"""Researched for jobs using SerpAPI"""

from typing import Dict, Any

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import SearchQueryPlan, RawJobMatchList, SearchStep, LocationData
from src.services.job_scraper import JobScraperService
from src.services.storage_service import StorageService
from src.utils.text_processing import filter_redundant_queries
from src.utils.func import log_message


def create_researcher_agent(research_llm):
    system_prompt = """## ROLE
You are a Universal Recruitment Strategist. Your goal is to map out a search architecture for any given job role by identifying its core titles, synonymous "adjacent" roles, and non-negotiable technical anchors.

## OBJECTIVE
Generate a `SearchQueryPlan` consisting of 3-4 distinct `SearchStep` objects. Each step must target a specific "talent segment" (e.g., Core, Senior/Lead, Specialist, or Adjacent).

## THE "STEMMING" PROTOCOL (CRITICAL)
To maximize reach across different search engine algorithms, you must provide **Word Stems** rather than full words for job titles. 
- **Rule**: Provide the root of the word that captures all variations (singular, plural, and gerund).
- **Example (Engineering)**: Use 'Engin' (matches Engineer, Engineering, Engineers).
- **Example (Management)**: Use 'Manag' (matches Manager, Management, Managing).
- **Example (Nursing)**: Use 'Nurs' (matches Nurse, Nursing).
- **Example (Analysis)**: Use 'Analyt' (matches Analyst, Analytics, Analytical).

## GUIDELINES FOR SEARCH STEPS
1. **Title Stems**: Provide a list of 2-3 root stems. DO NOT include symbols like :*, |, &, or !.
2. **Must-Have Skills**: Provide 1-2 "Anchor" keywords (tools, certifications, or specific hard skills) that define that segment.
3. **Segmentation Strategy**:
   - **Step 1 (The Core)**: The most common industry-standard stems.
   - **Step 2 (The Specialist)**: Stems and skills focused on a niche or high-value sub-set.
   - **Step 3 (The Adjacent)**: Titles that do the same work but under different names.
   
## ATTRIBUTE WEIGHTS (CONSTRAINT STRENGTH)
You will receive "WEIGHTS" (Scale 0-100). Use them to determine how STRICT your filters should be:

1. **High Skills Weight (>70)**: 
   - The stack is non-negotiable. 
   - SOP: Use very specific `must_have_skills`. Do not "guess" adjacent tools.
   
2. **Low Skills Weight (<30)**: 
   - The stack is flexible. 
   - SOP: Use broad skills (e.g., 'Cloud' instead of 'AWS Lambda') to increase volume.

3. **High Seniority Weight (>70)**: 
   - The level is non-negotiable. 
   - SOP: Use explicit seniority stems that match the profile (e.g., if they have 3 years, use 'Mid' or 'Senior'). Do NOT return entry-level roles.

4. **Low Seniority Weight (<30)**: 
   - The level is flexible. 
   - SOP: Focus on the job function only. Omit seniority stems to cast a wider net.

## FORMATTING
Return a JSON object matching the `SearchQueryPlan` schema."""
    return create_agent(
        model=research_llm,
        system_prompt=system_prompt,
        response_format=SearchQueryPlan,
    )


async def researcher_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Orchestrates the discovery phase:
    1. Fetches candidate profile from StorageService.
    2. Generates search strategy via LLM.
    3. Executes scraper via JobScraperService.
    4. Syncs results to Global Library.
    """
    cfg = config.get("configurable", {})
    settings = cfg.get("pipeline_settings")
    agent = cfg.get("researcher_agent")
    storage: StorageService = cfg.get("storage_service")
    scraper = cfg.get("job_scraper") or JobScraperService(settings)
    
    profile_id = state.get("active_profile_id") or cfg.get("profile_id")
    if not profile_id:
        raise ValueError("active_profile_id is missing. Cannot research.")

    log_message("Retrieving profile for strategy planning...")
    profile = storage.fetch_candidate_profile(profile_id)

    search_location: LocationData = cfg.get("location")
    target_roles = cfg.get(
        "role", profile.job_titles[0] if profile.job_titles else "General"
    )

    prompt_content = _build_strategy_prompt(
        profile, target_roles, search_location, settings
    )
    new_message = HumanMessage(content=prompt_content)

    log_message(f"Planning search strategy in {search_location.city}...")
    response = await agent.ainvoke({**state, "messages": [new_message]})

    query_plan: SearchQueryPlan = response["structured_response"]
    
    final_queries = filter_redundant_queries(query_plan.steps, threshold=80)

    log_message(f"Created {len(final_queries)} job queries")

    raw_results = await scraper.run_research(final_queries, search_location)

    synced_jobs = storage.sync_global_library(raw_results, ttl_days=7)

    log_message(f"Research complete! {len(synced_jobs)} unique roles identified.")

    return {
        "messages": [new_message], 
        "research_data": RawJobMatchList(jobs=[j.model_dump() for j in synced_jobs])
    }


def _build_strategy_prompt(profile, roles, location, settings) -> str:
    """Helper to keep the node logic clean and focus on the check-list."""
    w = settings.weights
    return (
        f"TARGET ROLES: {roles}\n"
        f"CANDIDATE EXPERIENCE: {profile.years_of_experience} years\n"
        f"LOCATION: {location}\n"
        f"--- SEARCH WEIGHTS (0-100 Scale) ---\n"
        f"Skills Strictness: {w.key_skills}\n"
        f"Seniority Strictness: {w.seniority_weight}\n"
        f"------------------------------------\n"
        f"PROFILE: {profile.model_dump_json()}"
    )
