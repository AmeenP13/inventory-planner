try:
    from ..state import State
except ImportError:
    from state import State
def demand_agent(state: State):
    if state.get("all_dates_inventory"):
        total_sold = 0
        for item in state["all_dates_inventory"]:
            sold = item["quantity_sold"]
            avg_sales = sold / 30
            est_demand = sold
            item["average_daily_sales"] = round(avg_sales, 2)
            item["estimated_demand"] = est_demand
            total_sold += sold
        latest = state["all_dates_inventory"][-1]
        state["demand"] = {
            "average_daily_sales": round(total_sold / (len(state["all_dates_inventory"]) * 30), 2),
            "estimated_demand": round(total_sold / len(state["all_dates_inventory"]), 2)
        }
        latest["average_daily_sales"] = state["demand"]["average_daily_sales"]
        latest["estimated_demand"] = state["demand"]["estimated_demand"]
    return state