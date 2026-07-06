from .state import State
from langgraph.graph import StateGraph, START, END
from .agents.inventory_agent import inventory_agent
from .agents.demand_agent import demand_agent
from .agents.risk_agent import risk_analysis
from .agents.rag_agent import rag_agent
from .agents.recommendation import recommentated_agent
builder = StateGraph(State)
builder.add_node("inventory", inventory_agent)
builder.add_node("demand", demand_agent)
builder.add_node("risk", risk_analysis)
builder.add_node("rag", rag_agent)
builder.add_node("recommendation", recommentated_agent)
builder.add_edge(START, "inventory")
builder.add_edge("inventory", "demand")
builder.add_edge("demand", "risk")
def route(state: State):
    if state.get("error"):
        return "recommendation"
    risk = state.get("risk", "Low").lower()
    if risk in ["high", "medium"]:
        return "rag"
    return "recommendation"
builder.add_conditional_edges(
    "risk",
    route,
    {
        "rag": "rag",
        "recommendation": "recommendation"
    }
)
builder.add_edge("rag", "recommendation")
builder.add_edge("recommendation", END)
graph = builder.compile()