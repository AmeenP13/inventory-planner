"""
seed_database.py
-----------------
Day 1 task for Database & API Architect.

Builds inventory.db (SQLite) from schema.sql, then loads real data
from final_inventory_dataset_real_products.csv into the 4 normalized
tables: suppliers, products, inventory_daily, sales.

Run:
    python seed_database.py
"""

import sqlite3
import pandas as pd
import os 

CSV_PATH = "final_inventory_dataset_real_products.csv"
DB_PATH = "inventory.db"
SCHEMA_PATH = "schema.sql"


def build_schema(conn):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    print("Schema created.")


def load_csv():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded CSV: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def seed_suppliers(conn, df):
    suppliers = df["supplier_id"].drop_duplicates().sort_values()
    supplier_rows = [(sid, None) for sid in suppliers]
    conn.executemany(
        "INSERT OR IGNORE INTO suppliers (supplier_id, supplier_name) VALUES (?, ?)",
        supplier_rows,
    )
    print(f"Inserted {len(supplier_rows)} suppliers.")


def seed_products(conn, df):
    products = (
        df.sort_values("date")
        .groupby("product_id")
        .first()
        .reset_index()[
            ["product_id", "product_name", "cost_price", "base_price",
             "supplier_id", "avg_lead_time_day"]
        ]
    )
    conn.executemany(
        """INSERT OR IGNORE INTO products
           (product_id, product_name, cost_price, base_price, supplier_id, avg_lead_time_day)
           VALUES (?, ?, ?, ?, ?, ?)""",
        products.itertuples(index=False, name=None),
    )
    print(f"Inserted {len(products)} products.")


def seed_inventory_daily(conn, df):
    inv = df[["product_id", "date", "current_stock", "expiry_date"]]
    conn.executemany(
        """INSERT OR IGNORE INTO inventory_daily
           (product_id, date, current_stock, expiry_date)
           VALUES (?, ?, ?, ?)""",
        inv.itertuples(index=False, name=None),
    )
    print(f"Inserted {len(inv)} inventory_daily rows.")


def seed_sales(conn, df):
    sales = df[["product_id", "date", "quantity_sold", "customer_rating"]]
    conn.executemany(
        """INSERT OR IGNORE INTO sales
           (product_id, date, quantity_sold, customer_rating)
           VALUES (?, ?, ?, ?)""",
        sales.itertuples(index=False, name=None),
    )
    print(f"Inserted {len(sales)} sales rows.")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed old {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)

    df = load_csv()
    seed_suppliers(conn, df)
    seed_products(conn, df)
    seed_inventory_daily(conn, df)
    seed_sales(conn, df)

    conn.commit()
    conn.close()
    print(f"\nDone. Database written to {DB_PATH}")


if __name__ == "__main__":
    main()