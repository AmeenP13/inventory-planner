from src.services.agentic_ai.config import llm
from src.services.agentic_ai.state import State


def recommendation_agent(state: State):
    """
    Generate final inventory recommendation using Gemini.
    Combines:
    - Inventory data
    - Demand analysis
    - Risk assessment
    - Retrieved company policy
    """

    if state.get("error"):
        state["recommendation"] = f"Error: {state['error']}"
        return state


    inventory = state.get("inventory", {})
    demand = state.get("demand", {})
    next_day = state.get("next_day_inventory", {})
    risk = state.get("risk", "N/A")


    # Handle RAG policy object
    policy_data = state.get("policy", {})

    if isinstance(policy_data, dict):
        policy = policy_data.get(
            "content",
            "No policy found."
        )
    else:
        policy = policy_data


    prompt = f"""
You are an Autonomous Inventory Replenishment AI.

Analyze the inventory situation and generate the final recommendation.

Inventory Information:

Product Name:
{inventory.get("product_name")}

Current Stock:
{inventory.get("current_stock")}

Quantity Sold:
{inventory.get("quantity_sold")}

Customer Rating:
{inventory.get("customer_rating")}

Supplier ID:
{inventory.get("supplier_id")}

Lead Time:
{inventory.get("lead_time")} days


Demand Analysis:

Average Daily Sales:
{demand.get("average_daily_sales")}

Reorder Point:
{demand.get("reorder_point")}

Safety Stock:
{demand.get("safety_stock")}

Days Of Stock Left:
{demand.get("days_of_stock_left")}

Demand Trend:
{demand.get("trend")}


Risk Assessment:

Risk Level:
{risk}


Next Day Inventory Forecast:

{next_day}


Company Inventory Policy:

{policy}


Generate output in this format:


AI Inventory Recommendation

Product Name:
Current Stock:
Quantity Sold:
Demand Trend:
Risk Level:

Company Policy:

Decision:
(REORDER NOW / MONITOR / DO NOT REORDER)

Recommendation:

Reason:
(Explain the decision using inventory data and company policy in 2-4 lines.)
"""


    try:

        response = llm.invoke(prompt)

        state["recommendation"] = (
            response.content.strip()
        )


    except Exception as e:

        state["error"] = (
            f"LLM Error: {e}"
        )

        state["recommendation"] = (
            "Failed to generate recommendation.\n"
            f"Error: {e}"
        )


    return state