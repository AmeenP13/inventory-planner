try:
    from ..config import llm
    from ..state import State
except ImportError:
    from config import llm
    from state import State
def recommentated_agent(state: State):
    if state.get("error"):
        state["recommendation"] = f"Error: {state['error']}"
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
            avg_val = item.get("average_daily_sales")
            avg_val = float(avg_val) if avg_val is not None else 0.0
            est_val = item.get("estimated_demand")
            est_val = float(est_val) if est_val is not None else 0.0
            dates_summary_list.append(
                f"Date: {item.get('date','N/A')} | "
                f"Stock: {item.get('current_stock',0)} | "
                f"Sold: {item.get('quantity_sold',0)} | "
                f"Avg Daily Sales: {avg_val:.2f} | "
                f"Estimated Demand: {est_val:.2f} | "
                f"Risk: {item.get('risk','N/A')}"
            )
        dates_summary = "\n".join(dates_summary_list)
    else:
        dates_summary = "N/A"
    avg_sales = demand.get("average_daily_sales")
    avg_sales = float(avg_sales) if avg_sales is not None else 0.0
    est_demand = demand.get("estimated_demand")
    est_demand = float(est_demand) if est_demand is not None else 0.0

    prompt = f"""
You are an Autonomous AI Replenishment Agent.

Analyze the following inventory information and generate a recommendation.

Product Name: {inventory.get('product_name','Unknown')}
Latest Date: {inventory.get('date','N/A')}
Current Stock: {inventory.get('current_stock',0)}
Quantity Sold: {inventory.get('quantity_sold',0)}
Historical Data Summary:
{dates_summary}
Next Day Details:
{next_day_str}
Average Daily Sales: {avg_sales:.2f}
Estimated Demand: {est_demand:.2f}
Supplier ID: {inventory.get('supplier_id','N/A')}
Lead Time: {inventory.get('lead_time','N/A')} days
Risk Level: {risk}
Company Policy:
{policy}

Generate the output EXACTLY in the following format:

AI Inventory Recommendation

Product Name:
Latest Date:
Current Stock:
Quantity Sold:

Historical Data Summary:

Next Day Details:

Average Daily Sales:

Estimated Demand:

Supplier ID:

Lead Time:

Risk Level:

Company Policy:

Reason:
Explain in 2-4 lines why this recommendation was made.
"""
    try:
        response = llm.invoke(prompt)
        state["recommendation"] = response.content
    except Exception as e:
        state["error"] = f"LLM Error: {str(e)}"
        state["recommendation"] = f"Error: Failed to generate recommendation using LLM. Details: {str(e)}"
    return state