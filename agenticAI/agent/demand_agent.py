from state import state
def demand_agent(state:state):
    if 'error' in state:
        return state
    if 'all_dates_inventory' in state and state['all_dates_inventory']:
        for item in state['all_dates_inventory']:
            sold_day = item['quantity_sold']
            avg_daily = sold_day / 30
            item['demand'] = {
                'average_daily_sales': avg_daily,
                'estimated_demand': avg_daily * 30
            }
        total_sold = sum(item['quantity_sold'] for item in state['all_dates_inventory'])
        num_days = len(state['all_dates_inventory'])
        average_daily_sales = total_sold / num_days
        estimated_demand = average_daily_sales * 30
    else:
        sold=state.get('inventory', {}).get('quantity_sold', 0)
        average_daily_sales=sold/30
        estimated_demand=average_daily_sales*30
        
    state['demand']={
        'average_daily_sales':average_daily_sales,
        'estimated_demand':estimated_demand
    }
    return state
