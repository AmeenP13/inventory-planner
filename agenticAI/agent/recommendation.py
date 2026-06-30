from config import llm
from state import State
def recommentated_agent(state: State):
    if state.get("error"):
        state["recommentated"] = f"Error: {state['error']}"
        return state
    inventory = state.get("inventory", {})
    next_inventory = state.get("next_day_inventory")
    all_dates = state.get("all_dates_inventory")
    demand = state.get("demand", {})
    risk = state.get("risk", "N/A")
    policy = state.get("policy", "N/A")
    if next_inventory:
        next_day_str = (
            f"Date: {next_inventory.get('date','N/A')}, "
            f"Stock: {next_inventory.get('current_stock',0)}, "
            f"Sold: {next_inventory.get('quantity_sold',0)}"
        )
    else:
        next_day_str = "N/A"
    if all_dates:
        dates_summary_list = []
        for item in all_dates:
            daily_demand = item.get("demand", {})
            dates_summary_list.append(
                f"Date: {item.get('date','N/A')} | "
                f"Stock: {item.get('current_stock',0)} | "
                f"Sold: {item.get('quantity_sold',0)} | "
                f"Risk: {item.get('risk','N/A')} | "
                f"Est Demand: {daily_demand.get('estimated_demand',0.0):.1f}"
            )
        dates_summary = "\n".join(dates_summary_list)
        date_heading = "historical data summary:"
    else:
        dates_summary = "N/A"
        date_heading = "historical data summary:"
    avg_sales = demand.get("average_daily_sales", 0.0)
    est_demand = demand.get("estimated_demand", 0.0)
    prompt = f"""
You are an Autonomous AI replenishment Agent.
Analyze the inventory and generate a recommendation report.
product name: {inventory.get('product_name','unknown')}
latest date: {inventory.get('query_date','N/A')}
current stock: {inventory.get('current_stock',0)}
quantity sold: {inventory.get('quantity_sold',0)}
{date_heading}
{dates_summary}
next day details: {next_day_str}
average daily sales: {avg_sales:.2f}
estimated demand: {est_demand:.2f}
supplier id: {inventory.get('supplier_id','N/A')}
lead time: {inventory.get('lead_time','N/A')} days
risk level: {risk}
policy: {policy}
Format strictly:
AI Inventory Recommendation
product name:
latest date:
current stock:
quantity sold:
historical data summary:
next day details:
average daily sales:
estimated demand:
suppliers:
lead days:
risk:
company policies:
Reason: 2-4 lines explanation
"""
    response = llm.invoke(prompt)
    state["recommendation"] = response.content
    return state