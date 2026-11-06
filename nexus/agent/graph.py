from langgraph.graph import END, START, StateGraph

from nexus.agent.nodes import (
    expand_links_node,
    generate_node,
    grade_node,
    retrieve_node,
    rewrite_node,
    verify_node,
)
from nexus.agent.state import AgentState

# One first search plus at most two more
MAX_SEARCHES = 3


def route_after_grade(state):
    if state["verdict"] == "enough":
        return "generate"
    if state["attempt"] >= MAX_SEARCHES:
        return "generate"
    if not state["better_query"] or state["better_query"] == state["query"]:
        return "generate"
    return "rewrite"


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("expand_links", expand_links_node)
    graph.add_node("grade", grade_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)
    graph.add_node("verify", verify_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "expand_links")
    graph.add_edge("expand_links", "grade")
    graph.add_conditional_edges("grade", route_after_grade, ["generate", "rewrite"])
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", "verify")
    graph.add_edge("verify", END)

    return graph.compile()
