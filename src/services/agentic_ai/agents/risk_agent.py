from src.services.agentic_ai.state import State


def risk_analysis(state: State):

    if state.get("error"):
        return state

    inventory = state.get("inventory", {})
    demand = state.get("demand", {})

    current_stock = inventory.get("current_stock", 0)
    reorder_point = demand.get("reorder_point", 0)
    safety_stock = demand.get("safety_stock", 0)

    if current_stock <= safety_stock:
        risk = "High"
    elif current_stock <= reorder_point:
        risk = "Medium"
    else:
        risk = "Low"

    state["risk"] = risk
    inventory["risk"] = risk

    history = state.get("all_dates_inventory", [])
    for record in history:
        record["risk"] = risk

    next_day = state.get("next_day_inventory")
    if isinstance(next_day, dict):
        next_day["risk"] = risk

    return state