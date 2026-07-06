from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from state import State

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "final_inventory_dataset_real_products.csv"
DATE_FORMAT = "%Y-%m-%d"


def inventory_agent(state: State):
    product_name = _extract_product_name(state)
    if not product_name:
        state["error"] = "Product name is missing from the incoming message."
        return state

    df = pd.read_csv(DATA_FILE)
    product_rows = _find_product_rows(df, product_name)

    if product_rows.empty:
        state["error"] = f"Product '{product_name}' not found."
        return state

    inventory_history = _build_inventory_history(product_rows)
    latest_record = inventory_history[-1]

    state["all_dates_inventory"] = inventory_history
    state["inventory"] = latest_record
    state["next_day_inventory"] = _build_next_day_inventory(latest_record)

    return state


def _extract_product_name(state: State) -> str:
    messages = state.get("message", [])
    if not messages:
        return ""

    last_message = messages[-1]
    if isinstance(last_message, str):
        product_name = last_message.strip()
    else:
        product_name = getattr(last_message, "content", "").strip()

    return product_name.lower()


def _find_product_rows(df: pd.DataFrame, product_name: str) -> pd.DataFrame:
    normalized_name = df["product_name"].astype(str).str.lower().str.strip()
    return df[normalized_name == product_name].sort_values("date")


def _build_inventory_history(product_rows: pd.DataFrame) -> list[dict]:
    history = []
    for _, row in product_rows.iterrows():
        history.append({
            "date": str(row["date"]),
            "product_name": str(row["product_name"]),
            "current_stock": int(row["current_stock"]),
            "quantity_sold": int(row["quantity_sold"]),
            "supplier_id": str(row.get("supplier_id", "")),
            "lead_time": int(row.get("avg_lead_time_day", 0)),
            "cost_price": float(row.get("cost_price", 0.0)),
            "base_price": float(row.get("base_price", 0.0)),
            "customer_rating": float(row.get("customer_rating", 0.0)),
            "expiry_date": str(row.get("expiry_date", "")),
        })
    return history


def _build_next_day_inventory(latest_record: dict) -> dict:
    latest_date = datetime.strptime(latest_record["date"], DATE_FORMAT)
    predicted_stock = max(0, latest_record["current_stock"] - latest_record["quantity_sold"])

    return {
        "date": (latest_date + timedelta(days=1)).strftime(DATE_FORMAT),
        "current_stock": predicted_stock,
        "quantity_sold": latest_record["quantity_sold"],
        "average_daily_sales": 0.0,
        "estimated_demand": 0.0,
    }
