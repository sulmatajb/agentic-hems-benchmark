"""
Battery Agent — reports home battery state and recommends charge/discharge/idle.
"""


def get_battery_report(row: dict) -> dict:
    """
    Generate a battery agent report from current household state.

    Args:
        row: Current hour's household DataFrame row (as dict)

    Returns:
        dict with SoC, capacity, usable energy, and charge headroom
    """
    soc = row["home_battery_soc_kwh"]
    capacity = row["home_battery_capacity_kwh"]
    soc_pct = soc / capacity if capacity > 0 else 0.0

    usable = max(0.0, soc - capacity * 0.1)       # 10% min SoC floor
    headroom = max(0.0, capacity * 0.95 - soc)    # 95% max SoC ceiling

    return {
        "battery_soc_kwh": round(float(soc), 3),
        "battery_capacity_kwh": round(float(capacity), 3),
        "battery_soc_pct": round(soc_pct * 100, 1),
        "usable_energy_kwh": round(float(usable), 3),
        "charge_headroom_kwh": round(float(headroom), 3),
        "can_discharge": usable > 0.5,
        "can_charge": headroom > 0.5,
    }


def apply_battery_action(soc: float, capacity: float, action: str, solar_kw: float = 0.0) -> float:
    """
    Update battery SoC based on orchestrator decision.

    action: "charge" | "discharge" | "idle"
    Returns new SoC (kWh), clamped to [10%, 95%] of capacity.
    """
    min_soc = capacity * 0.10
    max_soc = capacity * 0.95
    charge_rate = min(capacity * 0.25, solar_kw) if action == "charge" else capacity * 0.25

    if action == "charge":
        new_soc = min(soc + charge_rate, max_soc)
    elif action == "discharge":
        new_soc = max(soc - capacity * 0.25, min_soc)
    else:
        new_soc = soc

    return round(new_soc, 4)


def format_for_prompt(report: dict) -> str:
    return (
        f"BATTERY AGENT REPORT:\n"
        f"  SoC: {report['battery_soc_kwh']:.2f} kWh "
        f"({report['battery_soc_pct']:.0f}% of {report['battery_capacity_kwh']:.0f} kWh)\n"
        f"  Usable for discharge: {report['usable_energy_kwh']:.2f} kWh\n"
        f"  Headroom to charge: {report['charge_headroom_kwh']:.2f} kWh\n"
        f"  Can discharge: {report['can_discharge']} | Can charge: {report['can_charge']}"
    )
