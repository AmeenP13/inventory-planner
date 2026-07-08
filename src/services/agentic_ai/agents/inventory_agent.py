from datetime import datetime, timedelta

import requests

from src.services.agentic_ai.state import State

BASE_URL = "http://127.0.0.1:8000/api"


def inventory_agent(state: State):
    """Fetch inventory details from FastAPI."""

    if state.get("error"):
        return state

    last_msg = state["message"][-1]

    product_name = (
        last_msg.content.strip()
        if hasattr(last_msg, "content")
        else str(last_msg).strip()
    )

    try:
        response = requests.get(
            f"{BASE_URL}/inventory",
            params={"product_name": product_name},
            timeout=10,
        )

        response.raise_for_status()

    except requests.exceptions.ConnectionError:
        state["error"] = (
            "Unable to connect to the FastAPI server.\n"
            "Start it using:\n"
            "python -m uvicorn src.backend.main:app --reload"
        )
        return state

    except requests.exceptions.RequestException as err:
        state["error"] = f"FastAPI Error: {err}"
        return state

    rows = response.json()

    if not rows:
        state["error"] = f"Product '{product_name}' not found."
        return state

    inventory_history = []

    for row in rows:
        inventory_history.append(
            {
                "date": row["date"],
                "product_name": row["product_name"],
                "current_stock": row["current_stock"],
                "quantity_sold": row["quantity_sold"],
                "supplier_id": row["supplier_id"],
                "lead_time": row["avg_lead_time_day"],
                "cost_price": row["cost_price"],
                "base_price": row["base_price"],
                "customer_rating": row["customer_rating"],
                "expiry_date": row["expiry_date"],
            }
        )

    state["all_dates_inventory"] = inventory_history

    latest = inventory_history[-1]

    state["inventory"] = latest

    latest_date = datetime.strptime(
        latest["date"],
        "%Y-%m-%d",
    )

    state["next_day_inventory"] = {
        "date": (
            latest_date + timedelta(days=1)
        ).strftime("%Y-%m-%d"),
        "current_stock": max(
            0,
            latest["current_stock"] - latest["quantity_sold"],
        ),
        "quantity_sold": latest["quantity_sold"],
    }

    return state