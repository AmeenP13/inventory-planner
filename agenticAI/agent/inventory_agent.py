import os
import json
import pandas as pd
from state import state
from config import llm

def extract_product_and_date(query: str):
    prompt = f"""
Analyze the user query: "{query}"
We need to extract:
1. "product": The name of the product the user is asking about.
2. "date": The specific date they are asking about (if any), formatted exactly as YYYY-MM-DD. 
   - If they ask for "all dates", "every date", "every day", "everyday", "history", "trend", "all data", or similar terms indicating they want the full history or all dates, set this to "all".
   - If they ask for "today" or "now", or don't specify any date, return null.

Return ONLY a valid JSON object. Do not include markdown code block syntax.

Example 1:
Query: "Tell me about Apple on June 5th, 2026"
Output: {{"product": "Apple", "date": "2026-06-05"}}

Example 2:
Query: "Show me all dates for Orange"
Output: {{"product": "Orange", "date": "all"}}

Example 3:
Query: "What is the status of Orange?"
Output: {{"product": "Orange", "date": null}}
"""
    try:
        response = llm.invoke(prompt)
        text = response.content.strip()
        # Remove markdown code block markers if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                text = "\n".join(lines[1:-1])
        data = json.loads(text.strip())
        return data.get("product"), data.get("date")
    except Exception as e:
        return None, None

def inventory_agent(state: state):
    # Locate dataset path relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "..", "data", "final_inventory_dataset_real_products.csv")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        state["error"] = f"Error loading CSV file: {str(e)}"
        return state

    # Extract user input query
    user_query = state['message'][-1]
    extracted_product, extracted_date = extract_product_and_date(user_query)
    
    if not extracted_product:
        state["error"] = f"Could not determine the product name from your query: '{user_query}'"
        return state

    # Try matching product name case-insensitively
    product_query = str(extracted_product).strip().lower()
    product_df = df[df['product_name'].str.lower() == product_query]
    
    # Substring matching fallback if exact match not found
    if product_df.empty:
        product_df = df[df['product_name'].str.lower().str.contains(product_query, na=False)]
        
    if product_df.empty:
        state["error"] = f"Product '{extracted_product}' was not found in the inventory dataset."
        return state

    # Sort product rows chronologically by date
    product_df = product_df.sort_values("date")

    # If "all" dates are requested, populate history list
    if extracted_date == "all":
        all_dates_list = []
        for _, row in product_df.iterrows():
            all_dates_list.append({
                "date": row["date"],
                "current_stock": int(row["current_stock"]),
                "quantity_sold": int(row["quantity_sold"])
            })
        state["all_dates_inventory"] = all_dates_list
        state["next_day_inventory"] = None
        # Default target row to the latest record for downstream agents
        product_row = product_df.iloc[-1].to_dict()
    else:
        state["all_dates_inventory"] = None
        # Find the target date row and next date row
        if extracted_date:
            date_df = product_df[product_df['date'] == extracted_date]
            if not date_df.empty:
                product_row = date_df.iloc[0].to_dict()
                
                # Find the position of the target row in the sorted dataframe
                idx = date_df.index[0]
                sorted_indices = list(product_df.index)
                pos = sorted_indices.index(idx)
                
                if pos + 1 < len(sorted_indices):
                    next_row = product_df.iloc[pos + 1].to_dict()
                    state["next_day_inventory"] = {
                        "date": next_row["date"],
                        "current_stock": int(next_row["current_stock"]),
                        "quantity_sold": int(next_row["quantity_sold"]),
                    }
                else:
                    state["next_day_inventory"] = None
            else:
                # Fallback if specific date is not found: default to latest available
                if len(product_df) >= 2:
                    product_row = product_df.iloc[-2].to_dict()
                    next_row = product_df.iloc[-1].to_dict()
                    state["next_day_inventory"] = {
                        "date": next_row["date"],
                        "current_stock": int(next_row["current_stock"]),
                        "quantity_sold": int(next_row["quantity_sold"]),
                    }
                else:
                    product_row = product_df.iloc[-1].to_dict()
                    state["next_day_inventory"] = None
        else:
            # Default to latest date, showing the second-to-last as target and last as next
            if len(product_df) >= 2:
                product_row = product_df.iloc[-2].to_dict()
                next_row = product_df.iloc[-1].to_dict()
                state["next_day_inventory"] = {
                    "date": next_row["date"],
                    "current_stock": int(next_row["current_stock"]),
                    "quantity_sold": int(next_row["quantity_sold"]),
                }
            else:
                product_row = product_df.iloc[-1].to_dict()
                state["next_day_inventory"] = None

    state["inventory"] = {
        "product_name": product_row["product_name"],
        "current_stock": int(product_row["current_stock"]),
        "quantity_sold": int(product_row["quantity_sold"]),
        "supplier_id": product_row["supplier_id"],
        "lead_time": int(product_row["avg_lead_time_day"]),
        "cost_price": float(product_row["cost_price"]),
        "base_price": float(product_row["base_price"]),
        "customer_rating": float(product_row["customer_rating"]),
        "expiry_date": product_row["expiry_date"],
        "query_date": product_row["date"]  # Store the actual date retrieved
    }
    
    return state
