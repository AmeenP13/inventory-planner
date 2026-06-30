"""
Inventory Management — Full Pipeline
======================================
Runs every stage of the project as ONE continuous script, in order:

  STEP 1 — Load & validate the CSV
  STEP 2 — Build the base report (avg daily sales, ROP, stock status)
  STEP 3 — Detect dead stock (zero sales in the last N days)
  STEP 4 — Build the supplier scorecard & flag better alternatives
  STEP 5 — Build the budget-constrained reorder plan
  STEP 6 — Save every output file + print one consolidated summary

This file does not replace inventory_management.py, inventory_advance.py,
or inventory_monitor.py — those still work standalone. This script just
imports their functions and chains them together so you can run the
whole project in a single command instead of three.

Requires inventory_management.py and inventory_advance.py to be in the
same folder (this script imports functions from both).

Usage:
    python inventory_pipeline.py --csv my_data.csv --budget 50000
    python inventory_pipeline.py --csv my_data.csv --budget 50000 --service-level 0.95 --dead-stock-days 90

Outputs (all written to the current folder unless paths are overridden):
    - low_stock_alert_report.csv   (Step 2)
    - stock_status_chart.png       (Step 2)
    - dead_stock_report.csv        (Step 3)
    - supplier_scorecard.csv       (Step 4)
    - reorder_plan.csv             (Step 5)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# --- STEP 1 & 2 building blocks (from the base script) ---
from inventory_management import (
    load_data,
    build_report,
    print_diagnostics,
    print_summary,
    save_chart,
    safe_to_csv,
)

# --- STEP 3, 4, 5 building blocks (from the advanced script) ---
from inventory_advance import (
    DEAD_STOCK_WINDOW_DAYS,
    detect_dead_stock,
    build_supplier_scorecard,
    flag_supplier_alternatives,
    build_reorder_plan,
    print_budget_summary,
)


def banner(step_number: int, title: str) -> None:
    print("\n" + "#" * 70)
    print(f"# STEP {step_number}: {title}")
    print("#" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Full inventory pipeline: report, dead stock, suppliers, and budget plan in one run"
    )
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument("--budget", type=float, required=True,
                         help="Available procurement budget for the reorder plan")
    parser.add_argument("--service-level", type=float, default=0.95,
                         help="Target service level for safety stock (e.g. 0.90, 0.95, 0.99)")
    parser.add_argument("--dead-stock-days", type=int, default=DEAD_STOCK_WINDOW_DAYS,
                         help=f"Days with zero sales to flag as dead stock (default: {DEAD_STOCK_WINDOW_DAYS})")
    parser.add_argument("--top-n", type=int, default=25,
                         help="Number of most at-risk products to show in the chart")
    parser.add_argument("--report-out", default="low_stock_alert_report.csv")
    parser.add_argument("--chart-out", default="stock_status_chart.png")
    parser.add_argument("--dead-stock-out", default="dead_stock_report.csv")
    parser.add_argument("--supplier-out", default="supplier_scorecard.csv")
    parser.add_argument("--reorder-plan-out", default="reorder_plan.csv")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    banner(1, "LOAD & VALIDATE DATA")
    # ------------------------------------------------------------------
    print(f"Loading data from: {args.csv}")
    df = load_data(args.csv)
    print(f"Loaded {len(df)} rows across {df['product_id'].nunique()} products.")

    # ------------------------------------------------------------------
    banner(2, "BASE REPORT — AVG DAILY SALES, REORDER POINT, STOCK STATUS")
    # ------------------------------------------------------------------
    report = build_report(df, service_level=args.service_level)
    print_diagnostics(df, report)
    print_summary(report)

    report_path = safe_to_csv(report, args.report_out)
    print(f"Report saved: {report_path}")
    save_chart(report, args.chart_out, top_n=args.top_n)

    # ------------------------------------------------------------------
    banner(3, f"DEAD STOCK DETECTION ({args.dead_stock_days}-DAY WINDOW)")
    # ------------------------------------------------------------------
    dead_stock = detect_dead_stock(df, report, window_days=args.dead_stock_days)
    n_dead = dead_stock["is_dead_stock"].sum()
    print(f"{n_dead} product(s) flagged as dead stock.")
    if n_dead > 0:
        exposure = dead_stock.loc[dead_stock["is_dead_stock"], "holding_cost_exposure"].sum()
        print(f"Total holding cost tied up in dead stock: {exposure:,.2f}")
        print(dead_stock[dead_stock["is_dead_stock"]].head(10)[
            ["product_id", "product_name", "units_sold_last_90d", "holding_cost_exposure"]
        ].to_string(index=False))

    dead_stock_path = safe_to_csv(dead_stock, args.dead_stock_out)
    print(f"\nDead stock report saved: {dead_stock_path}")

    # ------------------------------------------------------------------
    banner(4, "SUPPLIER SCORECARD & ALTERNATIVES")
    # ------------------------------------------------------------------
    scorecard = build_supplier_scorecard(report)
    print(f"Scored {len(scorecard)} supplier(s) on lead time + cost:")
    print(scorecard[["rank", "supplier_id", "products_supplied",
                      "avg_lead_time_day", "avg_cost_price", "supplier_score"]]
          .head(10).to_string(index=False))

    supplier_path = safe_to_csv(scorecard, args.supplier_out)
    print(f"\nSupplier scorecard saved: {supplier_path}")

    alt_flags = flag_supplier_alternatives(report, scorecard)
    n_better_available = alt_flags["better_supplier_available"].sum() if not alt_flags.empty else 0
    print(f"{n_better_available} at-risk product(s) have a better-scoring supplier available "
          f"elsewhere (flagged for manual review, not auto-swapped).")

    # ------------------------------------------------------------------
    banner(5, "BUDGET-CONSTRAINED REORDER PLAN")
    # ------------------------------------------------------------------
    plan = build_reorder_plan(report, budget=args.budget)
    print_budget_summary(plan, args.budget)

    plan_path = safe_to_csv(plan, args.reorder_plan_out)
    print(f"Reorder plan saved: {plan_path}")

    # ------------------------------------------------------------------
    banner(6, "PIPELINE COMPLETE — FILES GENERATED")
    # ------------------------------------------------------------------
    outputs = [
        ("Stock report (CSV)", report_path),
        ("Stock risk chart (PNG)", args.chart_out),
        ("Dead stock report (CSV)", dead_stock_path),
        ("Supplier scorecard (CSV)", supplier_path),
        ("Reorder plan (CSV)", plan_path),
    ]
    for label, path in outputs:
        exists = "OK" if Path(path).exists() else "MISSING"
        print(f"  [{exists}] {label:28s} -> {path}")
    print()


if __name__ == "__main__":
    main()