try:
    from ..state import State
except ImportError:
    from state import State

def risk_analysis(state: State):

    if state.get("error"):
        return state

    if state.get("all_dates_inventory"):

        for item in state["all_dates_inventory"]:

            stock = item["current_stock"]
            sold = item["quantity_sold"]

            if stock <= sold:
                risk = "High"
            elif stock <= sold * 2:
                risk = "Medium"
            else:
                risk = "Low"

            item["risk"] = risk

        # Store latest risk
        state["risk"] = state["all_dates_inventory"][-1]["risk"]
        state["inventory"]["risk"] = state["risk"]

    else:

        inventory = state.get("inventory", {})

        stock = inventory.get("current_stock", 0)
        sold = inventory.get("quantity_sold", 0)

        if stock <= sold:
            risk = "High"
        elif stock <= sold * 2:
            risk = "Medium"
        else:
            risk = "Low"

        inventory["risk"] = risk
        state["risk"] = risk

    return state