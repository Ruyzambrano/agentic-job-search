"""Analyses the returned jobs based on the candidate profile"""

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


def create_writer_agent(writer_llm):
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
    log_message("Analysing jobs against your profile...")
    pipeline_settings = config.get("configurable", {}).get("pipeline_settings")

    embeddings = get_embeddings()
    user_store = get_user_analysis_store(embeddings)

    user_id = config.get("configurable", {}).get("user_id")
    profile_id = state.get("active_profile_id") or config.get("configurable", {}).get(
        "profile_id"
    )

    if not profile_id or not user_id:
        raise ValueError("Missing profile_id or user_id. Cannot perform analysis.")

    research_jobs = state.get("research_data")

    new_message_obj = None

    final_analyses, new_jobs_to_process = check_analysis_cache(
        user_store, research_jobs, profile_id
    )

    if new_jobs_to_process:
        log_message(f"Cache Miss: Analyzing {len(new_jobs_to_process)} new jobs...")
        job_list_context = ""

        for i, job in enumerate(new_jobs_to_process):
            job_list_context += f"\nNEW JOB #{i+1}:\n{job.model_dump_json()}"

        expected_count = len(new_jobs_to_process)
        new_message_obj = HumanMessage(
            content=(
                f"There are {expected_count} NEW jobs to analyse. "
                f"You MUST return an analysis for EVERY SINGLE ONE ({expected_count} total). "
                f"Data: {job_list_context}"
            )
        )

        response = agent.invoke(
            {**state, "messages": state["messages"] + [new_message_obj]}
        )
        llm_results = response["structured_response"].jobs

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
        log_message("🚀 All jobs retrieved from cache. Zero tokens consumed.")

    log_message("Analysis complete!")

    return {
        "messages": [new_message_obj] if new_message_obj else [],
        "writer_data": AnalysedJobMatchListWithMeta(jobs=final_analyses),
    }
