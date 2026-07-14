from pathlib import Path
from src.services.agentic_ai.state import State
from datetime import datetime, timedelta
from src.backend.database import get_db_session
from src.backend.models import ProductORM, InventoryDailyORM, SalesORM
from sqlalchemy import func


def inventory_agent(state: State):
    last_msg = state["message"][-1]
    if hasattr(last_msg, "content"):
        product_name = last_msg.content.lower().strip()
    else:
        product_name = str(last_msg).lower().strip()

    # Query inventory daily combined with product details and sales metrics via ORM
    with get_db_session() as db:
        rows = db.query(
            InventoryDailyORM.date,
            ProductORM.product_name,
            InventoryDailyORM.current_stock,
            func.coalesce(SalesORM.quantity_sold, 0).label("quantity_sold"),
            ProductORM.supplier_id,
            ProductORM.avg_lead_time_day,
            ProductORM.cost_price,
            ProductORM.base_price,
            func.coalesce(SalesORM.customer_rating, 0.0).label("customer_rating"),
            InventoryDailyORM.expiry_date
        ).join(
            ProductORM, InventoryDailyORM.product_id == ProductORM.product_id
        ).outerjoin(
            SalesORM, (InventoryDailyORM.product_id == SalesORM.product_id) & (InventoryDailyORM.date == SalesORM.date)
        ).filter(
            func.lower(func.trim(ProductORM.product_name)) == product_name
        ).order_by(
            InventoryDailyORM.date
        ).all()

    if not rows:
        state["error"] = f"Product '{product_name}' not found."
        return state

    inventory_history = []
    for row in rows:
        inventory_history.append({
            "date": row.date,
            "product_name": row.product_name,
            "current_stock": int(row.current_stock),
            "quantity_sold": int(row.quantity_sold),
            "supplier_id": row.supplier_id,
            "lead_time": int(row.avg_lead_time_day),
            "cost_price": float(row.cost_price),
            "base_price": float(row.base_price),
            "customer_rating": float(row.customer_rating),
            "expiry_date": row.expiry_date
        })

    state["all_dates_inventory"] = inventory_history
    latest = inventory_history[-1]
    state["inventory"] = latest
    latest_date = datetime.strptime(latest["date"], "%Y-%m-%d")
    predicted_stock = max(0, latest["current_stock"] - latest["quantity_sold"])
    state["next_day_inventory"] = {
        "date": (latest_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "current_stock": predicted_stock,
        "quantity_sold": latest["quantity_sold"]
    }
    return state
