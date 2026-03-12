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
    system_prompt = """You are a Search Strategist specializing in Recruitment Engineering.

### YOUR GOAL
Generate 3-4 high-powered, Boolean-optimized search queries. Quality over quantity is essential to stay within API limits.

### SEARCH RULES
1. **Consolidation**: Instead of separate queries, use 'OR' groups. 
   - BAD: "Data Engineer", "Data Platform Engineer"
   - GOOD: "('Data Engineer' OR 'Data Platform Engineer' OR 'ETL Developer')"
2. **Boolean Grouping**: Use parentheses to protect logical units, e.g., "(Python AND AWS) OR (Spark AND Java)".
3. **Internal Operators**: You may use AND, OR, and NOT within a query.
4. **Seniority**: If the profile has 5+ years of experience, ALWAYS group seniority terms: "(Senior OR Lead OR Principal)".
5. **No Redundancy**: Do not repeat skills across queries. Query 1 should focus on Job Titles, Query 2 on Niche Skills, Query 3 on the Tech Stack.

### OUTPUT FORMAT
Return a 'SearchQueryPlan' object. Limit the output to a maximum of 4 queries."""
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
            f"- Retention Risk Level: {weights.retention_risk}\n\n"
            
            f"TARGET ROLES:\n"
            f"- Anchor: {target_roles}\n"
            f"- Instructions: Use the anchor as a base but include synonymous or adjacent titles found in the profile.\n\n"
            
            f"LOCATION: {search_location}\n\n"
            
            f"TASK:\n"
            f"Create exactly 3-4 high-density Boolean API query strings. "
            f"Use grouping parentheses for all OR clusters to ensure search engine precision. "
            f"Example format: (Senior OR Lead) AND ('Data Engineer' OR 'Analytics Engineer') AND Python\n\n"
            
            f"PROFILE DATA (JSON): {profile.model_dump_json()}."
   )

    new_message = [HumanMessage(content=prompt_content)]
    response = await agent.ainvoke(
        {**state, "messages": state["messages"] + new_message}
    )

    query_plan = response["structured_response"]
    clean_pool = [sanitize_query(q) for q in query_plan.queries][:3]
    final_queries = filter_redundant_queries(clean_pool)
    jobs = await batch_scrape_jobs(final_queries, search_location, pipeline_settings)
    jobs = sync_with_global_library(global_store, jobs, 7)
    log_message(f"Research complete! Found a total of {len(jobs)} jobs")
    return {"messages": new_message, "research_data": jobs}
