from src.services.agentic_ai.state import State
from src.services.analytics.inventory_core import build_report, prepare_dataframe


def demand_agent(state: State):

    if state.get("error"):
        return state

    inventory_history = state.get("all_dates_inventory", [])

    if not inventory_history:
        state["error"] = "Inventory history not found."
        return state

    df = prepare_dataframe(inventory_history)

    report = build_report(df)

    product_name = state["inventory"]["product_name"].strip().lower()

    product = report[report["product_name"].astype(str).str.lower() == product_name]

    if product.empty:
        state["error"] = f"{product_name} not found in preprocessing report."
        return state

    row = product.iloc[0]

    state["demand"] = {
        "average_daily_sales": float(row["avg_daily_sales"]),
        "reorder_point": float(row["reorder_point"]),
        "safety_stock": float(row["safety_stock"]),
        "days_of_stock_left": float(row["days_of_stock_left"]),
        "stock_status": row["stock_status"],
    }

    for record in inventory_history:
        record["average_daily_sales"] = state["demand"]["average_daily_sales"]
        record["reorder_point"] = state["demand"]["reorder_point"]
        record["safety_stock"] = state["demand"]["safety_stock"]
        record["days_of_stock_left"] = state["demand"]["days_of_stock_left"]
        record["stock_status"] = state["demand"]["stock_status"]

    next_day = state.get("next_day_inventory")
    if isinstance(next_day, dict):
        next_day["average_daily_sales"] = state["demand"]["average_daily_sales"]
        next_day["reorder_point"] = state["demand"]["reorder_point"]
        next_day["safety_stock"] = state["demand"]["safety_stock"]
        next_day["days_of_stock_left"] = state["demand"]["days_of_stock_left"]
        next_day["stock_status"] = state["demand"]["stock_status"]

    return state
