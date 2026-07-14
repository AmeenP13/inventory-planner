from src.services.agentic_ai.state import State


def risk_analysis(state: State):
    if state.get("error"):
        return state

    inventory_history = state.get("all_dates_inventory")
    if inventory_history:
        _annotate_history_risk(inventory_history)
        latest_risk = inventory_history[-1].get("risk", "N/A")
        state["risk"] = latest_risk
        state.setdefault("inventory", {})["risk"] = latest_risk
        return state

    inventory = state.get("inventory", {})
    risk = _calculate_risk(
        inventory.get("current_stock", 0),
        inventory.get("quantity_sold", 0),
    )
    inventory["risk"] = risk
    state["risk"] = risk
    return state


def _annotate_history_risk(history: list[dict]) -> None:
    for record in history:
        record["risk"] = _calculate_risk(
            record.get("current_stock", 0),
            record.get("quantity_sold", 0),
        )


def _calculate_risk(stock: int, sold: int) -> str:
    if stock <= sold:
        return "High"
    if stock <= sold * 2:
        return "Medium"
    return "Low"
