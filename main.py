from os import environ as ENV

from dotenv import load_dotenv
from langchain.messages import HumanMessage

from src.agents.cv_parser import create_cv_parser_agent
from src.agents.researcher import create_researcher_agent
from src.agents.writer import create_writer_agent
from src.graph import create_workflow
from src.utils.document_handler import ingest_input_folder, save_findings_to_docx
from src.utils.func import pretty_print_jobs_with_rich, log_message, get_llm_model


def run_job_matcher(raw_context, config: dict):
    cv_parser_agent = create_cv_parser_agent(
        get_llm_model(
            model=ENV.get("CV_PARSE_GEMINI_MODEL"),
        )
    )
    researcher_agent = create_researcher_agent(
        get_llm_model(ENV.get("SEARCH_GEMINI_MODEL"))
    )
    writer_agent = create_writer_agent(get_llm_model(ENV.get("WRITER_GEMINI_MODEL")))

    app = create_workflow(cv_parser_agent, researcher_agent, writer_agent)
    
    desired_job = config.get("configurable", {}).get("role")
    if desired_job:
        desired_job = f"focused on {desired_job}"
    desired_location = config.get("configurable", {}).get("location")
    if desired_location:
        desired_location = f"in {desired_location}"
    content = f"Parse the provided raw cv text and find the best job matches {desired_job} {desired_location}: {raw_context}"
    state = {"messages": [HumanMessage(content=content)]}

    log_message("Starting Workflow")

    state = app.invoke(input=state, config=config)

    print(save_findings_to_docx(state))
    pretty_print_jobs_with_rich(state["writer_data"].model_dump_json())
    log_message("SUCCESS: WORKFLOW COMPLETE")


if __name__ == "__main__":
    load_dotenv()
    desired_job = input("What job role are you looking for?\n").strip()
    desired_location = input("Where are you looking today?\n").strip()
    config = {"configurable": {"user_id": "Ruy001", "location": desired_location, "role": desired_job}}
    raw_context = ingest_input_folder("files/input")
    run_job_matcher(raw_context, config)
