from config import llm
from state import state
def recommentated(state:state):
    inventory=state['demand']
    demand=state['demand']
    risk=state['risk']
    policy=state['policy']
    prompt=f"""
    You are Inventory Replenishment AI
    Product Name:{inventory['product_name']}
    Current Stock:{inventory['current_stock']}
    estimated sold:{inventory['estimated_sold']}
    estimated demand:{demand['estimated_demand']}
    Risk Level:{risk}
    Company policies:{policy}
    Based on the Above information,recommentated whether retailer should reorder the product.
    Mention:
    1.stock status
    2.Risk level
    3.Recommendation
    4.Reason
    """
    response=llm.invoke(prompt)
    state['recommented']=response.content
    return state
