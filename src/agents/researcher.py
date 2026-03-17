"""Researched for jobs using SerpAPI"""

from typing import Dict, Any

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import SearchQueryPlan, RawJobMatchList
from src.services.job_scraper import JobScraperService
from src.services.storage_service import StorageService
from src.utils.text_processing import sanitize_query, filter_redundant_queries
from src.utils.func import log_message


def create_researcher_agent(research_llm):
    system_prompt = """You are a Search Strategist specializing in Recruitment Engineering.

### YOUR GOAL
Generate 3-4 high-powered, Boolean-optimized search queries. Quality over quantity is essential to stay within API limits.

### SEARCH RULES
1. **Consolidation**: Instead of separate queries, use 'OR' groups. 
   - BAD: "Data Engineer", "Data Platform Engineer"
   - GOOD: "('Data Engineer' OR 'Data Platform Engineer' OR 'ETL Developer')"
2. **Boolean Grouping**: Use parentheses to protect logical units, e.g., "(Python AND AWS) OR (Spark AND Java)".
3. **Internal Operators**: You may use AND, OR, and NOT within a query.
4. **Seniority**: If the profile has 7+ years of experience, ALWAYS group seniority terms: "(Senior OR Lead OR Principal)".
5. **No Redundancy**: Do not repeat skills across queries. Query 1 should focus on Job Titles, Query 2 on Niche Skills, Query 3 on the Tech Stack.

### OUTPUT FORMAT
Return a 'SearchQueryPlan' object. Limit the output to a maximum of 4 queries."""
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

    search_location = cfg.get("location") or profile.current_location or "Remote"
    target_roles = cfg.get(
        "role", profile.job_titles[0] if profile.job_titles else "General"
    )

    prompt_content = _build_strategy_prompt(
        profile, target_roles, search_location, settings
    )
    new_message = HumanMessage(content=prompt_content)

    log_message(f"Planning search strategy in {search_location}...")
    response = await agent.ainvoke({**state, "messages": [new_message]})

    query_plan: SearchQueryPlan = response["structured_response"]
    clean_queries = [sanitize_query(q) for q in query_plan.queries][:4]
    final_queries = filter_redundant_queries(clean_queries)

    raw_results = await scraper.run_research(final_queries, search_location)

    synced_jobs = storage.sync_global_library(raw_results, ttl_days=7)

    log_message(f"Research complete! {len(synced_jobs)} unique roles identified.")

    return {
        "messages": [new_message], 
        "research_data": RawJobMatchList(jobs=synced_jobs) 
    }


def _build_strategy_prompt(profile, roles, location, settings) -> str:
    """Helper to keep the node logic clean and focus on the check-list."""
    w = settings.weights
    return (
        f"TARGET ROLES: {roles}\n"
        f"LOCATION: {location}\n"
        f"WEIGHTS: Skills={w.key_skills}, Seniority={w.seniority_weight}\n"
        f"PROFILE: {profile.model_dump_json()}"
    )
