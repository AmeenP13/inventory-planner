from state import state
def rag_agent(state:state):
    product=state['inventory']['product_name']
    policy=f"maintain safety stock for {product}"
    state['policy']=policy
    return state
