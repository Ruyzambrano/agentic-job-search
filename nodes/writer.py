from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.rate_limiters import InMemoryRateLimiter

from schema import AnalysedJobMatchList
from state import AgentState


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


def writer_node(state: AgentState, agent):
    """For setting up the nodes"""
    print("Analysing jobs against your profile...")
    job_list_context = ""
    for i, job in enumerate(state["research_data"].jobs):
        job_list_context += f"\nJOB #{i+1}:\n"
        job_list_context += f"Title: {job.title}\n"
        job_list_context += f"URL: {job.job_url}\n"
        job_list_context += f"Description: {job.description}\n"
        job_list_context += f"Attributes{job.attributes.model_dump_json()}"

    new_message = [HumanMessage(
        content=f"Here is the research data:\n{job_list_context}\n\n"
                f"Analyse these against my profile and return the structured list. "
                f"CRITICAL: Use the EXACT 'URL' provided for each job. Do not invent links."
    )]
    
    response = agent.invoke({**state, "messages": state["messages"] + new_message})
    print("Analysis complete!")
    return {"message": new_message,
            "writer_data": response["structured_response"]}
