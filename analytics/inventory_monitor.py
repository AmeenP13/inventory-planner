
"""
Inventory Live Monitor
=======================
Watches a CSV file (one that gets periodically overwritten/exported by
another system) and re-runs the inventory analysis on an interval.

When a product NEWLY crosses into LOW_STOCK or OUT_OF_STOCK status
(i.e. it wasn't in alert state on the previous check), this script:
  - Prints a clear console alert
  - Fires a desktop notification (Windows/Mac/Linux via 'plyer')

Each check also refreshes:
  - <report-out>            (latest full report, overwritten each run)
  - <chart-out>              (latest chart, overwritten each run)
  - inventory_alert_log.csv  (append-only history of every NEW alert ever fired)

This script does NOT touch your source CSV. It only reads it.

Requirements:
    pip install plyer --break-system-packages   (desktop notifications)
    (pandas / numpy / matplotlib already required by inventory_management.py)

Usage:
    python inventory_monitor.py --csv my_data.csv
    python inventory_monitor.py --csv my_data.csv --interval-minutes 60
    python inventory_monitor.py --csv my_data.csv --run-once   (single check, no loop)

Stop with Ctrl+C.
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

import pandas as pd

# Reuse all the core logic from the existing one-shot script.
# inventory_management.py must be in the same folder.
from inventory_management import (
    load_data,
    build_report,
    print_diagnostics,
    print_summary,
    save_chart,
    safe_to_csv,
)

try:
    from plyer import notification
    DESKTOP_NOTIFICATIONS_AVAILABLE = True
except ImportError:
    DESKTOP_NOTIFICATIONS_AVAILABLE = False


ALERT_LOG_PATH = "inventory_alert_log.csv"


def send_desktop_notification(title: str, message: str) -> None:
    """Fire an OS-level desktop notification. Falls back to console-only if unavailable."""
    if DESKTOP_NOTIFICATIONS_AVAILABLE:
        try:
            notification.notify(title=title, message=message, timeout=15)
            return
        except Exception as e:
            print(f"(Desktop notification failed: {e}. Showing console alert instead.)")

    # Fallback: loud console banner
    print("\a")  # terminal bell, if supported
    print("!" * 60)
    print(f"ALERT: {title}")
    print(message)
    print("!" * 60 + "\n")


def append_alert_log(new_alerts: pd.DataFrame, log_path: str) -> None:
    """Append newly-triggered alerts to a persistent history CSV."""
    if new_alerts.empty:
        return
    new_alerts = new_alerts.copy()
    new_alerts.insert(0, "alert_triggered_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    log_file = Path(log_path)
    if log_file.exists():
        new_alerts.to_csv(log_path, mode="a", header=False, index=False)
    else:
        new_alerts.to_csv(log_path, mode="w", header=True, index=False)


def get_file_signature(path: str) -> tuple:
    """Return (mtime, size) for change detection without re-reading the file."""
    p = Path(path)
    stat = p.stat()
    return (stat.st_mtime, stat.st_size)


def run_check(csv_path: str, service_level: float, report_out: str, chart_out: str,
              top_n: int, previous_alert_ids: set) -> set:
    """
    Run one full analysis pass. Returns the updated set of product_ids
    currently in LOW_STOCK or OUT_OF_STOCK status.
    """
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking '{csv_path}'...")

    df = load_data(csv_path)
    report = build_report(df, service_level=service_level)

    print_diagnostics(df, report)
    print_summary(report)

    actual_report_path = safe_to_csv(report, report_out)
    print(f"Report updated: {actual_report_path}")
    save_chart(report, chart_out, top_n=top_n)

    current_alerts = report[report["stock_status"].isin(["LOW_STOCK", "OUT_OF_STOCK"])]
    current_alert_ids = set(current_alerts["product_id"])

    # Only products that are NEW to alert status since the last check
    newly_alerting_ids = current_alert_ids - previous_alert_ids
    newly_alerting = current_alerts[current_alerts["product_id"].isin(newly_alerting_ids)]

    if not newly_alerting.empty:
        append_alert_log(newly_alerting, ALERT_LOG_PATH)

        names = ", ".join(newly_alerting["product_name"].head(8).tolist())
        more = "" if len(newly_alerting) <= 8 else f" (+{len(newly_alerting) - 8} more)"
        message = f"{len(newly_alerting)} product(s) just dropped to low/out of stock: {names}{more}"

        print(f"\n*** NEW ALERTS: {message} ***\n")
        send_desktop_notification("Inventory Alert: Reorder Needed", message)
    else:
        print("No new alerts since last check.")

    # Products that recovered (left alert status) — useful to know, not alerted on
    recovered_ids = previous_alert_ids - current_alert_ids
    if recovered_ids:
        print(f"{len(recovered_ids)} product(s) recovered above reorder point since last check.")

    return current_alert_ids


def main():
    parser = argparse.ArgumentParser(description="Live Inventory Monitor with change-triggered alerts")
    parser.add_argument("--csv", required=True, help="Path to the CSV file to watch")
    parser.add_argument("--service-level", type=float, default=0.95,
                         help="Target service level for safety stock (e.g. 0.90, 0.95, 0.99)")
    parser.add_argument("--report-out", default="low_stock_alert_report.csv",
                         help="Output path for the full CSV report (overwritten each check)")
    parser.add_argument("--chart-out", default="stock_status_chart.png",
                         help="Output path for the chart image (overwritten each check)")
    parser.add_argument("--top-n", type=int, default=25,
                         help="Number of most at-risk products to show in the chart")
    parser.add_argument("--interval-minutes", type=float, default=60,
                         help="How often to re-check the CSV, in minutes (default: 60)")
    parser.add_argument("--run-once", action="store_true",
                         help="Run a single check and exit, instead of looping forever")
    parser.add_argument("--check-mtime-only", action="store_true",
                         help="Only re-analyze when the CSV's modified time/size has changed "
                              "since the last check, instead of every interval regardless")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        sys.exit(f"ERROR: file not found: {args.csv}")

    if not DESKTOP_NOTIFICATIONS_AVAILABLE:
        print("NOTE: 'plyer' is not installed, so desktop notifications are disabled.")
        print("      Install it with: pip install plyer --break-system-packages")
        print("      Falling back to console alerts only.\n")

    previous_alert_ids: set = set()
    last_signature = None

    print(f"Starting inventory monitor on '{args.csv}'")
    print(f"Check interval: every {args.interval_minutes} minute(s)")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            signature = get_file_signature(args.csv)
            should_check = True

            if args.check_mtime_only and signature == last_signature:
                should_check = False
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"No change detected in '{args.csv}'. Skipping this cycle.")

            if should_check:
                previous_alert_ids = run_check(
                    csv_path=args.csv,
                    service_level=args.service_level,
                    report_out=args.report_out,
                    chart_out=args.chart_out,
                    top_n=args.top_n,
                    previous_alert_ids=previous_alert_ids,
                )
                last_signature = signature

            if args.run_once:
                break

            time.sleep(args.interval_minutes * 60)

    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")


if __name__ == "__main__":
    main()