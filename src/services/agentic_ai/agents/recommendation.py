from src.services.agentic_ai.config import llm
from src.services.agentic_ai.state import State


def recommendation_agent(state: State):

    if state.get("error"):
        state["recommendation"] = f"Error: {state['error']}"
        return state

    inventory = state.get("inventory", {})
    demand = state.get("demand", {})
    next_day = state.get("next_day_inventory", {})
    history = state.get("all_dates_inventory", [])
    risk = state.get("risk", "N/A")
    policy = state.get("policy", "N/A")

    prompt = f"""
You are an Autonomous Inventory Replenishment AI.

Analyze the following information and generate a recommendation.

Product Name: {inventory.get("product_name")}
Current Stock: {inventory.get("current_stock")}
Quantity Sold: {inventory.get("quantity_sold")}


Average Daily Sales: {demand.get("average_daily_sales")}
Reorder Point: {demand.get("reorder_point")}
Safety Stock: {demand.get("safety_stock")}
Days Of Stock Left: {demand.get("days_of_stock_left")}
Stock Status: {demand.get("stock_status")}
=======
    import os
    from src.services.agentic_ai.config import is_dummy_key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if is_dummy_key(api_key):
        raise ValueError("Google Gemini API Key is not configured or is a dummy key.")

    try:
        response = llm.invoke(prompt)
        recommendation = response.content.strip()
        state["recommendation"] = recommendation
    except Exception as e:
        state["error"] = f"LLM Error: {str(e)}"
        state["recommendation"] = f"Error: Failed to generate recommendation using LLM. Details: {str(e)}"
>>>>>>> 9409c6cf8deb09b427a28cd3faa8fb463fd39f18

Risk Level: {risk}

Supplier ID: {inventory.get("supplier_id")}
Lead Time: {inventory.get("lead_time")} days

Next Day Forecast:
{next_day}

Company Policy:
{policy}

Generate the output in the following format:

AI Inventory Recommendation

Product Name:
Current Stock:
Quantity Sold:
Average Daily Sales:
Reorder Point:
Safety Stock:
Days Of Stock Left:
Stock Status:
Risk Level:
Supplier ID:
Lead Time:
Company Policy:

Recommendation:
Reason:
(Explain in 2-4 lines why this recommendation was generated.)
"""

    try:
        response = llm.invoke(prompt)
        state["recommendation"] = response.content.strip()

    except Exception as e:
        state["error"] = f"LLM Error: {e}"
        state["recommendation"] = f"Failed to generate recommendation.\nError: {e}"

    return state
