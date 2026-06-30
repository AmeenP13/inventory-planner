from state import State
def rag_agent(state: State):
    if "error" in state:
        return state
    inventory = state.get("inventory", {})
    product = inventory.get("product_name", "unknown product")
    policy_text = f"Maintain safety stock for {product} based on demand and historical sales patterns."
    if inventory:
        state["inventory"]["policy"] = policy_text
    if state.get("all_dates_inventory"):
        for item in state["all_dates_inventory"]:
            item["policy"] = policy_text
    state["policy"] = policy_text
    return state