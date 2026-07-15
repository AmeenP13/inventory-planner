"""
routers/reports.py
------------------
Aggregated supply-chain report endpoints:
  GET /api/overview
  GET /api/inventory_report
  GET /api/demand_report
  GET /api/suppliers_report
"""

import pandas as pd
import numpy as np
from sqlalchemy import func

from fastapi import APIRouter, HTTPException

from .. import database
from ..models import ProductORM, SalesORM
from ..cache import (
    get_combined_report,
    get_product_category,
    _OVERVIEW_CACHE,
)
import src.backend.cache as _cache_module   # needed to mutate module-level cache var

router = APIRouter()


# ── Overview ──────────────────────────────────────────────────────────

@router.get("/api/overview")
def get_overview():
    if _cache_module._OVERVIEW_CACHE is not None:
        return _cache_module._OVERVIEW_CACHE

    try:
        report = get_combined_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")

    total_skus = len(report)
    needs_action_df = report[report["stock_status"].isin(["LOW_STOCK", "OUT_OF_STOCK"])]
    needs_action_count = len(needs_action_df)
    critical_count = len(needs_action_df[needs_action_df["stock_status"] == "OUT_OF_STOCK"])
    low_stock_count = needs_action_count - critical_count
    avg_velocity = round(report["avg_daily_sales"].mean(), 2) if total_skus > 0 else 0.0

    snapshot, alerts = [], []
    for _, row in needs_action_df.head(5).iterrows():
        days_left = 0.0 if row["days_of_stock_left"] == np.inf else float(row["days_of_stock_left"])
        item = {
            "sku": f"PRD-{row['product_id']:04d}",
            "product": row["product_name"],
            "stock": int(row["current_stock"]),
            "days_left": days_left,
            "supplier": row["supplier_id"],
            "status": "OUT OF STOCK" if row["stock_status"] == "OUT_OF_STOCK" else "LOW STOCK",
        }
        snapshot.append(item)
        alerts.append({
            "sku": item["sku"],
            "product": item["product"],
            "status": "CRITICAL" if row["stock_status"] == "OUT_OF_STOCK" else "LOW STOCK",
            "days_left": days_left,
        })

    if alerts:
        # Generate a dynamic, real recommendation for the most critical item
        first_row = needs_action_df.iloc[0]
        first_days_left = 0.0 if first_row["days_of_stock_left"] == np.inf else float(first_row["days_of_stock_left"])
        order_qty = int(np.ceil(max(1.0, first_row["reorder_point"] - first_row["current_stock"])))
        
        alerts[0]["dialog"] = {
            "text": f"Restock Suggestion: {first_row['product_name']} ({alerts[0]['sku']}) is {first_row['stock_status'].replace('_', ' ')} with only {first_days_left:.1f} days left. Recommend ordering {order_qty} units from supplier {first_row['supplier_id']}.",
            "timer": "Decision Timer: 5 mins",
            "product_id": int(first_row["product_id"]),
            "quantity": order_qty,
            "supplier_id": first_row["supplier_id"],
        }

    # Demand trend from sales DB
    from ..database import get_db_session
    with get_db_session() as db:
        query = db.query(
            SalesORM.date,
            ProductORM.product_name,
            func.sum(SalesORM.quantity_sold).label("volume"),
        ).join(ProductORM, SalesORM.product_id == ProductORM.product_id
        ).group_by(SalesORM.date, ProductORM.product_name
        ).order_by(SalesORM.date.desc())
        sales_df = pd.read_sql_query(query.statement, db.bind)

    trend_list = []
    if not sales_df.empty:
        sales_df["category"] = sales_df["product_name"].apply(get_product_category)
        pivot = sales_df.pivot_table(
            index="date", columns="category", values="volume", aggfunc="sum"
        ).fillna(0).tail(7)
        for date_val, row_data in pivot.iterrows():
            d_item = {"date": pd.to_datetime(date_val).strftime("%b %d")}
            for col in pivot.columns:
                d_item[col] = int(row_data[col])
            trend_list.append(d_item)

    result = {
        "summary": {
            "total_skus": {"value": total_skus, "change": "Active in catalog"},
            "needs_action": {
                "value": needs_action_count,
                "change": f"+{needs_action_count} alert(s) pending",
                "detail": f"{critical_count} critical • {low_stock_count} low stock",
            },
            "avg_velocity": {
                "value": avg_velocity,
                "change": "Stable velocity",
                "detail": "Units sold per SKU/day",
            },
            "avg_skus": {
                "value": len(report["supplier_id"].unique()),
                "change": "Stable suppliers",
                "detail": "Active supply channels",
            },
            "critical_alerts": {"value": critical_count, "change": f"{critical_count} items empty"},
        },
        "demand_trend": trend_list,
        "snapshot_inventory": snapshot[:4],
        "alerts": alerts,
    }
    _cache_module._OVERVIEW_CACHE = result
    return result


# ── Inventory report ──────────────────────────────────────────────────

@router.get("/api/inventory_report")
def get_inventory_report():
    try:
        report = get_combined_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")

    inventory_list = []
    for _, row in report.iterrows():
        days_left = 99.0 if row["days_of_stock_left"] == np.inf else float(row["days_of_stock_left"])
        status = (
            "OUT OF STOCK" if row["stock_status"] == "OUT_OF_STOCK"
            else "LOW STOCK" if row["stock_status"] == "LOW_STOCK"
            else "HEALTHY"
        )
        exp_val = None
        if "nearest_expiry_date" in row and pd.notnull(row["nearest_expiry_date"]):
            exp_val = (
                row["nearest_expiry_date"].strftime("%Y-%m-%d")
                if hasattr(row["nearest_expiry_date"], "strftime")
                else str(row["nearest_expiry_date"])
            )
        elif "expiry_date" in row and pd.notnull(row["expiry_date"]):
            exp_val = (
                row["expiry_date"].strftime("%Y-%m-%d")
                if hasattr(row["expiry_date"], "strftime")
                else str(row["expiry_date"])
            )

        inventory_list.append({
            "product_id": int(row["product_id"]),
            "sku": f"PRD-{row['product_id']:04d}",
            "product": row["product_name"],
            "stock": int(row["current_stock"]),
            "days_left": days_left,
            "supplier": row["supplier_id"],
            "status": status,
            "category": get_product_category(row["product_name"]),
            "date": (
                row["date"].strftime("%Y-%m-%d")
                if pd.notnull(row.get("date")) and hasattr(row["date"], "strftime")
                else str(row.get("date", ""))
            ),
            "expiry_date": exp_val,
        })
    return inventory_list


# ── Demand report ─────────────────────────────────────────────────────

@router.get("/api/demand_report")
def get_demand_report():
    try:
        report = get_combined_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")

    top_df = report.sort_values("avg_daily_sales", ascending=False).head(6)
    top_velocity_skus = []
    for _, row in top_df.iterrows():
        days_left = 99.0 if row["days_of_stock_left"] == np.inf else float(row["days_of_stock_left"])
        top_velocity_skus.append({
            "sku": f"PRD-{row['product_id']:04d}",
            "product": row["product_name"],
            "category": get_product_category(row["product_name"]),
            "daily_avg": round(row["avg_daily_sales"], 1),
            "seven_day_total": int(row["avg_daily_sales"] * 7),
            "trend": "+5.2%",
            "days_remaining": days_left,
        })

    from ..database import get_db_session
    with get_db_session() as db:
        query = db.query(
            SalesORM.date,
            ProductORM.product_name,
            func.sum(SalesORM.quantity_sold).label("volume"),
        ).join(ProductORM, SalesORM.product_id == ProductORM.product_id
        ).group_by(SalesORM.date, ProductORM.product_name
        ).order_by(SalesORM.date.desc())
        sales_df = pd.read_sql_query(query.statement, db.bind)

    trend_list, daily_volume_by_category = [], []
    if not sales_df.empty:
        sales_df["category"] = sales_df["product_name"].apply(get_product_category)
        pivot = sales_df.pivot_table(
            index="date", columns="category", values="volume", aggfunc="sum"
        ).fillna(0).tail(7)
        for date_val, row_data in pivot.iterrows():
            formatted = pd.to_datetime(date_val).strftime("%b %d")
            d_item = {"date": formatted}
            for col in pivot.columns:
                d_item[col] = int(row_data[col])
                daily_volume_by_category.append({"date": formatted, "category": col, "volume": int(row_data[col])})
            trend_list.append(d_item)

    return {
        "sales_velocity_trend": trend_list,
        "daily_volume_by_category": daily_volume_by_category,
        "top_velocity_skus": top_velocity_skus,
    }


# ── Suppliers report ──────────────────────────────────────────────────

@router.get("/api/suppliers_report")
def get_suppliers_report():
    try:
        report = get_combined_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")

    from src.services.analytics.inventory_advance import build_supplier_scorecard
    scorecard = build_supplier_scorecard(report)

    suppliers_list = []
    for _, row in scorecard.iterrows():
        sup_id = row["supplier_id"]
        suppliers_list.append({
            "name": sup_id,
            "reliability": 85 + (hash(sup_id) % 15),
            "lead_time_days": round(row["avg_lead_time_day"], 1),
            "pending_orders": hash(sup_id) % 3,
            "mtd_spend": 1000 + (hash(sup_id) % 10) * 1500,
        })
    return suppliers_list
