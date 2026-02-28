"""Researched for jobs using SerpAPI"""
import json

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import ListRawJobMatch
from src.utils.tools import scrape_for_jobs
from src.utils.vector_handler import get_user_analysis_store, get_global_jobs_store, fetch_candidate_profile, sync_with_global_library
from src.utils.func import log_message

def create_researcher_agent(research_llm):
    """Creates a research agent that can read a cv and get relevant jobs"""
    system_prompt = """You are a Recruitment Search Engine. 

### YOUR DATA SOURCE
You have been provided with a structured 'CandidateProfile'. Use the job_title OR key_skills fields to create high-intent searches where the candidate profile would be a top candidate.

### YOUR MANDATE
1.  **Search Immediately**: Your first response MUST be a call to 'scrape_for_jobs'. 
2.  **Use OR boolean searches**: When constructing the search parameters, use OR over AND
3.  **No Internal Monologue**: Do not explain your reasoning. Just call the tool.
4.  **Halt**: Once you have called the tool, stop and wait for the results.
5.  **Three searches**: You will only be able to make up to three searches. use a wide range of terms for a wide scope of searches
6.  **NO POSTCODES**: No postcodes should be used in your searches, only city names. If in doubt, use the closest large town or city for your search"""

    research_llm.rate_limiter = InMemoryRateLimiter(
        requests_per_second=0.1, check_every_n_seconds=0.1
    )
    return create_agent(
        model=research_llm,
        system_prompt=system_prompt,
        tools=[scrape_for_jobs],
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="scrape_for_jobs", thread_limit=3, run_limit=3
            )
        ],
        response_format=ListRawJobMatch,
    )


def researcher_node(state: AgentState, agent, config: RunnableConfig):
    """Creates the node of the agent for workflows"""
    user_store = get_user_analysis_store()
    global_store = get_global_jobs_store()
    profile_id = state.get("active_profile_id") or config.get("configurable", {}).get("profile_id")

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

    log_message(f"Researching for roles in {search_location}...")
    prompt_content = (
            f"Find jobs in {search_location} for this profile: {profile.summary}. "
            f"Target roles: {target_roles} {profile.job_titles}. Skills: {profile.key_skills}."
        )
    new_message = [HumanMessage(content=prompt_content)]
    response = agent.invoke({**state, "messages": state["messages"] + new_message})

    raw_results = response["structured_response"]

    final_jobs = sync_with_global_library(global_store, raw_results)

    log_message(f"Research complete! Found a total of {len(final_jobs)} jobs")
    return {"messages": new_message, "research_data": ListRawJobMatch(jobs=final_jobs)}
