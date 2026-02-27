"""Researched for jobs using SerpAPI"""
import json

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import ListRawJobMatch, CandidateProfile, RawJobMatch
from src.utils.tools import scrape_for_jobs
from src.utils.vector_handler import get_user_analysis_store, get_global_jobs_store


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
5.  **Three searches**: You will only be able to make up to three searches. use a wide range of terms for a wide scope of searches"""

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
    user_id = config.get("configurable", {}).get("user_id")
    target_location = config.get("configurable", {}).get("location")

    if not user_id:
        raise ValueError("user_id is required in config to fetch profile.")
    
    print("LOG: Getting Vector metadata")

    user_store = get_user_analysis_store()
    profile_record = user_store.get(ids=[f"profile_{user_id}"])
    
    if not profile_record:
        raise ValueError(f"No profile found for {user_id}. Run CV parser first")

    meta = profile_record["metadatas"][0]

    for field in ["job_titles", "key_skills", "industries"]:
        if field in meta and isinstance(meta[field], str):
            meta[field] = json.loads(meta[field])
    
    profile = CandidateProfile(**meta)
    search_location = target_location or profile.current_location or "Remote"
    print(f"Researching for roles in {search_location}...")
    prompt_content = (
            f"Find jobs in {search_location} for this profile: {profile.summary}. "
            f"Target roles: {profile.job_titles}. Skills: {profile.key_skills}."
        )
    new_message = [HumanMessage(content=prompt_content)]
    response = agent.invoke({**state, "messages": state["messages"] + new_message})

    raw_results = response["structured_response"]
    global_store = get_global_jobs_store()
    final_jobs = []
    seen_urls = set()

    for job in raw_results.jobs:
        if job.job_url not in seen_urls:
            existing = global_store.get(ids=[job.job_url])
            seen_urls.add(job.job_url)

            if not existing.get("ids"):
                global_store.add_texts(
                    texts=[job.description],
                    metadatas=[job.model_dump()],
                    ids=[job.job_url]
                )
                final_jobs.append(job)
                print(f"LOG: New job saved to global library: {job.title}")
                
            else:
                cached_metadata = existing['metadatas'][0]
                if isinstance(cached_metadata.get("qualifications"), str):
                    cached_metadata["qualifications"] = json.loads(cached_metadata["qualifications"])
                
                cached_job = RawJobMatch(**cached_metadata)
                final_jobs.append(cached_job)
                print(f"DEBUG: Using cached global data for: {job.title}")

    print(f"Research complete! Found a total of {len(final_jobs)} jobs")
    return {"messages": new_message, "research_data": ListRawJobMatch(jobs=final_jobs)}
