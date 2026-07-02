import os
import sys

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

rag_path = os.path.join(project_root, "rag_policy")

if project_root not in sys.path:
    sys.path.insert(0, project_root)

if rag_path not in sys.path:
    sys.path.insert(0, rag_path)

from state import State
from rag_policy.search import search_policy


def rag_agent(state: State):

    if state.get("error"):
        return state

    inventory = state.get("inventory", {})
    product = inventory.get("product_name", "Unknown Product")

    all_dates = state.get("all_dates_inventory", [])

    # Retrieve policy for every historical record
    if all_dates:

        for item in all_dates:

            risk = item.get("risk", "Low")

            query = (
                f"What is the company policy for {product} "
                f"when inventory risk is {risk}?"
            )

            policy = search_policy(query)

            item["policy"] = policy

        # Store latest policy and risk
        latest = all_dates[-1]
        state["policy"] = latest.get("policy", "N/A")
        state["risk"] = latest.get("risk", "Low")

    else:

        risk = state.get("risk", "Low")

        query = (
            f"What is the company policy for {product} "
            f"when inventory risk is {risk}?"
        )

        state["policy"] = search_policy(query)

    return state