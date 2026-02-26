from langgraph.graph import StateGraph, START, END
from functools import partial

from state import AgentState
from nodes.cv_parser import cv_parser_node
from nodes.researcher import researcher_node
from nodes.writer import writer_node


def create_workflow(cv_parser_agent, researcher_agent, writer_agent):
    workflow = StateGraph(AgentState)
    workflow.add_node("cv_parser_node", partial(cv_parser_node, agent=cv_parser_agent))
    workflow.add_node(
        "researcher_node", partial(researcher_node, agent=researcher_agent)
    )
    workflow.add_node("writer_node", partial(writer_node, agent=writer_agent))

    workflow.add_edge(START, "cv_parser_node")
    workflow.add_edge("cv_parser_node", "researcher_node")
    workflow.add_edge("researcher_node", "writer_node")
    workflow.add_edge("writer_node", END)

    return workflow.compile()
