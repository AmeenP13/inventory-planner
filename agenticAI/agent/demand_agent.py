from state import State
def demand_agent(state: State):
    if state.get("all_dates_inventory"):
        total_sold = 0
        count = 0
        for item in state["all_dates_inventory"]:
            sold = item["quantity_sold"]
            average_daily_sales = sold / 30
            estimated_demand = average_daily_sales * 30
            item["average_daily_sales"] = average_daily_sales
            item["estimated_demand"] = estimated_demand
            total_sold += sold
            count += 1
        state["demand"] = {
            "average_daily_sales": total_sold / (count * 30),
            "estimated_demand": (total_sold / (count * 30)) * 30
        }
    else:
        inventory = state.get("inventory", {})
        sold = inventory.get("quantity_sold", 0)
        average_daily_sales = sold / 30
        estimated_demand = average_daily_sales * 30
        inventory["average_daily_sales"] = average_daily_sales
        inventory["estimated_demand"] = estimated_demand
        state["demand"] = {
            "average_daily_sales": average_daily_sales,
            "estimated_demand": estimated_demand
        }
    return state