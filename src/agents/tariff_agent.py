"""
Tariff Agent — reports current and upcoming electricity prices from a parsed tariff structure.
Returns a structured summary used by the Orchestrator.
"""

from datetime import datetime
from typing import Optional


def get_tariff_report(tariff: dict, hour_of_day: int, day_of_week: int = 0) -> dict:
    """
    Generate a tariff report for the current hour and the next 6 hours.

    Args:
        tariff: Parsed tariff dict (from tariff_parser.load_parsed_tariff)
        hour_of_day: Current hour (0-23)
        day_of_week: 0=Monday … 6=Sunday

    Returns:
        dict with current_price, next_6h_prices, peak_hours, off_peak_hours, currency
    """
    is_weekend = day_of_week >= 5
    schedule = tariff["weekend_prices"] if is_weekend else tariff["weekday_prices"]

    current_price = schedule[hour_of_day]

    # Next 6 hours (wrapping around midnight)
    next_6h = [schedule[(hour_of_day + i) % 24] for i in range(1, 7)]

    # Identify peak / off-peak windows from the full day schedule
    avg_price = sum(schedule) / 24
    peak_hours = [h for h, p in enumerate(schedule) if p > avg_price * 1.1]
    off_peak_hours = [h for h, p in enumerate(schedule) if p < avg_price * 0.9]

    return {
        "current_hour": hour_of_day,
        "current_price_per_kwh": round(current_price, 5),
        "next_6h_prices": [round(p, 5) for p in next_6h],
        "is_peak_hour": hour_of_day in peak_hours,
        "is_off_peak_hour": hour_of_day in off_peak_hours,
        "peak_hours_today": peak_hours,
        "off_peak_hours_today": off_peak_hours,
        "day_min_price": round(min(schedule), 5),
        "day_max_price": round(max(schedule), 5),
        "currency": tariff["currency"],
        "unit": tariff["unit"],
        "tariff_id": tariff["tariff_id"],
    }


def format_for_prompt(report: dict) -> str:
    """Format tariff report as a concise text block for the orchestrator prompt."""
    return (
        f"TARIFF AGENT REPORT:\n"
        f"  Current price: ${report['current_price_per_kwh']:.4f}/kWh "
        f"({'PEAK' if report['is_peak_hour'] else 'OFF-PEAK' if report['is_off_peak_hour'] else 'MID'})\n"
        f"  Next 6h prices: {[f'${p:.4f}' for p in report['next_6h_prices']]}\n"
        f"  Today range: ${report['day_min_price']:.4f} - ${report['day_max_price']:.4f}/kWh\n"
        f"  Off-peak hours: {report['off_peak_hours_today']}\n"
        f"  Peak hours: {report['peak_hours_today']}"
    )
