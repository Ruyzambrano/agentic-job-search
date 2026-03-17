from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.agents.cv_parser import cv_parser_node
from src.agents.researcher import researcher_node
from src.agents.writer import writer_node


def create_workflow():
    """
    Creates a clean workflow.
    Nodes now pull their agents from the 'config' parameter
    rather than having them hard-coded via partial.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("cv_parser", cv_parser_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)

    workflow.add_edge(START, "cv_parser")
    workflow.add_edge("cv_parser", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)

    return workflow.compile()
