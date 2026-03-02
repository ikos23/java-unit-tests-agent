"""
LangGraph workflow definition.
Wires the three agents together with a conditional retry loop.

Graph topology:
    START --> analyzer --> generator --> validator --[pass]--> END
                               ^                  |
                               |----[fail,retry]--|
                               (max 3 retries, then END regardless)
"""
from langgraph.graph import StateGraph, START, END

from graph.state import AgentState
from agents.analyzer import run_analyzer
from agents.generator import run_generator
from agents.validator import run_validator, route_after_validation


def build_graph():
    """
    Build and compile the multi-agent StateGraph.
    Returns a compiled LangGraph application ready to invoke.
    """
    builder = StateGraph(AgentState)

    # Register the three agent nodes
    builder.add_node("analyzer", run_analyzer)
    builder.add_node("generator", run_generator)
    builder.add_node("validator", run_validator)

    # Linear entry: START -> analyzer -> generator -> validator
    builder.add_edge(START, "analyzer")
    builder.add_edge("analyzer", "generator")
    builder.add_edge("generator", "validator")

    # Conditional retry edge from validator:
    #   "end"       -> END          (tests passed, or max retries hit)
    #   "generator" -> generator    (tests failed, retry with error context)
    builder.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "end": END,
            "generator": "generator",
        },
    )

    return builder.compile()


# Module-level compiled graph — import this in main.py
graph = build_graph()
