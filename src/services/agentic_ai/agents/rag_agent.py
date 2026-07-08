from src.services.agentic_ai.state import State
from src.services.rag_policy.search import search_policy


def rag_agent(state: State):

    if state.get("error"):
        return state

    inventory = state.get("inventory", {})
    product = inventory.get("product_name", "Unknown Product")

    risk = state.get("risk", "Low")

    query = (
        f"What is the company policy for {product} " f"when inventory risk is {risk}?"
    )

    try:
        policy = search_policy(query)

        state["policy"] = policy

        inventory["policy"] = policy

        history = state.get("all_dates_inventory", [])
        if history:
            history[-1]["policy"] = policy

        next_day = state.get("next_day_inventory")
        if isinstance(next_day, dict):
            next_day["policy"] = policy

    except Exception as e:
        state["error"] = f"RAG Error: {e}"

    return state
