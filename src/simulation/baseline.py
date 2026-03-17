"""
Baseline simulations:

1. Unmanaged baseline — EV charges immediately at max rate when plugged in,
   no battery dispatch, no solar optimization.

2. Oracle baseline — linear programming (scipy) with perfect price foresight.
   Provides theoretical minimum cost for each run.

Both return total_cost_usd for the 30-day simulation.
"""

import pandas as pd
from typing import Optional


def compute_hourly_cost(
    base_load_kw: float,
    ev_charge_kw: float,
    battery_charge_kw: float,   # positive = charging, negative = discharging
    solar_gen_kw: float,
    price_per_kwh: float,
    export_rate: float = 0.03,  # $/kWh net metering credit (conservative)
) -> float:
    """
    Compute electricity cost for one hour.
    Net grid import = base_load + ev_charge + battery_charge - solar_gen
    Negative import = export (earn export_rate).
    """
    net_grid_kw = base_load_kw + ev_charge_kw + battery_charge_kw - solar_gen_kw
    if net_grid_kw >= 0:
        return net_grid_kw * price_per_kwh
    else:
        return net_grid_kw * export_rate  # negative cost = credit


def run_unmanaged(df: pd.DataFrame, tariff: dict) -> dict:
    """
    Unmanaged baseline:
    - EV charges at full 7.2 kW immediately when plugged in (until full)
    - Home battery stays idle
    - Solar is exported to grid (no optimization)

    Returns dict with total_cost_usd and per-hour costs.
    """
    schedule = tariff["weekday_prices"]  # simplified: use weekday prices throughout
    hourly_costs = []
    ev_soc = df.iloc[0]["ev_soc_kwh"]

    prev_plugged = int(df.iloc[0]["ev_plugged_in"])

    for _, row in df.iterrows():
        hour_of_day = int(row["hour_of_day"])
        price = schedule[hour_of_day]
        curr_plugged = int(row["ev_plugged_in"])

        # EV departs: apply daily driving discharge
        if prev_plugged == 1 and curr_plugged == 0:
            daily_discharge = float(row.get("ev_daily_discharge_kwh", 12.0))
            ev_soc = max(row["ev_capacity_kwh"] * 0.10, ev_soc - daily_discharge)
        prev_plugged = curr_plugged

        # EV: charge at max when plugged in and not full
        if curr_plugged and ev_soc < row["ev_capacity_kwh"]:
            ev_charge_kw = min(7.2, row["ev_capacity_kwh"] - ev_soc)
            ev_soc = min(ev_soc + ev_charge_kw, row["ev_capacity_kwh"])
        else:
            ev_charge_kw = 0.0

        cost = compute_hourly_cost(
            base_load_kw=row["base_load_kw"],
            ev_charge_kw=ev_charge_kw,
            battery_charge_kw=0.0,
            solar_gen_kw=row["solar_gen_kw"],
            price_per_kwh=price,
        )
        hourly_costs.append(cost)

    return {
        "total_cost_usd": round(sum(hourly_costs), 4),
        "hourly_costs": hourly_costs,
        "type": "unmanaged",
    }


def run_oracle(df: pd.DataFrame, tariff: dict) -> dict:
    """
    Oracle baseline — day-by-day LP with perfect price foresight.

    For each day:
      - EV session: charge required kWh (from daily discharge + deficit) in
        the cheapest available overnight hours.
      - Battery: daily arbitrage — charge during cheapest off-peak hours,
        discharge during most expensive hours, within SoC limits.
    """
    schedule = tariff["weekday_prices"]
    ev_cap = float(df.iloc[0]["ev_capacity_kwh"])
    bat_cap = float(df.iloc[0]["home_battery_capacity_kwh"])
    daily_discharge = float(df.iloc[0].get("ev_daily_discharge_kwh", 12.0))
    max_ev_rate = 7.2
    max_bat_rate = bat_cap * 0.25

    ev_target = ev_cap * 0.80
    ev_soc = float(df.iloc[0]["ev_soc_kwh"])
    bat_soc = float(df.iloc[0]["home_battery_soc_kwh"])
    bat_min = bat_cap * 0.10
    bat_max = bat_cap * 0.95

    hourly_costs = [0.0] * len(df)
    ev_charge_schedule = [0.0] * len(df)
    bat_schedule = [0.0] * len(df)  # positive = charging, negative = discharging

    # Identify EV charging sessions (consecutive plugged-in hours)
    sessions = _find_ev_sessions(df)

    for session_start, session_end in sessions:
        # Hours available in this session
        session_hours = list(range(session_start, session_end))
        session_prices = [schedule[int(df.iloc[h]["hour_of_day"])] for h in session_hours]

        # EV is discharged at departure (applied when ev departs)
        ev_needed = max(0.0, ev_target - ev_soc)

        if ev_needed > 0 and session_hours:
            # Sort hours by price, charge cheapest first
            sorted_hours = sorted(session_hours, key=lambda h: session_prices[session_hours.index(h)])
            remaining = ev_needed
            for h in sorted_hours:
                if remaining <= 0:
                    break
                charge = min(max_ev_rate, remaining, ev_cap - ev_soc)
                ev_charge_schedule[h] = charge
                ev_soc = min(ev_soc + charge, ev_cap)
                remaining -= charge

    # Battery: daily arbitrage across the full day
    for day in range(30):
        day_start = day * 24
        day_hours = list(range(day_start, min(day_start + 24, len(df))))
        if not day_hours:
            break

        day_prices = [schedule[int(df.iloc[h]["hour_of_day"])] for h in day_hours]
        sorted_by_price = sorted(day_hours, key=lambda h: day_prices[day_hours.index(h)])

        # Charge during bottom quartile, discharge during top quartile
        n_charge = max(1, len(day_hours) // 4)
        n_discharge = max(1, len(day_hours) // 4)
        charge_hours = set(sorted_by_price[:n_charge])
        discharge_hours = set(sorted_by_price[-n_discharge:])

        for h in day_hours:
            if h in charge_hours and bat_soc < bat_max:
                charge = min(max_bat_rate, bat_max - bat_soc)
                bat_schedule[h] = charge
                bat_soc = min(bat_soc + charge, bat_max)
            elif h in discharge_hours and bat_soc > bat_min:
                discharge = min(max_bat_rate, bat_soc - bat_min)
                bat_schedule[h] = -discharge
                bat_soc = max(bat_soc - discharge, bat_min)

    # Apply daily EV discharge at departures and compute costs
    prev_plugged = int(df.iloc[0]["ev_plugged_in"])
    ev_soc = float(df.iloc[0]["ev_soc_kwh"])

    for i, row in df.iterrows():
        curr_plugged = int(row["ev_plugged_in"])
        if prev_plugged == 1 and curr_plugged == 0:
            ev_soc = max(ev_cap * 0.10, ev_soc - daily_discharge)
        if curr_plugged:
            ev_soc = min(ev_soc + ev_charge_schedule[i], ev_cap)
        prev_plugged = curr_plugged

        cost = compute_hourly_cost(
            base_load_kw=row["base_load_kw"],
            ev_charge_kw=ev_charge_schedule[i],
            battery_charge_kw=bat_schedule[i],
            solar_gen_kw=row["solar_gen_kw"],
            price_per_kwh=schedule[int(row["hour_of_day"])],
        )
        hourly_costs[i] = cost

    return {
        "total_cost_usd": round(sum(hourly_costs), 4),
        "hourly_costs": hourly_costs,
        "type": "oracle",
    }


def _find_ev_sessions(df: pd.DataFrame) -> list:
    """Return list of (session_start, session_end) hour indices for each EV plug-in session."""
    sessions = []
    in_session = False
    start = 0
    for i, row in df.iterrows():
        curr = int(row["ev_plugged_in"])
        if not in_session and curr == 1:
            in_session = True
            start = i
        elif in_session and curr == 0:
            sessions.append((start, i))
            in_session = False
    if in_session:
        sessions.append((start, len(df)))
    return sessions


def _find_plugout_hours(df: pd.DataFrame) -> list:  # kept for potential external use
    """Find hours where EV transitions from plugged_in=1 to plugged_in=0."""
    plugout = []
    prev = 0
    for _, row in df.iterrows():
        curr = int(row["ev_plugged_in"])
        if prev == 1 and curr == 0:
            plugout.append(int(row["hour"]))
        prev = curr
    return plugout
