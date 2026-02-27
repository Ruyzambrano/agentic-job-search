"""Parses a CV and returns a CandidateProfile while also writing the profile to a DB"""
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

from src.state import AgentState
from src.schema import CandidateProfile
from src.utils.vector_handler import save_candidate_profile, get_user_analysis_store


def create_cv_parser_agent(cv_parser_llm):
    """Creates a research agent that can read a cv and get relevant jobs"""
    system_prompt = """### ROLE
You are a precise HR Data Extraction Engine. Your sole purpose is to transform raw text into a structured JSON schema. You operate with 100% fidelity to the source text.

### OPERATIONAL CONSTRAINTS
- NO PLACEHOLDERS: Never use names like "John Doe", "Jane Smith", or "N/A" unless they are explicitly written in the CV.
- ESCAPE HATCH: If a specific data point (like 'full_name' or 'current_location') is absolutely missing from the provided text, return an empty string (""). 
- NO CREATIVITY: Do not infer skills. If the candidate says "Built apps with Python," do not add "Django" or "Flask" unless they are mentioned.
- SOURCE ONLY: Your knowledge base for this task is ONLY the text provided in the user message. Ignore your internal training data about generic CVs.

### EXTRACTION GUIDELINES
1. **Name Extraction**: The name is usually at the very top. If multiple names appear (e.g., references), identify the candidate by looking for the one associated with contact info.
2. **Title Normalization**: Map messy titles to standard industry terms (e.g., "Full Stack Wizard" -> "Full Stack Developer").
3. **Skill Prioritization**: Focus on technical "Hard Skills" (Python, AWS, SQL) over "Soft Skills" (Teamwork, Leadership).
4. **Seniority Logic**: 
   - 0-2 years: Junior
   - 3-5 years: Mid
   - 6+ years: Senior
   - Management: Lead/Executive

### FORMATTING
Return ONLY the JSON object. Do not provide an intro, outro, or explanations."""
    return create_agent(
        model=cv_parser_llm,
        system_prompt=system_prompt,
        response_format=CandidateProfile,
    )


def cv_parser_node(state: AgentState, agent, config: RunnableConfig):
    """Creates the node of the agent for workflows"""

    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        raise ValueError("user_id is missing from the configuration. Cannot save profile.")
    
    user_store = get_user_analysis_store()

    print("Parsing cv...")
    result = agent.invoke(state)
    cv_data = result["structured_response"]

    print("Parsing complete!")
    print("\nCandidate info:")
    print(f"Name: {cv_data.full_name}")
    print(f"Key Skills: {cv_data.key_skills}\n")
    print(cv_data.summary, end="\n\n")
    
    profile_id = save_candidate_profile(user_store, user_id, cv_data)
    return {
            "cv_data": cv_data, 
            "active_profile_id": profile_id
        }
