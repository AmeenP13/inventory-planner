from src.services.agentic_ai.config import llm
from src.services.agentic_ai.state import State


def recommendation_agent(state: State):
    if state.get("error"):
        state["recommendation"] = f"Error: {state['error']}"
        return state

    inventory = state.get("inventory", {})
    next_inventory = state.get("next_day_inventory") or {}
    all_dates = state.get("all_dates_inventory", []) or []
    demand = state.get("demand", {}) or {}
    risk = state.get("risk", "N/A")
    policy = state.get("policy", "N/A")

    avg_sales = demand.get("average_daily_sales")
    avg_sales = float(avg_sales) if avg_sales is not None else 0.0
    est_demand = demand.get("estimated_demand")
    est_demand = float(est_demand) if est_demand is not None else 0.0

    dates_summary = _format_history_summary(all_dates)
    next_day_str = _format_next_day_details(
        next_inventory, avg_sales, est_demand)

    prompt = _build_prompt(
        inventory=inventory,
        dates_summary=dates_summary,
        next_day_str=next_day_str,
        avg_sales=avg_sales,
        est_demand=est_demand,
        risk=risk,
        policy=policy,
    )

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

    return state


def _format_history_summary(history: list[dict]) -> str:
    if not history:
        return "N/A"

    lines = []
    for item in history:
        avg_daily_sales = item.get("average_daily_sales")
        avg_daily_sales = float(
            avg_daily_sales) if avg_daily_sales is not None else 0.0
        estimated_demand = item.get("estimated_demand")
        estimated_demand = float(
            estimated_demand) if estimated_demand is not None else 0.0

        lines.append(
            "Date: {date} | Stock: {current_stock} | Sold: {quantity_sold} | "
            "Avg Daily Sales: {avg_daily_sales:.2f} | Estimated Demand: {estimated_demand:.2f} | "
            "Risk: {risk}".format(
                date=item.get(
                    "date",
                    "N/A"),
                current_stock=item.get(
                    "current_stock",
                    0),
                quantity_sold=item.get(
                    "quantity_sold",
                    0),
                avg_daily_sales=avg_daily_sales,
                estimated_demand=estimated_demand,
                risk=item.get(
                    "risk",
                    "N/A"),
            ))
    return "\n".join(lines)


def _format_next_day_details(
        next_inventory: dict,
        avg_sales: float,
        est_demand: float) -> str:
    if not next_inventory:
        return "N/A"

    return (
        f"Date: {next_inventory.get('date', 'N/A')} | "
        f"Stock: {next_inventory.get('current_stock', 0)} | "
        f"Sold: {next_inventory.get('quantity_sold', 0)} | "
        f"Avg Daily Sales: {avg_sales:.2f} | "
        f"Estimated Demand: {est_demand:.2f}"
    )


def _build_prompt(
    inventory: dict,
    dates_summary: str,
    next_day_str: str,
    avg_sales: float,
    est_demand: float,
    risk: str,
    policy: str,
) -> str:
    return f"""
You are an Autonomous AI Replenishment Agent.

Analyze the following inventory information and generate a recommendation.

Product Name: {inventory.get('product_name', 'Unknown')}

Latest Date: {inventory.get('date', 'N/A')}

Current Stock: {inventory.get('current_stock', 0)}

Quantity Sold: {inventory.get('quantity_sold', 0)}

Historical Data Summary:
{dates_summary}

Next Day Details:
{next_day_str}

Average Daily Sales: {avg_sales:.2f}
Estimated Demand: {est_demand:.2f}
Supplier ID: {inventory.get('supplier_id', 'N/A')}
Lead Time: {inventory.get('lead_time', 'N/A')} days
Risk Level: {risk}
Company Policy:
{policy}

Generate the output EXACTLY in the following format:

AI Inventory Recommendation

Product Name:
Latest Date:
Current Stock:
Quantity Sold:

Historical Data Summary:

Next Day Details:

Average Daily Sales:

Estimated Demand:

Supplier ID:

Lead Time:

Risk Level:

Company Policy:

Reason:
Explain in 2-4 lines why this recommendation was made.
"""
