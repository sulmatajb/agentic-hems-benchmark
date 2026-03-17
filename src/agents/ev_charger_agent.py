"""
EV Charger Agent — reports EV state, charging constraints, and departure deadline.
"""


# Assume EV must reach 80% SoC before departure
TARGET_SOC_PCT = 0.80


def get_ev_report(row: dict, hours_until_departure: int) -> dict:
    """
    Generate an EV charger agent report.

    Args:
        row: Current hour's household DataFrame row (as dict)
        hours_until_departure: Hours until EV must be unplugged

    Returns:
        dict with EV SoC, charging urgency, and energy needed
    """
    soc = row["ev_soc_kwh"]
    capacity = row["ev_capacity_kwh"]
    plugged_in = bool(row["ev_plugged_in"])
    soc_pct = soc / capacity if capacity > 0 else 0.0

    target_kwh = capacity * TARGET_SOC_PCT
    energy_needed = max(0.0, target_kwh - soc)

    # Max charge rate: 7.2 kW (typical L2 home charger)
    max_charge_rate_kw = 7.2
    hours_needed = energy_needed / max_charge_rate_kw if max_charge_rate_kw > 0 else 0

    # Urgency: if we need more charging time than we have hours left
    urgent = plugged_in and hours_until_departure > 0 and hours_needed >= hours_until_departure * 0.8

    return {
        "ev_soc_kwh": round(float(soc), 3),
        "ev_capacity_kwh": round(float(capacity), 3),
        "ev_soc_pct": round(soc_pct * 100, 1),
        "ev_plugged_in": plugged_in,
        "energy_needed_kwh": round(float(energy_needed), 3),
        "hours_until_departure": hours_until_departure,
        "max_charge_rate_kw": max_charge_rate_kw,
        "is_urgent": urgent,
        "target_soc_pct": TARGET_SOC_PCT * 100,
    }


def apply_ev_charge(soc: float, capacity: float, charge_rate_pct: float) -> float:
    """
    Update EV SoC based on charging decision.

    charge_rate_pct: 0-100 (% of 7.2 kW max rate)
    Returns new SoC (kWh), clamped at capacity.
    """
    max_rate_kw = 7.2
    charged_kwh = max_rate_kw * (charge_rate_pct / 100.0)
    new_soc = min(soc + charged_kwh, capacity)
    return round(new_soc, 4)


def format_for_prompt(report: dict) -> str:
    urgency_str = " [URGENT - must charge soon]" if report["is_urgent"] else ""
    plugged_str = "plugged in" if report["ev_plugged_in"] else "NOT plugged in"
    return (
        f"EV CHARGER AGENT REPORT:\n"
        f"  Status: {plugged_str}{urgency_str}\n"
        f"  SoC: {report['ev_soc_kwh']:.1f} kWh "
        f"({report['ev_soc_pct']:.0f}% of {report['ev_capacity_kwh']:.0f} kWh)\n"
        f"  Energy needed to reach {report['target_soc_pct']:.0f}%: {report['energy_needed_kwh']:.1f} kWh\n"
        f"  Hours until departure: {report['hours_until_departure']}\n"
        f"  Max charge rate: {report['max_charge_rate_kw']} kW"
    )
