from .state import State
from langgraph.graph import StateGraph, START, END

from .agents.demand_agent import demand_agent
from .agents.inventory_agent import inventory_agent
from .agents.rag_agent import rag_agent
from .agents.recommendation import recommendation_agent
from .agents.risk_agent import risk_analysis

NODE_INVENTORY = "inventory"
NODE_DEMAND = "demand"
NODE_RISK = "risk"
NODE_RAG = "rag"
NODE_RECOMMENDATION = "recommendation"


def _route_after_risk(state: State) -> str:
    if state.get("error"):
        return NODE_RECOMMENDATION

    risk_level = state.get("risk", "Low").lower()
    if risk_level in {"high", "medium"}:
        return NODE_RAG
    return NODE_RECOMMENDATION


def _build_graph() -> StateGraph:
    builder = StateGraph(State)

    builder.add_node(NODE_INVENTORY, inventory_agent)
    builder.add_node(NODE_DEMAND, demand_agent)
    builder.add_node(NODE_RISK, risk_analysis)
    builder.add_node(NODE_RAG, rag_agent)
    builder.add_node(NODE_RECOMMENDATION, recommendation_agent)

    builder.add_edge(START, NODE_INVENTORY)
    builder.add_edge(NODE_INVENTORY, NODE_DEMAND)
    builder.add_edge(NODE_DEMAND, NODE_RISK)

    builder.add_conditional_edges(
        NODE_RISK,
        _route_after_risk,
        {
            NODE_RAG: NODE_RAG,
            NODE_RECOMMENDATION: NODE_RECOMMENDATION,
        },
    )

    builder.add_edge(NODE_RAG, NODE_RECOMMENDATION)
    builder.add_edge(NODE_RECOMMENDATION, END)

    return builder.compile()


graph = _build_graph()