from state import state
from langgraph.graph import StateGraph,START,END
from agent.demand_agent import demand_agent
from agent.inventory_agent import inventory_agent
from agent.rag_agent import rag_agent
from agent.recommendation import recommentated_agent
from agent.risk_agent import risk_analysis
builder=StateGraph(state)
builder.add_node('inventory',inventory_agent)
builder.add_node('demand',demand_agent)
builder.add_node('risk',risk_analysis)
builder.add_node('rag',rag_agent)
builder.add_node('recommendation',recommentated_agent)
builder.add_edge(START,'inventory')
builder.add_edge('inventory','demand')
builder.add_edge('demand','risk')
def route(state:state):
    if state['risk']=='high':
        return 'rag'
    elif state['risk']=='medium':
        return 'rag'
    else:
        return 'recommendation'
builder.add_conditional_edges(
    'risk',
    route,
    {
        'rag':'rag',
        'recommendation':'recommendation'
    }
)
builder.add_edge('rag','recommendation')
builder.add_edge('recommendation',END)
graph=builder.compile()
