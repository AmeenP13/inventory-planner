from datetime import datetime, timedelta
import requests

from state import State

BASE_URL = "http://127.0.0.1:8000"


def inventory_agent(state: State):

    if state.get("error"):
        return state

    last_msg = state["message"][-1]

    product_name = (
        last_msg.content.strip().lower()
        if hasattr(last_msg, "content")
        else str(last_msg).strip().lower()
    )

    try:
    
        response = requests.get(
            f"{BASE_URL}/api/products",
            timeout=10,
        )
        response.raise_for_status()
        products = response.json()

        product = next(
            (
                p for p in products
                if p["product_name"].strip().lower() == product_name
            ),
            None,
        )

        if not product:
            state["error"] = f"Product '{product_name}' not found."
            return state

        product_id = product["product_id"]

    
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            params={"product_id": product_id},
            timeout=10,
        )
        response.raise_for_status()
        inventory = response.json()


        response = requests.get(
            f"{BASE_URL}/api/sales",
            params={"product_id": product_id},
            timeout=10,
        )
        response.raise_for_status()
        sales = response.json()

    except requests.exceptions.RequestException as e:
        state["error"] = f"Backend API Error: {e}"
        return state

    if not inventory:
        state["error"] = "No inventory history found."
        return state

    sales_lookup = {
        row["date"]: row
        for row in sales
    }

    inventory_history = []

    for row in inventory:

        sale = sales_lookup.get(row["date"], {})

        inventory_history.append(
            {
                "product_id": product_id,
                "product_name": product["product_name"],
                "date": row["date"],
                "current_stock": row["current_stock"],
                "quantity_sold": sale.get("quantity_sold", 0),
                "customer_rating": sale.get("customer_rating", 0.0),
                "supplier_id": product["supplier_id"],
                "avg_lead_time_day": product["avg_lead_time_day"],
                "lead_time": product["avg_lead_time_day"],
                "cost_price": product["cost_price"],
                "base_price": product["base_price"],
                "expiry_date": row.get("expiry_date"),
            }
        )

    state["all_dates_inventory"] = inventory_history

    latest = inventory_history[-1]

    state["inventory"] = latest

    latest_date = datetime.strptime(
        latest["date"],
        "%Y-%m-%d",
    )

    predicted_stock = max(
        0,
        latest["current_stock"] - latest["quantity_sold"],
    )

    state["next_day_inventory"] = {
        "date": (
            latest_date + timedelta(days=1)
        ).strftime("%Y-%m-%d"),
        "current_stock": predicted_stock,
        "quantity_sold": latest["quantity_sold"],
    }

    return state