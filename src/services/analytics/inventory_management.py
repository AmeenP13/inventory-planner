"""
Inventory Management System
============================
Reads a product sales CSV, computes average daily sales per product,
estimates how many days the current stock will last, calculates a
Reorder Point (ROP) with safety stock, and raises low-stock alerts
when current stock <= ROP.

Expected CSV columns (matches the user's dataset):
    product_id, product_name, current_stock, cost_price, base_price,
    date, quantity_sold, customer_rating, supplier_id,
    avg_lead_time_day, expiry_date

Usage:
    python inventory_management.py
    python inventory_management.py --csv my_data.csv --service-level 0.95

Outputs:
    - Console summary + alert table
    - low_stock_alert_report.csv   (full per-product report)
    - stock_status_chart.png       (bar chart: days of stock left, alert highlighted)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib   
matplotlib.use("Agg")  # safe for headless / script runs
import matplotlib.pyplot as plt


REQUIRED_COLUMNS = [
    "product_id", "product_name", "current_stock", "cost_price",
    "base_price", "date", "quantity_sold", "customer_rating",
    "supplier_id", "avg_lead_time_day", "expiry_date",
]

# Z-scores for common service levels, used to size safety stock.
# safety_stock = Z * std_dev_of_daily_sales * sqrt(lead_time)
Z_SCORE_TABLE = {
    0.90: 1.28,
    0.95: 1.65,
    0.975: 1.96,
    0.99: 2.33,
}


def load_data(csv_path: str) -> pd.DataFrame:
    """Load and validate the CSV."""
    path = Path(csv_path)
    if not path.exists():
        sys.exit(f"ERROR: file not found: {csv_path}")

    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: CSV is missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")

    # Basic cleaning
    df["quantity_sold"] = pd.to_numeric(df["quantity_sold"], errors="coerce").fillna(0)
    df = df.dropna(subset=["product_id", "date"])

    return df


def get_zscore(service_level: float) -> float:
    """Return nearest Z-score for a given service level (0-1)."""
    closest = min(Z_SCORE_TABLE.keys(), key=lambda k: abs(k - service_level))
    return Z_SCORE_TABLE[closest]


def build_report(df: pd.DataFrame, service_level: float = 0.95) -> pd.DataFrame:
    """
    Aggregate historical sales per product and compute:
      - avg_daily_sales
      - std_daily_sales
      - days_of_stock_left
      - safety_stock
      - reorder_point (ROP)
      - stock_status (SAFE / LOW_STOCK / OUT_OF_STOCK)
      - days_to_expiry (for the nearest upcoming expiry on record)
    """
    z = get_zscore(service_level)

    # One row per product for static fields (latest record wins)
    latest = (
        df.sort_values("date")
        .groupby("product_id")
        .tail(1)[[
            "product_id", "product_name", "current_stock", "cost_price",
            "base_price", "customer_rating", "supplier_id", "avg_lead_time_day",
        ]]
        .reset_index(drop=True)
    )

    # Sales stats per product across all historical rows
    sales_stats = (
        df.groupby("product_id")["quantity_sold"]
        .agg(avg_daily_sales="mean", std_daily_sales="std", total_days="count")
        .reset_index()
    )
    sales_stats["std_daily_sales"] = sales_stats["std_daily_sales"].fillna(0)

    # Nearest upcoming expiry per product (from today)
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

    # Avoid divide-by-zero: treat 0 avg sales as a tiny epsilon for days-left calc
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
        report["days_to_expiry"] = (
            report["nearest_expiry_date"] - today
        ).dt.days

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


def print_diagnostics(df: pd.DataFrame, report: pd.DataFrame) -> None:
    """Print sanity-check stats to help catch data issues early."""
    print("-" * 60)
    print("DIAGNOSTICS")
    print("-" * 60)
    print(f"Rows in raw data            : {len(df)}")
    print(f"Unique products             : {df['product_id'].nunique()}")
    print(f"quantity_sold  min/mean/max : "
          f"{df['quantity_sold'].min():.1f} / {df['quantity_sold'].mean():.1f} / {df['quantity_sold'].max():.1f}")
    zero_stock = (report["current_stock"] <= 0).sum()
    zero_sales = (report["avg_daily_sales"] <= 0).sum()
    print(f"Products with current_stock <= 0   : {zero_stock}")
    print(f"Products with avg_daily_sales <= 0 : {zero_sales}")
    if zero_stock > 0:
        print("  -> These will show as OUT_OF_STOCK with 0 days of stock left. That's expected.")
    if zero_sales > 0:
        print("  -> These have no recorded sales history; days_of_stock_left will show as infinite (no chart bar).")
    print("-" * 60 + "\n")


def print_summary(report: pd.DataFrame) -> None:
    total = len(report)
    low = (report["stock_status"] == "LOW_STOCK").sum()
    out = (report["stock_status"] == "OUT_OF_STOCK").sum()
    safe = (report["stock_status"] == "SAFE").sum()

    print("=" * 60)
    print("INVENTORY HEALTH SUMMARY")
    print("=" * 60)
    print(f"Total products analyzed : {total}")
    print(f"  SAFE                  : {safe}")
    print(f"  LOW_STOCK (reorder!)  : {low}")
    print(f"  OUT_OF_STOCK          : {out}")
    print("=" * 60)

    alerts = report[report["stock_status"].isin(["LOW_STOCK", "OUT_OF_STOCK"])]
    if alerts.empty:
        print("\nNo low-stock alerts. All products are within safe levels.\n")
    else:
        print(f"\n LOW-STOCK / REORDER ALERTS ({len(alerts)} products) ")
        display_cols = [
            "product_id", "product_name", "supplier_id", "current_stock",
            "reorder_point", "days_of_stock_left", "stock_status",
        ]
        print(alerts[display_cols].to_string(index=False))
        print()


def save_chart(report: pd.DataFrame, out_path: str, top_n: int = 25) -> None:
    """Bar chart of days-of-stock-left for the most at-risk products, color-coded by status."""
    plot_df = report.replace([np.inf], np.nan).dropna(subset=["days_of_stock_left"])
    plot_df = plot_df.sort_values("days_of_stock_left").head(top_n)

    if plot_df.empty:
        print("No finite stock-days data available to chart; skipping chart.")
        return

    color_map = {"OUT_OF_STOCK": "#b91c1c", "LOW_STOCK": "#f59e0b", "SAFE": "#16a34a"}
    colors = plot_df["stock_status"].map(color_map).fillna("#6b7280")

    # Give zero-value bars a tiny visible sliver so they don't render as invisible lines
    max_val = plot_df["days_of_stock_left"].max()
    min_visible = max(max_val * 0.01, 0.15)
    bar_widths = plot_df["days_of_stock_left"].clip(lower=min_visible)

    fig, ax = plt.subplots(figsize=(11, max(5, 0.32 * len(plot_df))))
    bars = ax.barh(plot_df["product_name"], bar_widths, color=colors)

    ax.invert_yaxis()
    ax.set_xlabel("Estimated Days of Stock Remaining")
    ax.set_title(f"Stock Risk Overview — {len(plot_df)} Most At-Risk Products")
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    label_offset = max(max_val, 1) * 0.01
    for bar, val in zip(bars, plot_df["days_of_stock_left"]):
        ax.text(bar.get_width() + label_offset, bar.get_y() + bar.get_height() / 2,
                 f"{int(val)}d", va="center", fontsize=8)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=c) for c in color_map.values()
    ]
    ax.legend(legend_handles, color_map.keys(), loc="upper left",
              bbox_to_anchor=(1.01, 1), title="Status", borderaxespad=0)

    plt.tight_layout()
    try:
        plt.savefig(out_path, dpi=150)
        saved_path = out_path
    except PermissionError:
        stem = Path(out_path).stem
        suffix = Path(out_path).suffix or ".png"
        saved_path = f"{stem}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        print(f"WARNING: '{out_path}' is locked or not writable. Saving to '{saved_path}' instead.")
        plt.savefig(saved_path, dpi=150)
    plt.close(fig)
    print(f"Chart saved to: {saved_path}")


def safe_to_csv(df: pd.DataFrame, path: str) -> str:
    """
    Write a DataFrame to CSV, falling back to a timestamped filename if the
    target path is locked (e.g. open in Excel) or otherwise not writable.
    Returns the path actually written to.
    """
    try:
        df.to_csv(path, index=False)
        return path
    except PermissionError:
        stem = Path(path).stem
        suffix = Path(path).suffix or ".csv"
        fallback = f"{stem}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        print(f"WARNING: '{path}' is locked or not writable "
              f"(is it open in Excel?). Saving to '{fallback}' instead.")
        df.to_csv(fallback, index=False)
        return fallback


def main():
    parser = argparse.ArgumentParser(description="Inventory Management & Reorder Alert System")
    parser.add_argument("--csv", default="final_inventory_dataset_real_products.csv", help="Path to input CSV file")
    parser.add_argument("--service-level", type=float, default=0.95,
                         help="Target service level for safety stock (e.g. 0.90, 0.95, 0.99)")
    parser.add_argument("--report-out", default="low_stock_alert_report.csv",
                         help="Output path for the full CSV report")
    parser.add_argument("--chart-out", default="stock_status_chart.png",
                         help="Output path for the chart image")
    parser.add_argument("--top-n", type=int, default=25,
                         help="Number of most at-risk products to show in the chart")
    args = parser.parse_args()

    print(f"Loading data from: {args.csv}")
    df = load_data(args.csv)
    print(f"Loaded {len(df)} rows across {df['product_id'].nunique()} products.\n")

    report = build_report(df, service_level=args.service_level)

    print_diagnostics(df, report)
    print_summary(report)

    actual_report_path = safe_to_csv(report, args.report_out)
    print(f"Full report saved to: {actual_report_path}")

    save_chart(report, args.chart_out, top_n=args.top_n)


if __name__ == "__main__":
    main()