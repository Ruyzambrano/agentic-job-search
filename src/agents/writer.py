"""Analyses the returned jobs based on the candidate profile"""
import asyncio

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig

from src.utils.vector_handler import (
    check_analysis_cache,
    get_user_analysis_store,
    save_job_analyses,
)
from src.schema import (
    AnalysedJobMatchListWithMeta,
    AnalysedJobMatchList,
    AnalysedJobMatchWithMeta,
    PipelineSettings,
)
from src.state import AgentState
from src.utils.func import log_message
from src.utils.embeddings_handler import get_embeddings


def create_writer_agent(writer_llm, free_tier:bool = False):
    """Creates a writer agent"""

    system_prompt = """You are a Critical Recruitment Auditor. Your task is to perform a high-fidelity "Gap Analysis" between a Candidate Profile and a list of job openings.

### YOUR MANDATE
1. ANALYZE EVERY JOB: You must return an analysis for EVERY job provided in the input list. Do not truncate the list. Do not focus only on the "best" ones.
2. BE HYPER-CRITICAL: Your Match Score must be conservative. A 95%+ score should be reserved for candidates who meet 100% of the tech stack AND seniority requirements. 
3. DETECT OVER-QUALIFICATION/UNDER-QUALIFICATION: If a candidate has 10 years of experience and the job is "Junior," the score should be LOW due to "Retention Risk."

### ANALYSIS CRITERIA
For every job, provide:
- The "Why": Specific evidence from the profile that matches the job requirements.
- The "Gap": Explicitly list missing technologies, industry experience, or seniority mismatches. If a skill isn't in the profile, assume they DON'T have it.
- Match Score: 
    * 85-100%: Perfect tech stack match, correct seniority, industry alignment.
    * 60-84%: Strong match but missing 1-2 secondary tools or slightly different industry background.
    * 0-59%: Missing core "Must-Have" tech stack or significant seniority mismatch.

### OUTPUT RULES
- Use the 'AnalysedJobMatchList' format.
- Tone: Clinical, objective, and realistic. 
- Stop being encouraging. Be accurate. If a candidate is a bad fit, say so and provide a low score.
- Ensure the 'job_url' in your output matches the input EXACTLY."""
    if free_tier:
        writer_llm.rate_limiter = InMemoryRateLimiter(
            requests_per_second=0.09, check_every_n_seconds=0.1, max_bucket_size=1
        )

    return create_agent(
        model=writer_llm,
        system_prompt=system_prompt,
        response_format=AnalysedJobMatchList,
    )


async def writer_node(state: AgentState, agent, config: RunnableConfig):
    """Analyses jobs against profile with local caching and parallel batching."""
    log_message("Analysing jobs against your profile...")
    
    pipeline_settings = config.get("configurable", {}).get("pipeline_settings")
    api_settings = pipeline_settings.api_settings
    weights = pipeline_settings.weights 
    user_id = config.get("configurable", {}).get("user_id")
    profile_id = state.get("active_profile_id") or config.get("configurable", {}).get("profile_id")
    
    if not profile_id or not user_id:
        raise ValueError("Missing profile_id or user_id. Cannot perform analysis.")

    max_concurrency = 1 if api_settings.free_tier else 3
    semaphore = asyncio.Semaphore(max_concurrency)

    user_store = get_user_analysis_store(get_embeddings())
    research_jobs = state.get("research_data")

    final_analyses, new_jobs_to_process = check_analysis_cache(
        user_store, research_jobs, profile_id
    )

    chunks_count = 0
    if new_jobs_to_process:
        CHUNK_SIZE = 5
        chunks = [new_jobs_to_process[i:i + CHUNK_SIZE] for i in range(0, len(new_jobs_to_process), CHUNK_SIZE)]
        chunks_count = len(chunks)
        
        log_message(f"Cache Miss: Analyzing {len(new_jobs_to_process)} jobs in {chunks_count} batches...")

        tasks = [
            analyze_job_chunk(chunk, agent, state, api_settings.free_tier, semaphore, weights) 
            for chunk in chunks
        ]
        
        batch_results = await asyncio.gather(*tasks)
        llm_results = [job for sublist in batch_results for job in sublist]

        jobs_with_meta = [
            AnalysedJobMatchWithMeta(
                **job.model_dump(),
                target_role=config.get("configurable", {}).get("role"),
                target_location=config.get("configurable", {}).get("location"),
            )
            for job in llm_results
        ]

        save_job_analyses(user_store, jobs_with_meta, user_id, profile_id)
        final_analyses.extend(jobs_with_meta)
    else:
        log_message("🚀 All jobs retrieved from cache.")

    log_message("Analysis complete!")

    summary_msg = HumanMessage(content=f"Analyzed {len(new_jobs_to_process)} new jobs across {chunks_count} batches.")
    
    return {
        "messages": [summary_msg], 
        "writer_data": AnalysedJobMatchListWithMeta(jobs=final_analyses),
    }


async def analyze_job_chunk(
    chunk, 
    agent, 
    state, 
    is_free_tier: bool, 
    semaphore: asyncio.Semaphore,
    weights
):
    """Processes a single batch of jobs with priority weighting."""
    async with semaphore:
        job_list_context = "\n".join([f"JOB: {j.model_dump_json()}" for j in chunk])
        
        prompt = (
            f"AUDIT PRIORITIES:\n"
            f"- Tech Skills: {weights.key_skills}/100\n"
            f"- Experience Level: {weights.experience}/100\n"
            f"- Seniority Match: {weights.seniority_weight}/100\n\n"
            f"Analyze these {len(chunk)} jobs based on the above priorities:\n{job_list_context}"
        )
        
        msg = HumanMessage(content=prompt)
        response = await agent.ainvoke({**state, "messages": [msg]})
        
        if is_free_tier:
            await asyncio.sleep(2.0) 
            
        return response["structured_response"].jobs