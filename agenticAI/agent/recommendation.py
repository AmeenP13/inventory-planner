from config import llm
from state import state
def recommentated_agent(state:state):
    inventory=state['inventory']
    demand=state['demand']
    risk=state['risk']
    policy=state['policy']
    prompt=f"""
    You Are at Autonomous replenishment Inventory Agent
    product name:{inventory['product_name']}
    current stock:{inventory['current_stock']}
    quantity sold:{inventory['quantity_sold']}
    estimated demand:{demand['estimated_demand']}
    risk level:{risk}
    company policies:{policy}
    Based on the given information whether retailer will reorder the product
    mention:
    1.stock states
    2.risk level
    3.recommentated
    4.Reason
    """
    response=llm.invoke(prompt)
    state['recommentated']=response.content
    return state
