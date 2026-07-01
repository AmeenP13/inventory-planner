"""
Inventory Advanced Analytics
=============================
Extends the base inventory report (inventory_management.py) with three
additional capabilities:

1. DEAD STOCK DETECTION
   Flags products with zero sales in the last 90 days (relative to today),
   so they can be reviewed for markdown, return-to-supplier, or write-off
   to reduce holding costs.

2. SUPPLIER SCORECARD
   Ranks every supplier in the dataset by average lead time and average
   cost price across the products they supply. For each LOW_STOCK /
   OUT_OF_STOCK product, flags whether a better-scoring supplier exists
   elsewhere in the dataset than the product's current supplier.
   NOTE: this is a "worth investigating" flag, not a guaranteed swap —
   the dataset only records one supplier per product, so we don't know
   if the better-scoring supplier can actually supply this exact item.

3. BUDGET-CONSTRAINED REORDER PLAN
   Builds a suggested purchase order for every LOW_STOCK / OUT_OF_STOCK
   product (reorder_point - current_stock units, at cost_price), then
   fits as many orders as possible within --budget, prioritizing the
   most urgent stockouts first (lowest days_of_stock_left). Orders that
   don't fit are marked DEFERRED rather than silently dropped.

Usage:
    python inventory_advance.py --csv my_data.csv --budget 50000

Outputs:
    - dead_stock_report.csv
    - supplier_scorecard.csv
    - reorder_plan.csv          (APPROVED + DEFERRED purchase orders)
    - Console summary of all three
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import numpy as np

from inventory_management import load_data, build_report, safe_to_csv

DEAD_STOCK_WINDOW_DAYS = 90


# ---------------------------------------------------------------------------
# 1. DEAD STOCK DETECTION
# ---------------------------------------------------------------------------

def detect_dead_stock(df: pd.DataFrame, report: pd.DataFrame,
                       window_days: int = DEAD_STOCK_WINDOW_DAYS) -> pd.DataFrame:
    """
    Flag products with zero quantity_sold in the last `window_days` calendar
    days from today. If a product has less than `window_days` of history
    available, it's judged on whatever history exists (can't penalize a
    new product for not having 90 days of data yet).
    """
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

    # Suggested 30% markdown for flagged items, applied to base_price
    dead["suggested_markdown_price"] = np.where(
        dead["is_dead_stock"],
        (dead["base_price"] * 0.70).round(2),
        np.nan,
    )

    # Holding cost exposure: what's tied up in this dead stock at cost price
    dead["holding_cost_exposure"] = np.where(
        dead["is_dead_stock"],
        (dead["current_stock"] * dead["cost_price"]).round(2),
        0.0,
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
# 2. SUPPLIER SCORECARD
# ---------------------------------------------------------------------------

def build_supplier_scorecard(report: pd.DataFrame) -> pd.DataFrame:
    """
    Score every supplier in the dataset by:
      - avg_lead_time_day across the products they supply (lower = better)
      - avg cost_price across the products they supply (lower = better)
    Combines both into a single 0-100 supplier_score (50/50 weight) using
    min-max normalization, so it's comparable across suppliers regardless
    of raw units.
    """
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
        """Lower raw value -> higher normalized score (0-100). Flat series -> all 100."""
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
    """
    For each LOW_STOCK / OUT_OF_STOCK product, check whether a better-scoring
    supplier exists than the one currently assigned. This is a flag for
    manual review, not an automatic reassignment.
    """
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
# 3. BUDGET-CONSTRAINED REORDER PLAN
# ---------------------------------------------------------------------------

def build_reorder_plan(report: pd.DataFrame, budget: float) -> pd.DataFrame:
    """
    Build a candidate purchase order for every LOW_STOCK / OUT_OF_STOCK
    product: order_qty = reorder_point - current_stock (at least 1 unit),
    order_cost = order_qty * cost_price.

    Sorts candidates by urgency (lowest days_of_stock_left first, i.e. the
    soonest stockouts) and walks the list in that order. An order is
    APPROVED if it fits in whatever budget remains at that point; otherwise
    it's marked DEFERRED and the function moves on to the next (less
    urgent) candidate rather than stopping — so a cheap, less-urgent order
    can still get approved even if a more urgent, expensive order didn't
    fit. This maximizes how many urgent needs get addressed within budget,
    but means "most urgent" and "approved" don't always align: a very
    expensive, very urgent order can be deferred while a cheaper, less
    urgent one is approved. Deferred high-urgency orders are still listed
    first in the output so they're not missed.
    """
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

    # Urgency-first: lowest days_of_stock_left goes first. Infinite values
    # (no sales history) sort last since they're not urgent by this measure.
    candidates = candidates.sort_values("days_of_stock_left", ascending=True).reset_index(drop=True)

    cumulative = 0.0
    statuses = []
    cumulative_spend_list = []
    for cost in candidates["order_cost"]:
        if cumulative + cost <= budget:
            cumulative += cost
            statuses.append("APPROVED")
        else:
            statuses.append("DEFERRED")  # doesn't fit now; keep checking remaining (less urgent) orders
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


def print_budget_summary(plan: pd.DataFrame, budget: float) -> None:
    if plan.empty:
        print("No products require reordering. Budget untouched.\n")
        return

    approved = plan[plan["order_status"] == "APPROVED"]
    deferred = plan[plan["order_status"] == "DEFERRED"]
    total_approved_cost = approved["order_cost"].sum()
    total_deferred_cost = deferred["order_cost"].sum()

    print("=" * 60)
    print("BUDGET-CONSTRAINED REORDER PLAN")
    print("=" * 60)
    print(f"Available budget       : {budget:,.2f}")
    print(f"Approved orders        : {len(approved)}  (total cost: {total_approved_cost:,.2f})")
    print(f"Deferred orders        : {len(deferred)}  (total cost if funded: {total_deferred_cost:,.2f})")
    print(f"Remaining budget       : {budget - total_approved_cost:,.2f}")
    print("=" * 60)

    if not deferred.empty:
        print(f"\n{len(deferred)} order(s) deferred due to budget limits "
              f"(most urgent deferred items shown):")
        print(deferred.head(10)[
            ["product_id", "product_name", "days_of_stock_left", "order_cost", "order_status"]
        ].to_string(index=False))

        # Flag cases where a deferred order is MORE urgent than an approved one,
        # since "approved" and "most urgent" don't always align under first-fit allocation.
        if not approved.empty:
            most_urgent_deferred = deferred["days_of_stock_left"].min()
            less_urgent_approved = approved[approved["days_of_stock_left"] > most_urgent_deferred]
            if not less_urgent_approved.empty:
                print(f"\n  NOTE: some deferred orders are MORE urgent (sooner stockout) than "
                      f"orders that WERE approved, because a smaller/cheaper order further down "
                      f"the list still fit in the remaining budget. Review deferred items above "
                      f"manually if a specific stockout is critical.")
    print()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Dead stock detection, supplier scorecard, and budget-constrained reorder planning"
    )
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument("--service-level", type=float, default=0.95,
                         help="Target service level for safety stock (used in base report)")
    parser.add_argument("--budget", type=float, required=True,
                         help="Available procurement budget for the reorder plan")
    parser.add_argument("--dead-stock-days", type=int, default=DEAD_STOCK_WINDOW_DAYS,
                         help=f"Days with zero sales to flag as dead stock (default: {DEAD_STOCK_WINDOW_DAYS})")
    parser.add_argument("--dead-stock-out", default="dead_stock_report.csv")
    parser.add_argument("--supplier-out", default="supplier_scorecard.csv")
    parser.add_argument("--reorder-plan-out", default="reorder_plan.csv")
    args = parser.parse_args()

    print(f"Loading data from: {args.csv}")
    df = load_data(args.csv)
    report = build_report(df, service_level=args.service_level)
    print(f"Loaded {len(df)} rows across {df['product_id'].nunique()} products.\n")

    # --- 1. Dead stock ---
    dead_stock = detect_dead_stock(df, report, window_days=args.dead_stock_days)
    n_dead = dead_stock["is_dead_stock"].sum()
    print(f"Dead stock check ({args.dead_stock_days}-day window): {n_dead} product(s) flagged.")
    if n_dead > 0:
        exposure = dead_stock.loc[dead_stock["is_dead_stock"], "holding_cost_exposure"].sum()
        print(f"  Total holding cost tied up in dead stock: {exposure:,.2f}")
    dead_path = safe_to_csv(dead_stock, args.dead_stock_out)
    print(f"  Saved: {dead_path}\n")

    # --- 2. Supplier scorecard ---
    scorecard = build_supplier_scorecard(report)
    print(f"Supplier scorecard built for {len(scorecard)} supplier(s).")
    print(scorecard[["rank", "supplier_id", "products_supplied",
                      "avg_lead_time_day", "avg_cost_price", "supplier_score"]]
          .head(10).to_string(index=False))
    supplier_path = safe_to_csv(scorecard, args.supplier_out)
    print(f"  Saved: {supplier_path}\n")

    alt_flags = flag_supplier_alternatives(report, scorecard)
    n_better_available = alt_flags["better_supplier_available"].sum() if not alt_flags.empty else 0
    print(f"  {n_better_available} at-risk product(s) have a better-scoring supplier available elsewhere "
          f"(flagged for manual review, not auto-swapped).\n")

    # --- 3. Budget-constrained reorder plan ---
    plan = build_reorder_plan(report, budget=args.budget)
    print_budget_summary(plan, args.budget)
    plan_path = safe_to_csv(plan, args.reorder_plan_out)
    print(f"Reorder plan saved: {plan_path}")


if __name__ == "__main__":
    main()