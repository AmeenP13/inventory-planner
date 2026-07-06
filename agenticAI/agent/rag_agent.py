import os
import sys

from state import State

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
rag_path = os.path.join(project_root, "rag_policy")

for path in (project_root, rag_path):
    if path not in sys.path:
        sys.path.insert(0, path)

from rag_policy.search import search_policy


def rag_agent(state: State):
    if state.get("error"):
        return state

    product = _get_product_name(state)
    all_dates = state.get("all_dates_inventory", [])

    if all_dates:
        _annotate_history_with_policy(all_dates, product)
        _update_latest_policy_and_risk(state, all_dates)
    else:
        state["policy"] = _query_policy(product, state.get("risk", "Low"))

    return state


def _get_product_name(state: State) -> str:
    inventory = state.get("inventory", {})
    return inventory.get("product_name", "Unknown Product")


def _query_policy(product: str, risk: str) -> str:
    query = f"What is the company policy for {product} when inventory risk is {risk}?"
    return search_policy(query)


def _annotate_history_with_policy(history: list[dict], product: str) -> None:
    for record in history:
        risk = record.get("risk", "Low")
        record["policy"] = _query_policy(product, risk)


def _update_latest_policy_and_risk(state: State, history: list[dict]) -> None:
    latest_record = history[-1]
    state["policy"] = latest_record.get("policy", "N/A")
    state["risk"] = latest_record.get("risk", "Low")
