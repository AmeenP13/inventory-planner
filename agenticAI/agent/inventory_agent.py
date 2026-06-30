from state import State
import pandas as pd
def inventory_agent(state: State):
    df = pd.read_csv("agenticAI/data/final_inventory_dataset_real_products.csv")
    product_name = state["message"][-1].content.lower().strip()
    products = df[df["product_name"].str.lower().str.strip() == product_name]
    if products.empty:
        state["error"] = f"Product '{product_name}' not found."
        return state
    products = products.sort_values("date")
    inventory_history = []

    for _, product in products.iterrows():
        inventory_history.append({
            "date": product["date"],
            "product_name": product["product_name"],
            "current_stock": int(product["current_stock"]),
            "quantity_sold": int(product["quantity_sold"]),
            "supplier_id": product["supplier_id"],
            "lead_time": int(product["avg_lead_time_day"]),
            "cost_price": float(product["cost_price"]),
            "base_price": float(product["base_price"]),
            "customer_rating": float(product["customer_rating"]),
            "expiry_date": product["expiry_date"]
        })
    state["all_dates_inventory"] = inventory_history
    latest = inventory_history[-1]

    state["inventory"] = latest

    return state