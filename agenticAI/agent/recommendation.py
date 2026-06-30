from config import llm
from state import state
def recommentated_agent(state:state):
    if 'error' in state:
        state['recommentated'] = f"Error: {state['error']}"
        return state
    inventory=state['inventory']
    next_inventory=state.get('next_day_inventory')
    all_dates=state.get('all_dates_inventory')
    demand=state['demand']
    risk=state['risk']
    policy=state['policy']
    
    if next_inventory:
        next_day_str = f"Date: {next_inventory['date']}, Stock: {next_inventory['current_stock']}, Sold: {next_inventory['quantity_sold']}"
    else:
        next_day_str = "N/A"

    if all_dates:
        dates_summary_list = []
        for item in all_dates:
            daily_demand = item.get('demand', {})
            dates_summary_list.append(
                f"Date: {item['date']} | Stock: {item['current_stock']} | Sold: {item['quantity_sold']} | "
                f"Risk: {item.get('risk', 'N/A')} | Est Demand: {daily_demand.get('estimated_demand', 0.0):.1f}"
            )
        dates_summary = "\n    ".join(dates_summary_list)
        date_heading = "historical data summary:"
    else:
        dates_summary = "N/A"
        date_heading = "historical data summary:"

    prompt=f""""
  You Are An Autonomuos AI replenishment Agent.
  Analyze the following inventory details and generate a recommendation report.
  mention:
    product name: {inventory.get('product_name', 'unknown product')}
    latest date:{inventory.get('query_date', 'N/A')}
    current stock:{inventory.get('current_stock', 0)}
    quantity sold:{inventory.get('quantity_sold', 0)}
    {date_heading}
    {dates_summary}
    next day details:{next_day_str}
    average daily sales:{demand['average_daily_sales']:.2f}
    estimated demand:{demand['estimated_demand']:.2f}
    supplier id:{inventory.get('supplier_id','not applicable')}
    lead day:{inventory.get('lead_time','not applicable')}days
    risk level:{risk}
    policy:{policy}
    
    Generate the output exactly these format:
    AI Inventory Recommendation
    product name:
    latest date:
    current stock:
    quantity sold:
    historical data summary: (List all dates with their stock/sold details if requested, otherwise print N/A)
    next day details:
    average daily sales:
    estimated demand:
    suppliers:
    lead days:
    risk:
    company policies:
    Reason:Explain 2-4 lines why these recommendation was made (discuss the historical trends across all dates if requested)
    """
    reason=llm.invoke(prompt)
    state['recommentated']=reason.content
    return state
