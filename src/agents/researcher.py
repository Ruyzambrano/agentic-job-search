"""Researched for jobs using SerpAPI"""

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import SearchQueryPlan
from src.utils.tools import batch_scrape_jobs, sanitize_query, filter_redundant_queries
from src.utils.vector_handler import (
    get_user_analysis_store,
    get_global_jobs_store,
    fetch_candidate_profile,
    sync_with_global_library,
)
from src.utils.func import log_message
from src.utils.embeddings_handler import get_embeddings


def create_researcher_agent(research_llm):
    system_prompt = """You are an Expert Search Strategist. 

### YOUR GOAL
Analyze the 'CandidateProfile' and generate a list of 8-10 high-intent search queries for the Google Jobs API (SerpApi).

### SEARCH ARCHITECTURE RULES
1. **Diversity**: Create a mix of queries. Some should be specific (Exact Job Title + City), others broader (Key Skills + Region).
2. **Boolean Logic**: Use 'OR' to group similar titles, e.g., "('Data Engineer' OR 'Data Infrastructure') London".
3. **No Postcodes**: Use city or town names only. 
4. **Keyword Extraction**: Identify the 3 most unique key skills in the profile and create at least two queries centered specifically on those skills.
5. **Seniority Mapping**: If the profile indicates 5+ years of experience, include terms like 'Senior', 'Lead', or 'Principal' in 50% of the queries.

### OUTPUT FORMAT
You must return a 'SearchQueryPlan' object. Do not attempt to call any tools. Your job is finished once the queries are generated."""

    return create_agent(
        model=research_llm,
        system_prompt=system_prompt,
        response_format=SearchQueryPlan,
    )


async def researcher_node(state: AgentState, agent, config: RunnableConfig):
    """Creates the node of the agent for workflows"""
    pipeline_settings = config.get("configurable", {}).get("pipeline_settings")

    embeddings = get_embeddings()
    user_store = get_user_analysis_store(embeddings)
    global_store = get_global_jobs_store(embeddings)

    profile_id = state.get("active_profile_id") or config.get("configurable", {}).get(
        "profile_id"
    )

    if not profile_id:
        raise ValueError("No active profile ID found to research against!")

    user_id = config.get("configurable", {}).get("user_id")
    target_location = config.get("configurable", {}).get("location")
    target_roles = config.get("configurable", {}).get("role")

    if not user_id:
        raise ValueError("user_id is required in config to fetch profile.")

    log_message("Getting Profile metadata")

    profile = fetch_candidate_profile(profile_id, user_store)

    search_location = target_location or profile.current_location or "Remote"
    weights = pipeline_settings.weights
    log_message(f"Researching for roles in {search_location}...")
    prompt_content = (
        f"USER PRIORITIES:\n"
        f"- Skill Importance: {weights.key_skills}/100\n"
        f"- Experience Importance: {weights.experience}/100\n"
        f"- Seniority Importance: {weights.seniority_weight}/100\n"
        f"- Retention Risk: {weights.retention_risk}\n\n"
        f"TASK: Create API query strings for target role {target_roles} "
        f"based on this profile: {profile.model_dump_json()}."
    )

    new_message = [HumanMessage(content=prompt_content)]
    response = await agent.ainvoke(
        {**state, "messages": state["messages"] + new_message}
    )

    all_queries = response["structured_response"]
    clean_pool = list(set(sanitize_query(q) for q in all_queries.queries))
    final_queries = filter_redundant_queries(clean_pool)
    jobs = await batch_scrape_jobs(final_queries, search_location, pipeline_settings)
    jobs = sync_with_global_library(global_store, jobs, 7)
    log_message(f"Research complete! Found a total of {len(jobs)} jobs")
    return {"messages": new_message, "research_data": jobs}
