"""
Solar Agent — reports current solar generation and 6-hour forecast.
"""


def get_solar_report(row: dict, horizon_rows: list) -> dict:
    """
    Generate a solar agent report.

    Args:
        row: Current hour's household DataFrame row (as dict)
        horizon_rows: Next 6 hours' rows (list of dicts)

    Returns:
        dict with current generation and forecast
    """
    current_gen = row["solar_gen_kw"]
    forecast_6h = [r["solar_gen_kw"] for r in horizon_rows[:6]]

    return {
        "current_solar_gen_kw": round(float(current_gen), 4),
        "forecast_6h_kw": [round(float(g), 4) for g in forecast_6h],
        "has_solar": row.get("solar_gen_kw", 0) > 0 or any(g > 0 for g in forecast_6h),
        "peak_solar_next_6h": round(max([current_gen] + forecast_6h), 4),
    }


def format_for_prompt(report: dict) -> str:
    return (
        f"SOLAR AGENT REPORT:\n"
        f"  Current generation: {report['current_solar_gen_kw']:.3f} kW\n"
        f"  Next 6h forecast: {[f'{g:.2f}kW' for g in report['forecast_6h_kw']]}\n"
        f"  Has solar: {report['has_solar']}"
    )
