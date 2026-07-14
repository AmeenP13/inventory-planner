from src.services.agentic_ai.state import State
from src.services.rag_policy.search import search_policy


def rag_agent(state: State):

    if state.get("error"):
        return state

    inventory = state.get("inventory", {})
    product = inventory.get("product_name", "Unknown Product")

    all_dates = state.get("all_dates_inventory", [])

    # Retrieve policy for the latest record or general state
    if all_dates:
        # Retrieve policy exactly once for the latest record
        latest = all_dates[-1]
        risk = latest.get("risk", "Low")

        query = (
            f"What is the company policy for {product} "
            f"when inventory risk is {risk}?"
        )

        policy = search_policy(query)
        latest["policy"] = policy
        state["policy"] = policy
        state["risk"] = risk

    else:

        risk = state.get("risk", "Low")

        query = (
            f"What is the company policy for {product} "
            f"when inventory risk is {risk}?"
        )

        state["policy"] = search_policy(query)

    return state
