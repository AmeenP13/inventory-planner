from src.services.agentic_ai.state import State
from langgraph.graph import StateGraph,START,END
from src.services.agentic_ai.agents.inventory_agent import inventory_agent
from src.services.agentic_ai.agents.demand_agent import demand_agent
from src.services.agentic_ai.agents.risk_agent import risk_analysis
from src.services.agentic_ai.agents.rag_agent import rag_agent
from src.services.agentic_ai.agents.recommendation import recommendation_agent


def route_after_risk(state:State):
    risk=state.get('risk','').lower()
    if risk in ['high','medium']:
        return 'rag'
    return 'recommendation'

builder=StateGraph(State)

builder.add_node('inventory',inventory_agent)
builder.add_node('demand',demand_agent)
builder.add_node('risk',risk_analysis)
builder.add_node('rag',rag_agent)
builder.add_node('recommendation',recommendation_agent)

builder.add_edge(START,'inventory')
builder.add_edge('inventory','demand')
builder.add_edge('demand','risk')
builder.add_conditional_edges (
    'risk',
    route_after_risk,
    {
        'rag':'rag',
        'recommendation':'recommendation',
    },
)

builder.add_edge('rag','recommendation')
builder.add_edge('recommendation',END)

graph=builder.compile()
