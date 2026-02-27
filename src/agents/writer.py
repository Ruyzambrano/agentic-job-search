"""Analyses the returned jobs based on the candidate profile"""
import json

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig

from src.utils.vector_handler import get_global_jobs_store, check_analysis_cache, get_user_analysis_store, fetch_candidate_profile, save_job_analyses
from src.schema import AnalysedJobMatch
from src.schema import AnalysedJobMatchList
from src.state import AgentState


def create_writer_agent(writer_llm):
    """Creates a writer agent"""
    system_prompt = """You are an Expert Career Advisor and Placement Specialist.
Your task is to take a list of job openings and a Candidate Profile, then analyze the 'fit' for each role.

### YOUR INPUTS
1. **Candidate Profile**: A structured summary of the user's skills and experience.
2. **Job List**: A raw list of scraped job openings in London.

### ANALYSIS CRITERIA
For every job, you must infer and explain:
- **The "Why"**: Why does this candidate's specific background make them a top 1% fit for this role?
- **The "Gap"**: What specific skills or experiences is the candidate missing for this role? Be honest but constructive.
- **Match Score**: A percentage (0-100%) based on skills, seniority, and location.

### YOUR OUTPUTS
- You MUST return an 'AnalsedJobMatchList'

### OUTPUT RULES
- You MUST return your analysis in the 'AnalysedJobMatchList' format.
- Focus on the Top 5 most relevant roles.
- Use professional, encouraging, yet data-driven language.
- DO NOT invent details about the company that aren't in the job description."""
    writer_llm.rate_limiter = InMemoryRateLimiter(
        requests_per_second=0.09, check_every_n_seconds=0.1, max_bucket_size=1
    )
    return create_agent(
        model=writer_llm,
        system_prompt=system_prompt,
        response_format=AnalysedJobMatchList,
    )


def writer_node(state: AgentState, agent, config: RunnableConfig):
    """Analyses jobs against profile with local caching logic."""
    print("Analysing jobs against your profile...")
    
    global_jobs_store = get_global_jobs_store()
    user_store = get_user_analysis_store()
    
    user_id = config.get("configurable", {}).get("user_id")
    profile_id = state.get("active_profile_id") or config.get("configurable", {}).get("profile_id")
    
    if not profile_id or not user_id:
        raise ValueError("Missing profile_id or user_id. Cannot perform analysis.")
    
    research_jobs = state.get("research_data").jobs
   
    new_message_obj = None

    final_analyses, new_jobs_to_process = check_analysis_cache(user_store, research_jobs, profile_id)
    
    if new_jobs_to_process:
        print(f"LOG: Cache Miss: Analyzing {len(new_jobs_to_process)} new jobs...")
        job_list_context = ""

        for i, job in enumerate(new_jobs_to_process):
            job_list_context += f"\nNEW JOB #{i+1}:\n{job.model_dump_json()}"

        new_message_obj = HumanMessage(
            content=f"Analyse these NEW jobs: {job_list_context}\n\n"
            f"Return the structured list. CRITICAL: Use the EXACT 'URL' provided."
        )

        response = agent.invoke(
            {**state, "messages": state["messages"] + [new_message_obj]}
        )
        llm_results = response["structured_response"].jobs

        save_job_analyses(user_store, llm_results, user_id, profile_id)
        final_analyses.extend(llm_results)
    else:
        print("LOG: 🚀 All jobs retrieved from cache. Zero tokens consumed.")

    print("Analysis complete!")

    return {
        "messages": [new_message_obj] if new_message_obj else [],
        "writer_data": AnalysedJobMatchList(jobs=final_analyses),
    }
