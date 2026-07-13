"""
routers/crud.py
---------------
Raw CRUD endpoints: products, suppliers, inventory, sales,
inventory write-back, order approval, and simple dead-stock query.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import database
from ..models import (
    Product, Supplier, InventoryRecord, SalesRecord,
    InventoryUpdate, OrderApproval,
    ProductORM, SupplierORM, InventoryDailyORM, SalesORM,
)
from ..cache import invalidate_caches

router = APIRouter()


# ── Products ──────────────────────────────────────────────────────────

@router.get("/api/products", response_model=List[Product])
def get_products(db: Session = Depends(database.get_db)):
    return db.query(ProductORM).all()


@router.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int, db: Session = Depends(database.get_db)):
    row = db.query(ProductORM).filter(ProductORM.product_id == product_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return row


# ── Suppliers ─────────────────────────────────────────────────────────

@router.get("/api/suppliers", response_model=List[Supplier])
def get_suppliers(db: Session = Depends(database.get_db)):
    return db.query(SupplierORM).all()


# ── Inventory ─────────────────────────────────────────────────────────

@router.get("/api/inventory", response_model=List[InventoryRecord])
def get_inventory(
    product_id: Optional[int] = None,
    date: Optional[str] = None,
    db: Session = Depends(database.get_db),
):
    query = db.query(InventoryDailyORM)
    if product_id is not None:
        query = query.filter(InventoryDailyORM.product_id == product_id)
    if date is not None:
        query = query.filter(InventoryDailyORM.date == date)
    return query.all()


@router.get("/api/inventory/latest", response_model=List[InventoryRecord])
def get_latest_inventory(db: Session = Depends(database.get_db)):
    max_date = db.query(func.max(InventoryDailyORM.date)).scalar_subquery()
    return db.query(InventoryDailyORM).filter(InventoryDailyORM.date == max_date).all()


@router.get("/api/inventory/low_stock", response_model=List[InventoryRecord])
def get_low_stock(threshold: int = 20, db: Session = Depends(database.get_db)):
    max_date = db.query(func.max(InventoryDailyORM.date)).scalar_subquery()
    return db.query(InventoryDailyORM).filter(
        InventoryDailyORM.date == max_date,
        InventoryDailyORM.current_stock <= threshold,
    ).all()


# ── Sales ─────────────────────────────────────────────────────────────

@router.get("/api/sales", response_model=List[SalesRecord])
def get_sales(
    product_id: Optional[int] = None,
    date: Optional[str] = None,
    db: Session = Depends(database.get_db),
):
    query = db.query(SalesORM)
    if product_id is not None:
        query = query.filter(SalesORM.product_id == product_id)
    if date is not None:
        query = query.filter(SalesORM.date == date)
    return query.all()


# ── Write-backs ───────────────────────────────────────────────────────

@router.post("/api/update_inventory")
def update_inventory(update: InventoryUpdate, db: Session = Depends(database.get_db)):
    product_exists = (
        db.query(ProductORM)
        .filter(ProductORM.product_id == update.product_id)
        .first()
    )
    if not product_exists:
        raise HTTPException(status_code=404, detail=f"Product {update.product_id} not found")

    record = db.query(InventoryDailyORM).filter(
        InventoryDailyORM.product_id == update.product_id,
        InventoryDailyORM.date == update.date,
    ).first()

    if record:
        record.current_stock = update.current_stock
        record.expiry_date = update.expiry_date
    else:
        record = InventoryDailyORM(
            product_id=update.product_id,
            date=update.date,
            current_stock=update.current_stock,
            expiry_date=update.expiry_date,
        )
        db.add(record)

    db.commit()
    invalidate_caches()
    return {
        "status": "ok",
        "message": f"Inventory updated for product {update.product_id} on {update.date}",
    }


@router.post("/api/approve_order")
def approve_order(order: OrderApproval, db: Session = Depends(database.get_db)):
    product = (
        db.query(ProductORM)
        .filter(ProductORM.product_id == order.product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {order.product_id} not found")

    invalidate_caches()
    return {
        "status": "approved",
        "product_id": order.product_id,
        "product_name": product.product_name,
        "quantity": order.quantity,
        "supplier_id": order.supplier_id,
        "notes": order.notes,
    }


# ── Simple dead-stock query (raw SQL, no analytics layer) ─────────────

@router.get("/api/dead_stock")
def get_dead_stock(
    days: int = 14,
    max_units_sold: int = 5,
    db: Session = Depends(database.get_db),
):
    cutoff = db.query(
        func.date(func.max(SalesORM.date), f"-{days} days")
    ).scalar_subquery()
    rows = (
        db.query(SalesORM.product_id, func.sum(SalesORM.quantity_sold).label("total_sold"))
        .filter(SalesORM.date >= cutoff)
        .group_by(SalesORM.product_id)
        .having(func.sum(SalesORM.quantity_sold) <= max_units_sold)
        .all()
    )
    return [{"product_id": r.product_id, "total_sold": r.total_sold} for r in rows]
