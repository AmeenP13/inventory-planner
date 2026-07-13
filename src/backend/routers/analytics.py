"""
routers/analytics.py
--------------------
Advanced analytics endpoints:
  GET /api/analytics/dead_stock
  GET /api/analytics/supplier_scorecard
  GET /api/analytics/supplier_alternatives
  GET /api/analytics/reorder_plan
"""

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from ..cache import get_combined_report, get_raw_and_aggregated_data

router = APIRouter()


@router.get("/api/analytics/dead_stock")
def get_analytics_dead_stock(days: int = 90):
    """Identify slow-moving / dead stock and suggest markdown prices."""
    try:
        from src.services.analytics.inventory_advance import detect_dead_stock
        df, report = get_raw_and_aggregated_data()
        dead_df = detect_dead_stock(df, report, window_days=days)

        records = []
        for _, row in dead_df.iterrows():
            records.append({
                "product_id": int(row["product_id"]),
                "sku": f"PRD-{row['product_id']:04d}",
                "product": row["product_name"],
                "supplier": row["supplier_id"],
                "stock": int(row["current_stock"]),
                "units_sold_last_90d": int(row["units_sold_last_90d"]),
                "days_of_history": int(row["days_of_history"]),
                "is_dead_stock": bool(row["is_dead_stock"]),
                "cost_price": float(row["cost_price"]),
                "base_price": float(row["base_price"]),
                "suggested_markdown_price": (
                    float(row["suggested_markdown_price"])
                    if pd.notnull(row["suggested_markdown_price"])
                    else None
                ),
                "holding_cost_exposure": float(row["holding_cost_exposure"]),
            })
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dead stock calculation failed: {e}")


@router.get("/api/analytics/supplier_scorecard")
def get_analytics_supplier_scorecard():
    """Rank suppliers by a weighted lead-time + cost score."""
    try:
        from src.services.analytics.inventory_advance import build_supplier_scorecard
        report = get_combined_report()
        scorecard = build_supplier_scorecard(report)

        records = []
        for _, row in scorecard.iterrows():
            records.append({
                "rank": int(row["rank"]),
                "supplier_id": row["supplier_id"],
                "products_supplied": int(row["products_supplied"]),
                "avg_lead_time_day": float(row["avg_lead_time_day"]),
                "avg_cost_price": float(row["avg_cost_price"]),
                "lead_time_score": float(row["lead_time_score"]),
                "cost_score": float(row["cost_score"]),
                "supplier_score": float(row["supplier_score"]),
            })
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supplier scorecard calculation failed: {e}")


@router.get("/api/analytics/supplier_alternatives")
def get_analytics_supplier_alternatives():
    """Flag at-risk items that have a better-scoring alternative supplier."""
    try:
        from src.services.analytics.inventory_advance import (
            build_supplier_scorecard,
            flag_supplier_alternatives,
        )
        report = get_combined_report()
        scorecard = build_supplier_scorecard(report)
        alternatives = flag_supplier_alternatives(report, scorecard)

        records = []
        if not alternatives.empty:
            for _, row in alternatives.iterrows():
                records.append({
                    "product_id": int(row["product_id"]),
                    "sku": row["sku"] if "sku" in row else f"PRD-{row['product_id']:04d}",
                    "product": row["product_name"],
                    "supplier_id": row["supplier_id"],
                    "current_supplier_score": (
                        float(row["current_supplier_score"])
                        if pd.notnull(row["current_supplier_score"])
                        else None
                    ),
                    "best_alt_supplier": row["best_alt_supplier"],
                    "best_alt_supplier_score": (
                        float(row["best_alt_supplier_score"])
                        if pd.notnull(row["best_alt_supplier_score"])
                        else None
                    ),
                    "better_supplier_available": bool(row["better_supplier_available"]),
                    "stock_status": row["stock_status"],
                    "days_of_stock_left": (
                        float(row["days_of_stock_left"])
                        if pd.notnull(row["days_of_stock_left"]) and row["days_of_stock_left"] != np.inf
                        else 999.0
                    ),
                })
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alternative supplier flagging failed: {e}")


@router.get("/api/analytics/reorder_plan")
def get_analytics_reorder_plan(budget: float = 15000.0):
    """Return a budget-constrained procurement plan sorted by urgency."""
    try:
        from src.services.analytics.inventory_advance import build_reorder_plan
        report = get_combined_report()
        plan = build_reorder_plan(report, budget=budget)

        records = []
        for _, row in plan.iterrows():
            records.append({
                "product_id": int(row["product_id"]),
                "sku": row["sku"] if "sku" in row else f"PRD-{row['product_id']:04d}",
                "product": row["product_name"],
                "supplier_id": row["supplier_id"],
                "stock": int(row["current_stock"]),
                "reorder_point": float(row["reorder_point"]),
                "days_left": (
                    float(row["days_of_stock_left"])
                    if pd.notnull(row["days_of_stock_left"]) and row["days_of_stock_left"] != np.inf
                    else 999.0
                ),
                "status": row["stock_status"],
                "order_qty": int(row["order_qty"]),
                "cost_price": float(row["cost_price"]),
                "order_cost": float(row["order_cost"]),
                "order_status": row["order_status"],
                "cumulative_spend": float(row["cumulative_spend"]),
            })
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reorder plan calculation failed: {e}")
