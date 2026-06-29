from state import state
def demand_agent(state:state):
    sold=state['inventory']['quantity_sold']
    average_daily_sales=sold/30
    estimated_demand=average_daily_sales*30
    state['demand']={
        'average_daily_sales':average_daily_sales,
        'estimated_demand':estimated_demand
    }
    return state
