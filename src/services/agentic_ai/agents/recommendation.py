from src.services.agentic_ai.config import llm
from src.services.agentic_ai.state import State


def recommendation_agent(state: State):

    if state.get("error"):
        state["recommendation"] = f"Error: {state['error']}"
        return state

    inventory = state.get("inventory", {})
    demand = state.get("demand", {})
    risk = state.get("risk", "N/A")
    policy = state.get("policy", "No policy found.")
    next_day = state.get("next_day_inventory", {})

    prompt = f"""
You are an Autonomous Inventory Replenishment AI.

Analyze the following information and generate the final inventory recommendation.

Inventory Details

Product Name:
{inventory.get("product_name")}

Current Stock:
{inventory.get("current_stock")}

Quantity Sold:
{inventory.get("quantity_sold")}

Lead Time:
{inventory.get("lead_time")}

Customer Rating:
{inventory.get("customer_rating")}


Demand Analysis

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


Risk Assessment

Risk Level:
{risk}


Retrieved Company Policy

{policy}


Next Day Inventory Prediction

{next_day}


Generate the response in the following format:

AI Inventory Recommendation

Product Name:

Decision:
(REORDER NOW / MONITOR / DO NOT REORDER)

Recommendation:

Reason:
(2-4 lines based on inventory data, demand analysis,
risk assessment and retrieved company policy.)
"""

    try:

        response = llm.invoke(prompt)

        state["recommendation"] = response.content.strip()

    except Exception as e:

        state["error"] = f"LLM Error: {e}"
        state["recommendation"] = "Failed to generate recommendation."

    return state