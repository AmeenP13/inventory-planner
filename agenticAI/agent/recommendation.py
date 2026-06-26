from state import State
from config import llm
def recommentaion_agent(state:State):
    inventory=state['inventory']
    demand=state['demand']
    risk=state['risk']
    policy=state['policy']
    prompt=f"""
    You Are In Replenishment AI Trigger
    product name:{inventory['product_name']}
    current stock:{inventory['current_stock']}
    estimated sold:{demand['estimated_sold']}
    estimated demand:{demand['estimated_demand']}
    risk level:{risk}
    company policies:{policy}
    Based on above information,recommented whether retail will reorder the product
    """
    response=llm.invoke(prompt)
    state['recommentaion']=response.content
    return state