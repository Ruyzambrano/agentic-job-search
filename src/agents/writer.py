"""Analyses the returned jobs based on the candidate profile"""

import asyncio
from typing import Dict, Any, List

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig
from html2text import html2text

from src.schema import (
    AnalysedJobMatchListWithMeta,
    AnalysedJobMatchList,
    RawJobMatchList,
    AnalysedJobMatchWithMeta,
)
from src.state import AgentState
from src.services.storage_service import StorageService
from src.utils.func import log_message


def create_writer_agent(writer_llm, free_tier: bool = False):
    """Creates a writer agent"""

    system_prompt = """You are a Critical Recruitment Auditor. Your task is to perform a high-fidelity "Gap Analysis" between a Candidate Profile and a list of job openings.

### YOUR MANDATE
1. ANALYZE EVERY JOB: You must return an analysis for EVERY job provided in the input list. Do not truncate the list. Do not focus only on the "best" ones.
2. BE HYPER-CRITICAL: Your Match Score must be conservative. A 95%+ score should be reserved for candidates who meet 100% of the tech stack AND seniority requirements. 
3. DETECT OVER-QUALIFICATION/UNDER-QUALIFICATION: If a candidate has 10 years of experience and the job is "Junior," the score should be LOW due to "Retention Risk."

### ANALYSIS CRITERIA
For every job, provide:
- job_summary: A 2-3 sentence value proposition of the role.
- attributes: List of key traits (e.g., 'Remote', 'Senior', 'Permanent').
- top_applicant_score: A conservative 0-100 score.
- top_applicant_reasoning: A high-fidelity "Gap Analysis". List specific evidence of matches AND explicitly list missing technologies or seniority mismatches (The "Gap").

### OUTPUT RULES
- Use the 'AnalysedJobMatchList' format.
- Tone: Clinical, objective, and realistic. 
- Stop being encouraging. Be accurate. If a candidate is a bad fit, say so and provide a low score.
- Ensure the 'job_url' in your output matches the input EXACTLY.

### FINAL JSON SAFETY CHECK
- You are producing NATIVE JSON. 
- If a job description contains double quotes, you MUST use single quotes in your 'Why' and 'Gap' fields.
- Example: Instead of "He said "Hello"", use "He said 'Hello'"."""
    if free_tier:
        writer_llm.rate_limiter = InMemoryRateLimiter(
            requests_per_second=0.09, check_every_n_seconds=0.1, max_bucket_size=1
        )

    return create_agent(
        model=writer_llm,
        system_prompt=system_prompt,
        response_format=AnalysedJobMatchList,
    )


async def writer_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Orchestrates the analysis phase:
    1. Checks StorageService for cached analyses.
    2. Chunks remaining jobs for LLM processing.
    3. Executes parallel analysis with concurrency control.
    4. Persists new analyses.
    """
    cfg = config.get("configurable", {})
    settings = cfg.get("pipeline_settings")
    storage: StorageService = cfg.get("storage_service")
    agent = cfg.get("writer_agent")

    profile_id = state.get("active_profile_id") or cfg.get("active_profile_id")
    research_data = state.get("research_data", [])

    if isinstance(research_data, list):
        research_jobs = RawJobMatchList(jobs=research_data)
    else:
        research_jobs = research_data

    log_message(f"Auditing {len(research_jobs.jobs)} jobs against profile...")

    final_analyses, jobs_to_process = storage.check_analysis_cache(
        research_jobs, profile_id
    )

    if not jobs_to_process:
        log_message("🚀 All jobs retrieved from cache.")
        final_analyses_meta = [AnalysedJobMatchWithMeta(**j.model_dump()) for j in final_analyses]
        return {"writer_data": AnalysedJobMatchListWithMeta(jobs=final_analyses_meta)}

    max_concurrency = 1 if settings.api_settings.free_tier else 3
    semaphore = asyncio.Semaphore(max_concurrency)
    chunk_size = 5
    chunks = [
        jobs_to_process[i : i + chunk_size]
        for i in range(0, len(jobs_to_process), chunk_size)
    ]

    log_message(
        f"Cache Miss: Analyzing {len(jobs_to_process)} jobs in {len(chunks)} batches..."
    )

    tasks = [
        _analyze_chunk(chunk, agent, state, semaphore, settings) for chunk in chunks
    ]
    batch_results = await asyncio.gather(*tasks)

    new_llm_results = [job for sublist in batch_results for job in sublist]
    
    loc_obj = cfg.get("location")
    target_loc_str = loc_obj.city if hasattr(loc_obj, "city") else str(loc_obj or "")

    enriched_results = [
        job.model_copy(update={
            "target_role": cfg.get("role"),
            "target_location": target_loc_str,
        })
        for job in new_llm_results
    ]

    storage.save_job_analyses(enriched_results, cfg.get("user_id"), profile_id)
    final_analyses.extend(enriched_results)

    final_analyses_meta = [
        AnalysedJobMatchWithMeta(**job.model_dump()) 
        if not isinstance(job, AnalysedJobMatchWithMeta) else job
        for job in final_analyses
    ]

    return {
    "writer_data": AnalysedJobMatchListWithMeta(
        jobs=[j.model_dump() if hasattr(j, "model_dump") else j for j in final_analyses_meta]
    ).model_dump(),
    "messages": [HumanMessage(content=f"Audited {len(final_analyses_meta)} roles.")],
}

async def _analyze_chunk(chunk, agent, state, semaphore, settings) -> List[Any]:
    """Handles LLM call with industry-agnostic seniority guardrails."""
    w = settings.weights
    profile = state['cv_data']
    
    async with semaphore:
        profile_summary = (
            f"--- CANDIDATE DOSSIER ---\n"
            f"NAME: {profile.full_name}\n"
            f"CURRENT TRACK EXPERIENCE: {profile.years_of_experience} years\n"
            f"PREVIOUS ROLES: {profile.job_titles}"
            f"CORE SKILLS: {', '.join(profile.key_skills)}\n"
            f"--------------------------\n"
        )

        context_parts = []
        for j in chunk:
            clean_desc = html2text(j.description)
            safe_desc = clean_desc[:2000]
            
            job_block = (
                f"--- JOB START ---\n"
                f"URL: {j.job_url}\n"
                f"TITLE: {j.title}\n"
                f"COMPANY: {j.company}\n"
                f"LOCATION: {j.location}\n"
                f"DESCRIPTION: {safe_desc}\n"
                f"--- JOB END ---"
            )
            context_parts.append(job_block)
        
        context = "\n".join(context_parts)
                    
        prompt = (
            f"--- AUDIT WEIGHTS ---\n"
            f"{w.model_dump_json(indent=2)}\n"
            f"----------------------\n"
            f"{profile_summary}\n"
            f"TASK: Analyze the following {len(chunk)} jobs against the candidate profile.\n"
            f"\n--- SCORING DIRECTIVES ---\n"
            f"1. SENIORITY RULE: Use ONLY 'CURRENT TRACK EXPERIENCE' ({profile.years_of_experience} yrs) "
            f"to match against the job's seniority requirements (e.g., Senior/Lead). "
            f"Do NOT use 'TOTAL CAREER TENURE' to satisfy industry-specific experience gaps.\n"
            f"2. INDUSTRY MATCH: If the job is in one of the candidate's target industries "
            f"({', '.join(profile.industries)}), apply a +10 point relevance bonus.\n"
            f"3. SKILL SYNERGY: Apply a point bonus if niche skills are required.\n"
            f"4. MAPPING: job_url, company, and location MUST match the input exactly.\n"
            f"5. REASONING: Start reasoning with: 'Candidate has {profile.years_of_experience} years in this track vs [X] years required by the role.'\n"
            f"\nJOBS TO ANALYZE:\n{context}"
        )

        try:
            response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
            structured_data = response.get("structured_response") or response
            return structured_data.jobs if hasattr(structured_data, 'jobs') else []
        except Exception as e:
            log_message(f"⚠️ Analysis Error: {str(e)[:100]}")
            return []