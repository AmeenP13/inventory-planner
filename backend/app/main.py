"""
main.py
--------
FastAPI app — Database & API Architect role.

Run locally with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for the interactive Swagger UI
(this auto-generated docs page is the easiest way to show the Frontend
and Agent Engineer exactly what each endpoint returns).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from . import database
from .models import Product, Supplier, InventoryRecord, SalesRecord, InventoryUpdate, OrderApproval

app = FastAPI(title="Inventory Replenishment Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Inventory Replenishment Agent API is running"}


@app.get("/api/products", response_model=List[Product])
def get_products():
    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    conn = database.get_connection()
    row = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return dict(row)


@app.get("/api/suppliers", response_model=List[Supplier])
def get_suppliers():
    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM suppliers").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/inventory", response_model=List[InventoryRecord])
def get_inventory(product_id: Optional[int] = None, date: Optional[str] = None):
    conn = database.get_connection()
    query = "SELECT * FROM inventory_daily WHERE 1=1"
    params = []
    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)
    if date is not None:
        query += " AND date = ?"
        params.append(date)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/inventory/latest", response_model=List[InventoryRecord])
def get_latest_inventory():
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT i.* FROM inventory_daily i
        WHERE i.date = (SELECT MAX(date) FROM inventory_daily)
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/inventory/low_stock", response_model=List[InventoryRecord])
def get_low_stock(threshold: int = 20):
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT * FROM inventory_daily
        WHERE date = (SELECT MAX(date) FROM inventory_daily)
        AND current_stock <= ?
        """,
        (threshold,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/sales", response_model=List[SalesRecord])
def get_sales(product_id: Optional[int] = None, date: Optional[str] = None):
    conn = database.get_connection()
    query = "SELECT * FROM sales WHERE 1=1"
    params = []
    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)
    if date is not None:
        query += " AND date = ?"
        params.append(date)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/update_inventory")
def update_inventory(update: InventoryUpdate):
    conn = database.get_connection()
    exists = conn.execute(
        "SELECT 1 FROM products WHERE product_id = ?", (update.product_id,)
    ).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Product {update.product_id} not found")

    conn.execute(
        """
        INSERT INTO inventory_daily (product_id, date, current_stock, expiry_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(product_id, date) DO UPDATE SET
            current_stock = excluded.current_stock,
            expiry_date = excluded.expiry_date
        """,
        (update.product_id, update.date, update.current_stock, update.expiry_date),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": f"Inventory updated for product {update.product_id} on {update.date}"}


@app.post("/api/approve_order")
def approve_order(order: OrderApproval):
    conn = database.get_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (order.product_id,)
    ).fetchone()
    conn.close()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {order.product_id} not found")

    return {
        "status": "approved",
        "product_id": order.product_id,
        "product_name": product["product_name"],
        "quantity": order.quantity,
        "supplier_id": order.supplier_id,
        "notes": order.notes,
    }


@app.get("/api/dead_stock")
def get_dead_stock(days: int = 14, max_units_sold: int = 5):
    conn = database.get_connection()
    rows = conn.execute(
        f"""
        SELECT product_id, SUM(quantity_sold) as total_sold
        FROM sales
        WHERE date >= (SELECT date(MAX(date), '-{days} days') FROM sales)
        GROUP BY product_id
        HAVING total_sold <= ?
        """,
        (max_units_sold,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]