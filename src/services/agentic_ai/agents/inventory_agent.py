from datetime import datetime, timedelta

from src.backend.database import get_connection
from src.services.agentic_ai.state import State


def inventory_agent(state: State):

    if state.get("error"):
        return state

    last_msg = state["message"][-1]

    product_name = (
        last_msg.content.strip().lower()
        if hasattr(last_msg, "content")
        else str(last_msg).strip().lower()
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            i.date,
            p.product_name,
            i.current_stock,
            COALESCE(s.quantity_sold,0) AS quantity_sold,
            p.supplier_id,
            p.avg_lead_time_day,
            p.cost_price,
            p.base_price,
            COALESCE(s.customer_rating,0) AS customer_rating,
            i.expiry_date
        FROM inventory_daily i
        INNER JOIN products p
            ON i.product_id = p.product_id
        LEFT JOIN sales s
            ON i.product_id = s.product_id
            AND i.date = s.date
        WHERE LOWER(TRIM(p.product_name)) = ?
        ORDER BY i.date
        """,
        (product_name,),
    )

    rows = cursor.fetchall()
    conn.close()

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

    latest_date = datetime.strptime(latest["date"], "%Y-%m-%d")

    state["next_day_inventory"] = {
        "date": (latest_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "current_stock": max(
            0,
            latest["current_stock"] - latest["quantity_sold"],
        ),
        "quantity_sold": latest["quantity_sold"],
    }

    return state
