"""
Inventory Core — Integration Layer for DB/API
================================================
Day 5 deliverable: every analytics function packaged as a pure,
side-effect-free function the DB/API architect can call directly.

DESIGN CONTRACT (read this before wiring it up):
  - Every function takes a pandas DataFrame (or list-of-dicts / list-of-rows,
    converted automatically) and returns a pandas DataFrame.
  - NOTHING in this file reads from disk, writes to disk, prints, or calls
    sys.exit(). All I/O (DB queries, file reads, HTTP responses) is the
    architect's responsibility, not this module's.
  - Bad input raises a normal Python exception (ValueError / KeyError),
    never sys.exit(). A server process must be able to catch it, turn it
    into a 400 response, and keep running.
  - to_json_records() is the one conversion helper provided for turning a
    result DataFrame into a JSON-serializable list of dicts for an API
    response. Everything else stays in DataFrame form, since that's what
    was explicitly requested for this handoff.

EXPECTED INPUT SCHEMA (one row per product per day):
    product_id        int
    product_name       str
    current_stock      int/float
    cost_price         float
    base_price         float
    date                str/datetime (parseable)
    quantity_sold       int/float
    customer_rating     float
    supplier_id         str
    avg_lead_time_day   int/float
    expiry_date         str/datetime (parseable, optional/nullable)

TYPICAL INTEGRATION (architect's code, not part of this file):

    from inventory_core import (
        prepare_dataframe, build_report, detect_dead_stock,
        build_supplier_scorecard, flag_supplier_alternatives,
        build_reorder_plan, to_json_records,
    )

    # --- From a SQL query ---
    rows = db.execute("SELECT * FROM inventory_transactions").fetchall()
    df = prepare_dataframe(rows)

    # --- From an API request body ---
    df = prepare_dataframe(request.json["rows"])

    # --- Run the pipeline ---
    report = build_report(df, service_level=0.95)
    dead_stock = detect_dead_stock(df, report, window_days=90)
    scorecard = build_supplier_scorecard(report)
    alt_flags = flag_supplier_alternatives(report, scorecard)
    plan = build_reorder_plan(report, budget=50000)

    # --- Respond to an API caller ---
    return jsonify(to_json_records(report))
"""

from typing import Union, List, Dict, Any

import pandas as pd
import numpy as np


REQUIRED_COLUMNS = [
    "product_id", "product_name", "current_stock", "cost_price",
    "base_price", "date", "quantity_sold", "customer_rating",
    "supplier_id", "avg_lead_time_day", "expiry_date",
]

Z_SCORE_TABLE = {
    0.90: 1.28,
    0.95: 1.65,
    0.975: 1.96,
    0.99: 2.33,
}

DEAD_STOCK_WINDOW_DAYS = 90


# ---------------------------------------------------------------------------
# INPUT NORMALIZATION
# ---------------------------------------------------------------------------

def prepare_dataframe(data: Union[pd.DataFrame, List[Dict[str, Any]], List[tuple]]) -> pd.DataFrame:
    """
    Normalize input into a clean, validated DataFrame ready for the rest of
    this module. Accepts:
      - an existing pandas DataFrame
      - a list of dicts (e.g. JSON request body, DB cursor.fetchall() with
        a DictCursor, or rows already converted to dicts)
      - a list of tuples/lists (e.g. a raw DB cursor.fetchall()) — in this
        case columns are assumed to be in REQUIRED_COLUMNS order

    Raises ValueError if required columns are missing or data is empty.
    Never calls sys.exit() — safe to call inside a server request handler.
    """
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, list):
        if len(data) == 0:
            raise ValueError("Input data is empty: no rows provided.")
        if isinstance(data[0], dict):
            df = pd.DataFrame(data)
        else:
            # Assume raw tuples/lists in REQUIRED_COLUMNS order
            df = pd.DataFrame(data, columns=REQUIRED_COLUMNS)
    else:
        raise ValueError(
            f"Unsupported input type: {type(data)}. "
            f"Expected pandas DataFrame, list of dicts, or list of tuples."
        )

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Input data is missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
    df["quantity_sold"] = pd.to_numeric(df["quantity_sold"], errors="coerce").fillna(0)
    df["current_stock"] = pd.to_numeric(df["current_stock"], errors="coerce").fillna(0)

    df = df.dropna(subset=["product_id", "date"])

    if df.empty:
        raise ValueError(
            "No valid rows remain after cleaning. Check that 'product_id' and "
            "'date' columns contain valid, parseable values."
        )

    return df


def to_json_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert a result DataFrame into a JSON-serializable list of dicts,
    for returning directly from an API endpoint (e.g. flask jsonify(),
    FastAPI response, etc.)

    Handles the two pandas types that don't serialize to plain JSON out of
    the box: Timestamp -> ISO date string, and inf/NaN -> None.
    """
    out = df.copy()

    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d").where(out[col].notna(), None)

    out = out.replace([np.inf, -np.inf], None)
    out = out.where(pd.notna(out), None)

    return out.to_dict(orient="records")


# ---------------------------------------------------------------------------
# CORE REPORT — avg daily sales, ROP, stock status
# ---------------------------------------------------------------------------

def get_zscore(service_level: float) -> float:
    """Return nearest Z-score for a given service level (0-1)."""
    closest = min(Z_SCORE_TABLE.keys(), key=lambda k: abs(k - service_level))
    return Z_SCORE_TABLE[closest]


def build_report(df: pd.DataFrame, service_level: float = 0.95) -> pd.DataFrame:
    """
    Aggregate historical sales per product and compute avg_daily_sales,
    days_of_stock_left, safety_stock, reorder_point (ROP), and stock_status
    (SAFE / LOW_STOCK / OUT_OF_STOCK). Pure function — no I/O.
    """
    z = get_zscore(service_level)

    latest = (
        df.sort_values("date")
        .groupby("product_id")
        .tail(1)[[
            "product_id", "product_name", "current_stock", "cost_price",
            "base_price", "customer_rating", "supplier_id", "avg_lead_time_day",
        ]]
        .reset_index(drop=True)
    )

    sales_stats = (
        df.groupby("product_id")["quantity_sold"]
        .agg(avg_daily_sales="mean", std_daily_sales="std", total_days="count")
        .reset_index()
    )
    sales_stats["std_daily_sales"] = sales_stats["std_daily_sales"].fillna(0)

    today = pd.Timestamp.today().normalize()
    upcoming_expiry = (
        df[df["expiry_date"] >= today]
        .groupby("product_id")["expiry_date"]
        .min()
        .reset_index()
        .rename(columns={"expiry_date": "nearest_expiry_date"})
    )

    report = latest.merge(sales_stats, on="product_id", how="left")
    report = report.merge(upcoming_expiry, on="product_id", how="left")

    safe_avg = report["avg_daily_sales"].replace(0, np.nan)

    report["days_of_stock_left"] = np.floor(report["current_stock"] / safe_avg)
    report["days_of_stock_left"] = report["days_of_stock_left"].fillna(np.inf)

    report["safety_stock"] = (
        z * report["std_daily_sales"] * np.sqrt(report["avg_lead_time_day"])
    ).round(1)

    report["reorder_point"] = (
        report["avg_daily_sales"] * report["avg_lead_time_day"] + report["safety_stock"]
    ).round(1)

    def classify(row):
        if row["current_stock"] <= 0:
            return "OUT_OF_STOCK"
        if row["current_stock"] <= row["reorder_point"]:
            return "LOW_STOCK"
        return "SAFE"

    report["stock_status"] = report.apply(classify, axis=1)

    if "nearest_expiry_date" in report.columns:
        report["days_to_expiry"] = (report["nearest_expiry_date"] - today).dt.days

    cols_order = [
        "product_id", "product_name", "supplier_id", "current_stock",
        "avg_daily_sales", "std_daily_sales", "avg_lead_time_day",
        "safety_stock", "reorder_point", "days_of_stock_left",
        "stock_status", "cost_price", "base_price", "customer_rating",
        "days_to_expiry",
    ]
    cols_order = [c for c in cols_order if c in report.columns]
    report = report[cols_order].sort_values("days_of_stock_left")

    return report.reset_index(drop=True)


# ---------------------------------------------------------------------------
# DEAD STOCK DETECTION
# ---------------------------------------------------------------------------

def detect_dead_stock(df: pd.DataFrame, report: pd.DataFrame,
                       window_days: int = DEAD_STOCK_WINDOW_DAYS) -> pd.DataFrame:
    """Flag products with zero quantity_sold in the last `window_days` calendar days."""
    today = pd.Timestamp.today().normalize()
    window_start = today - pd.Timedelta(days=window_days)

    recent = df[df["date"] >= window_start]
    sales_in_window = (
        recent.groupby("product_id")["quantity_sold"].sum().reset_index()
        .rename(columns={"quantity_sold": "units_sold_last_90d"})
    )

    earliest_date = df.groupby("product_id")["date"].min().reset_index()
    earliest_date = earliest_date.rename(columns={"date": "earliest_record_date"})
    earliest_date["days_of_history"] = (today - earliest_date["earliest_record_date"]).dt.days

    dead = report.merge(sales_in_window, on="product_id", how="left")
    dead = dead.merge(earliest_date, on="product_id", how="left")
    dead["units_sold_last_90d"] = dead["units_sold_last_90d"].fillna(0)

    dead["is_dead_stock"] = dead["units_sold_last_90d"] <= 0

    dead["suggested_markdown_price"] = np.where(
        dead["is_dead_stock"], (dead["base_price"] * 0.70).round(2), np.nan,
    )
    dead["holding_cost_exposure"] = np.where(
        dead["is_dead_stock"], (dead["current_stock"] * dead["cost_price"]).round(2), 0.0,
    )

    cols = [
        "product_id", "product_name", "supplier_id", "current_stock",
        "units_sold_last_90d", "days_of_history", "is_dead_stock",
        "cost_price", "base_price", "suggested_markdown_price",
        "holding_cost_exposure",
    ]
    cols = [c for c in cols if c in dead.columns]
    return dead[cols].sort_values(["is_dead_stock", "holding_cost_exposure"], ascending=[False, False])


# ---------------------------------------------------------------------------
# SUPPLIER SCORECARD
# ---------------------------------------------------------------------------

def build_supplier_scorecard(report: pd.DataFrame) -> pd.DataFrame:
    """Score every supplier by avg lead time + avg cost price (50/50, 0-100 scale)."""
    scorecard = (
        report.groupby("supplier_id")
        .agg(
            products_supplied=("product_id", "nunique"),
            avg_lead_time_day=("avg_lead_time_day", "mean"),
            avg_cost_price=("cost_price", "mean"),
        )
        .reset_index()
    )

    def normalize_inverse(series: pd.Series) -> pd.Series:
        lo, hi = series.min(), series.max()
        if hi == lo:
            return pd.Series(100.0, index=series.index)
        return 100 * (hi - series) / (hi - lo)

    scorecard["lead_time_score"] = normalize_inverse(scorecard["avg_lead_time_day"]).round(1)
    scorecard["cost_score"] = normalize_inverse(scorecard["avg_cost_price"]).round(1)
    scorecard["supplier_score"] = (
        0.5 * scorecard["lead_time_score"] + 0.5 * scorecard["cost_score"]
    ).round(1)

    scorecard = scorecard.sort_values("supplier_score", ascending=False).reset_index(drop=True)
    scorecard["rank"] = scorecard.index + 1
    return scorecard


def flag_supplier_alternatives(report: pd.DataFrame, scorecard: pd.DataFrame) -> pd.DataFrame:
    """For each at-risk product, flag whether a better-scoring supplier exists elsewhere."""
    at_risk = report[report["stock_status"].isin(["LOW_STOCK", "OUT_OF_STOCK"])].copy()
    if at_risk.empty:
        return at_risk.assign(
            current_supplier_score=pd.Series(dtype=float),
            best_alt_supplier=pd.Series(dtype=object),
            best_alt_supplier_score=pd.Series(dtype=float),
            better_supplier_available=pd.Series(dtype=bool),
        )

    score_lookup = scorecard.set_index("supplier_id")["supplier_score"]
    best_supplier_id = scorecard.iloc[0]["supplier_id"]
    best_supplier_score = scorecard.iloc[0]["supplier_score"]

    at_risk["current_supplier_score"] = at_risk["supplier_id"].map(score_lookup)
    at_risk["best_alt_supplier"] = best_supplier_id
    at_risk["best_alt_supplier_score"] = best_supplier_score
    at_risk["better_supplier_available"] = (
        at_risk["best_alt_supplier_score"] > at_risk["current_supplier_score"]
    ) & (at_risk["supplier_id"] != best_supplier_id)

    cols = [
        "product_id", "product_name", "supplier_id", "current_supplier_score",
        "best_alt_supplier", "best_alt_supplier_score", "better_supplier_available",
        "stock_status", "days_of_stock_left",
    ]
    return at_risk[cols].sort_values("better_supplier_available", ascending=False)


# ---------------------------------------------------------------------------
# BUDGET-CONSTRAINED REORDER PLAN
# ---------------------------------------------------------------------------

def build_reorder_plan(report: pd.DataFrame, budget: float) -> pd.DataFrame:
    """
    Build a candidate purchase order for every LOW_STOCK / OUT_OF_STOCK
    product and approve them urgency-first (skip-and-continue / first-fit)
    until the budget runs out. See module docstring history for full
    reasoning; behavior is unchanged from the standalone script version.
    """
    if budget < 0:
        raise ValueError(f"budget must be non-negative, got {budget}")

    candidates = report[report["stock_status"].isin(["LOW_STOCK", "OUT_OF_STOCK"])].copy()
    if candidates.empty:
        return candidates.assign(
            order_qty=pd.Series(dtype=float),
            order_cost=pd.Series(dtype=float),
            order_status=pd.Series(dtype=object),
            cumulative_spend=pd.Series(dtype=float),
        )

    candidates["order_qty"] = np.ceil(
        (candidates["reorder_point"] - candidates["current_stock"]).clip(lower=1)
    )
    candidates["order_cost"] = (candidates["order_qty"] * candidates["cost_price"]).round(2)

    candidates = candidates.sort_values("days_of_stock_left", ascending=True).reset_index(drop=True)

    cumulative = 0.0
    statuses = []
    cumulative_spend_list = []
    for cost in candidates["order_cost"]:
        if cumulative + cost <= budget:
            cumulative += cost
            statuses.append("APPROVED")
        else:
            statuses.append("DEFERRED")
        cumulative_spend_list.append(round(cumulative, 2))

    candidates["order_status"] = statuses
    candidates["cumulative_spend"] = cumulative_spend_list

    cols = [
        "product_id", "product_name", "supplier_id", "current_stock",
        "reorder_point", "days_of_stock_left", "stock_status",
        "order_qty", "cost_price", "order_cost", "order_status", "cumulative_spend",
    ]
    cols = [c for c in cols if c in candidates.columns]
    return candidates[cols]


# ---------------------------------------------------------------------------
# ONE-SHOT PIPELINE (convenience wrapper for the architect)
# ---------------------------------------------------------------------------

def run_full_pipeline(
    data: Union[pd.DataFrame, List[Dict[str, Any]], List[tuple]],
    service_level: float = 0.95,
    dead_stock_days: int = DEAD_STOCK_WINDOW_DAYS,
    budget: float = 0.0,
) -> Dict[str, pd.DataFrame]:
    """
    Convenience function: runs the entire analytics pipeline in one call
    and returns every result as a dict of DataFrames, keyed by name.
    Useful for a single API endpoint that needs everything at once
    (e.g. a dashboard GET /inventory/full-report).

    Returns:
        {
            "report": DataFrame,
            "dead_stock": DataFrame,
            "supplier_scorecard": DataFrame,
            "supplier_alternatives": DataFrame,
            "reorder_plan": DataFrame,
        }
    """
    df = prepare_dataframe(data)
    report = build_report(df, service_level=service_level)
    dead_stock = detect_dead_stock(df, report, window_days=dead_stock_days)
    scorecard = build_supplier_scorecard(report)
    alt_flags = flag_supplier_alternatives(report, scorecard)
    plan = build_reorder_plan(report, budget=budget)

    return {
        "report": report,
        "dead_stock": dead_stock,
        "supplier_scorecard": scorecard,
        "supplier_alternatives": alt_flags,
        "reorder_plan": plan,
    }