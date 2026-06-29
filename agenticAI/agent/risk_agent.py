from state import state
def risk_analysis(state:state):
    stock=state['inventory']['current_stock']
    sold=state['inventory']['quantity_sold']
    if stock<=sold:
        state['risk']='high'
    elif stock<=sold*2:
        state['risk']='medium'
    else:
        state['risk']='low'
    return state