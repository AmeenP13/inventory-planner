from state import State
def risk_analysis(state: State):
    if "error" in state:
        return state
    inventory = state.get("inventory", {})
    stock = inventory.get("current_stock", 0)
    sold = inventory.get("quantity_sold", 0)
    if stock is None or sold is None:
        state["risk"] = "unknown"
        return state
    if stock <= sold:
        risk = "high"
    elif stock <= sold * 2:
        risk = "medium"
    else:
        risk = "low"
    state["risk"] = risk
    return state