from src.services.agentic_ai.state import State

from datetime import datetime


def demand_agent(state: State):
    inventory_history = state.get("all_dates_inventory") or []
    if not inventory_history:
        return state

    total_sold = sum(int(record.get("quantity_sold", 0))
                     for record in inventory_history)
    period_days = _calculate_history_days(inventory_history)
    average_daily_sales = round(
        total_sold / period_days,
        2) if period_days else 0.0
    estimated_demand = round(
        total_sold / len(inventory_history),
        2) if inventory_history else 0.0

    demand_summary = {
        "average_daily_sales": average_daily_sales,
        "estimated_demand": estimated_demand,
        "total_sold": total_sold,
        "history_length": len(inventory_history),
        "period_days": period_days,
    }

    state["demand"] = demand_summary
    _sync_history_metrics(inventory_history, demand_summary)
    _update_next_day_inventory(state, demand_summary)

    return state


def _calculate_history_days(history: list[dict]) -> int:
    dates = [
        datetime.strptime(record["date"], "%Y-%m-%d")
        for record in history
        if record.get("date")
    ]
    if not dates:
        return 0

    sorted_dates = sorted(dates)
    total_days = (sorted_dates[-1] - sorted_dates[0]).days + 1
    return max(total_days, 1)


def _sync_history_metrics(history: list[dict], demand_summary: dict) -> None:
    for record in history:
        record["average_daily_sales"] = demand_summary["average_daily_sales"]
        record["estimated_demand"] = demand_summary["estimated_demand"]


def _update_next_day_inventory(state: State, demand_summary: dict) -> None:
    next_day = state.get("next_day_inventory")
    if not isinstance(next_day, dict):
        return

    next_day["average_daily_sales"] = demand_summary["average_daily_sales"]
    next_day["estimated_demand"] = demand_summary["estimated_demand"]
    next_day["forecasted_stock"] = max(0, int(next_day.get(
        "current_stock", 0) - round(demand_summary["average_daily_sales"])))
