"""This acts as the bridge between the UI and the Graph."""

import asyncio
from langchain.messages import HumanMessage

from src.graph import create_workflow
from src.agents.cv_parser import create_cv_parser_agent
from src.agents.researcher import create_researcher_agent
from src.agents.writer import create_writer_agent
from src.utils.func import log_message


async def run_job_matcher(raw_context: str, config: dict, models: dict) -> dict:
    """
    Controller function called by streamlit_utils.process_new_cv.
    """
    storage = config["configurable"].get("storage_service")
    agents = {
        "cv_parser_agent": create_cv_parser_agent(models["reader"]),
        "researcher_agent": create_researcher_agent(models["researcher"]),
        "writer_agent": create_writer_agent(models["writer"]),
    }

    config["configurable"].update({"storage_service": storage, **agents})

    app = create_workflow()

    initial_state = {
        "messages": [HumanMessage(content=f"Analyze CV Content:\n{raw_context}")],
        "active_profile_id": config["configurable"].get("active_profile_id"),
    }

    log_message("🚀 Launching Agentic Workflow...")

    final_state = await app.ainvoke(initial_state, config=config)

    log_message("✅ Workflow execution finished.")
    return final_state


if __name__ == "__main__":
    pass
