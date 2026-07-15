from datetime import datetime, timedelta
import requests

from src.services.agentic_ai.config import llm

from src.services.agentic_ai.state import State

BASE_URL = "http://127.0.0.1:8000"


def generate_policy_query(inventory):


    prompt = f"""
You are an Inventory Policy Query Generator.

Generate EXACTLY ONE semantic search query to retrieve the SINGLE MOST RELEVANT
inventory policy from the company policy database.

Inventory Details

Product Name: {inventory["product_name"]}
Current Stock: {inventory["current_stock"]}
Quantity Sold: {inventory["quantity_sold"]}
Lead Time: {inventory["lead_time"]} days
Customer Rating: {inventory["customer_rating"]}
Cost Price: {inventory["cost_price"]}
Base Price: {inventory["base_price"]}
Expiry Date: {inventory["expiry_date"]}

Instructions

1. Analyze the inventory condition.
2. Select ONLY the most important inventory issue.
3. ALWAYS include the PRODUCT NAME in the query.
4. Generate ONLY ONE search query.
5. Do NOT generate explanations.
6. Do NOT generate recommendations.
7. Do NOT combine multiple policy types.

Examples

Apple has low stock:
Inventory replenishment policy for Apple

Grapes are out of stock:
Inventory stockout handling policy for Grapes

Mango has excess inventory:
Inventory overstock management policy for Mango

Milk is near expiry:
Inventory expiry management policy for Milk

Supplier delay for Rice:
Inventory supplier delay policy for Rice

Return ONLY the search query.
"""

    response = llm.invoke(prompt)
    return response.content.strip()

from src.backend.database import get_db_session
from src.backend.models import ProductORM, InventoryDailyORM, SalesORM

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
        with get_db_session() as db:
            # Query product details directly
            product_row = db.query(ProductORM).filter(
                ProductORM.product_name.like(product_name)
            ).first()
            if not product_row:
                # Try exact case-insensitive search
                product_row = db.query(ProductORM).filter(
                    ProductORM.product_name == product_name
                ).first()

            if not product_row:
                # If still not found, search in all products
                all_products = db.query(ProductORM).all()
                product_row = next(
                    (p for p in all_products if p.product_name.strip().lower() == product_name),
                    None
                )

            if not product_row:
                state["error"] = f"Product '{product_name}' not found."
                return state

            product = {
                "product_id": product_row.product_id,
                "product_name": product_row.product_name,
                "cost_price": product_row.cost_price,
                "base_price": product_row.base_price,
                "supplier_id": product_row.supplier_id,
                "avg_lead_time_day": product_row.avg_lead_time_day
            }
            product_id = product["product_id"]

            # Query inventory daily records directly
            inventory_rows = db.query(InventoryDailyORM).filter(
                InventoryDailyORM.product_id == product_id
            ).all()
            inventory = [
                {
                    "product_id": row.product_id,
                    "date": row.date,
                    "current_stock": row.current_stock,
                    "expiry_date": row.expiry_date
                }
                for row in inventory_rows
            ]

            # Query sales records directly
            sales_rows = db.query(SalesORM).filter(
                SalesORM.product_id == product_id
            ).all()
            sales = [
                {
                    "product_id": row.product_id,
                    "date": row.date,
                    "quantity_sold": row.quantity_sold,
                    "customer_rating": row.customer_rating
                }
                for row in sales_rows
            ]

    except Exception as e:
        state["error"] = f"Database Access Error: {e}"
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

    # Generate policy query using Gemini
    try:
        policy_query = generate_policy_query(latest)
        state["policy_query"] = policy_query

        print(f"[Inventory] Policy Query: {policy_query}")

    except Exception as e:
        # Fallback: dynamically generate a flexible, context-specific query
        prod_name = latest.get("product_name", "product")
        curr_stock = int(latest.get("current_stock", 0))
        reorder_pt = float(latest.get("reorder_point", 0.0))
        
        if curr_stock == 0:
            fallback_query = f"Critical stockout replenishment protocol for {prod_name}"
        elif curr_stock < reorder_pt:
            fallback_query = f"Safety stock reorder threshold policy for {prod_name}"
        elif curr_stock > reorder_pt * 2.5:
            fallback_query = f"Overstock inventory limit policy for {prod_name}"
        else:
            fallback_query = f"General safety stock buffer policy for {prod_name}"
            
        state["policy_query"] = fallback_query

        print(f"[Inventory] Gemini Query Generation Error: {e}")
        print(f"[Inventory] Using fallback query: {fallback_query}")

    # Predict next day's inventory
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