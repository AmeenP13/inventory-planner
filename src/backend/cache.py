"""
cache.py
--------
Shared cache state, cache invalidation helper, and report-building
helpers shared by all router modules.
"""

from typing import Optional
import pandas as pd
import numpy as np
from sqlalchemy import func
from pydantic import BaseModel

from . import database
from .models import ProductORM, InventoryDailyORM, SalesORM

# ── Global in-process caches ──────────────────────────────────────────
_PROPOSAL_CACHE: Optional[dict] = None
_REPORT_CACHE: Optional[pd.DataFrame] = None
_OVERVIEW_CACHE: Optional[dict] = None
_RAW_DF_CACHE: Optional[pd.DataFrame] = None


def invalidate_caches() -> None:
    """Clear all four in-process caches (call after any DB write)."""
    global _PROPOSAL_CACHE, _REPORT_CACHE, _OVERVIEW_CACHE, _RAW_DF_CACHE
    _PROPOSAL_CACHE = None
    _REPORT_CACHE = None
    _OVERVIEW_CACHE = None
    _RAW_DF_CACHE = None


# ── Pydantic request schema shared by agent router ────────────────────
class ReplenishRequest(BaseModel):
    product_name: Optional[str] = None


# ── Category helper ───────────────────────────────────────────────────
def get_product_category(name: str) -> str:
    """Map a product name to its broad category string."""
    name_lower = name.lower()
    if any(x in name_lower for x in ["apple", "banana", "orange", "grape", "fruit", "vegetable"]):
        return "Produce"
    if any(x in name_lower for x in ["milk", "butter", "cheese", "yogurt", "cream", "dairy"]):
        return "Dairy"
    if any(x in name_lower for x in ["bread", "cake", "cookie", "pastry", "bakery"]):
        return "Bakery"
    if any(x in name_lower for x in ["coffee", "tea", "water", "soda", "juice", "beverage"]):
        return "Beverages"
    if any(x in name_lower for x in ["chicken", "beef", "pork", "meat", "fish", "salmon"]):
        return "Meat"
    return "Groceries"


# ── Core data-loading helpers ─────────────────────────────────────────
def get_raw_and_aggregated_data(service_level: float = 0.95):
    """
    Load all inventory + sales rows from the DB, build the analytics
    report via ``build_report``, cache both, and return (df, report).
    """
    global _RAW_DF_CACHE, _REPORT_CACHE
    if _REPORT_CACHE is not None and _RAW_DF_CACHE is not None:
        return _RAW_DF_CACHE, _REPORT_CACHE

    from src.services.analytics.inventory_management import build_report
    from .database import get_db_session

    with get_db_session() as db:
        query = db.query(
            InventoryDailyORM.product_id,
            ProductORM.product_name,
            InventoryDailyORM.current_stock,
            ProductORM.cost_price,
            ProductORM.base_price,
            InventoryDailyORM.date,
            func.coalesce(SalesORM.quantity_sold, 0).label("quantity_sold"),
            func.coalesce(SalesORM.customer_rating, 0.0).label("customer_rating"),
            ProductORM.supplier_id,
            ProductORM.avg_lead_time_day,
            InventoryDailyORM.expiry_date,
        ).join(
            ProductORM, InventoryDailyORM.product_id == ProductORM.product_id
        ).outerjoin(
            SalesORM,
            (InventoryDailyORM.product_id == SalesORM.product_id)
            & (InventoryDailyORM.date == SalesORM.date),
        )
        df = pd.read_sql_query(query.statement, db.bind)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
    df["quantity_sold"] = pd.to_numeric(df["quantity_sold"], errors="coerce").fillna(0)
    df = df.dropna(subset=["product_id", "date"])

    report = build_report(df, service_level=service_level)
    _REPORT_CACHE = report
    _RAW_DF_CACHE = df
    return df, report


def get_combined_report(service_level: float = 0.95) -> pd.DataFrame:
    """Return just the aggregated report DataFrame (caches on first call)."""
    return get_raw_and_aggregated_data(service_level)[1]
