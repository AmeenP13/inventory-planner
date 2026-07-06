try:
    from ..state import State
    from ...rag_policy.search import search_policy
except (ImportError, ValueError):
    from state import State
    try:
        from rag_policy.search import search_policy
    except ImportError:
        import os
        import sys
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        sys.path.insert(0, project_root)
        from rag_policy.search import search_policy


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