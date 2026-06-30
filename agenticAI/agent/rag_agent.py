from state import state
def rag_agent(state:state):
    if 'error' in state:
        return state
    product = state.get('inventory', {}).get('product_name', 'unknown product')
    if 'all_dates_inventory' in state and state['all_dates_inventory']:
        for item in state['all_dates_inventory']:
            item['policy'] = f"maintain safety stock for {product}"
            
    policy=f"maintain safety stock for {product}"
    state['policy']=policy
    return state
