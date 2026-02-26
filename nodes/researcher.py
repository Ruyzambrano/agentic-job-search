from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.rate_limiters import InMemoryRateLimiter

from state import AgentState
from schema import ListRawJobMatch
from nodes.utils.tools import scrape_for_jobs


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

def deduplicate_jobs(jobs_list):
    seen_ids = set()
    unique_jobs = []
    
    for job in jobs_list.jobs:
        fingerprint = f"{job.title}-{job.company_name}-{job.location}".lower().strip()
        
        if fingerprint not in seen_ids:
            seen_ids.add(fingerprint)
            unique_jobs.append(job)
            
    return ListRawJobMatch(jobs=unique_jobs)

def researcher_node(state: AgentState, agent):
    """Creates the node of the agent for workflows"""
    print("Researcher is researching...")
    new_message = [
        HumanMessage(
            content="Find relevant jobs for the candidate profile where they would be a top applicant in a relevant role in London"
        )
    ]
    response = agent.invoke({**state, "messages": state["messages"] + new_message})
    clean_data = deduplicate_jobs(response["structured_response"])
    print(
        f"Research complete! Found a total of {len(clean_data.jobs)} jobs"
    )
    return {
        "messages": new_message,
        "research_data": clean_data
    }
