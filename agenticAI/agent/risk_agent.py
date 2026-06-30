from state import state
def risk_analysis(state:state):
    if 'error' in state:
        return state
    if 'all_dates_inventory' in state and state['all_dates_inventory']:
        for item in state['all_dates_inventory']:
            stock_day = item['current_stock']
            sold_day = item['quantity_sold']
            if stock_day <= sold_day:
                item['risk'] = 'high'
            elif stock_day <= sold_day * 2:
                item['risk'] = 'medium'
            else:
                item['risk'] = 'low'

    stock=sold = state.get('inventory', {}).get('current_stock', 0)
    sold=sold = state.get('inventory', {}).get('quantity_sold', 0)
    if stock<=sold:
        state['risk']='high'
    elif stock<=sold*2:
        state['risk']='medium'
    else:
        state['risk']='low'
    return state