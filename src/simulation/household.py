"""
Synthetic household load profile generator.
Produces 30-day hourly CSVs for 3 archetypes × 3 seeds.

Output columns per CSV:
    hour (0-719), base_load_kw, solar_gen_kw, ev_plugged_in (bool),
    ev_soc_kwh, home_battery_soc_kwh
"""

import numpy as np
import pandas as pd
from pathlib import Path

HOUSEHOLDS_DIR = Path(__file__).parents[2] / "data" / "households"

ARCHETYPES = {
    "small_suburban": {
        "base_load_avg_kw": 0.5,
        "ev_capacity_kwh": 60.0,
        "ev_plugin_hour": 18,   # 6pm
        "ev_plugout_hour": 7,   # 7am
        "ev_daily_discharge_kwh": 12.0,  # ~48 miles @ 0.25 kWh/mile
        "solar_peak_kw": 5.0,
        "battery_capacity_kwh": 10.0,
        "battery_initial_soc_pct": 0.5,
        "ev_initial_soc_pct": 0.3,
    },
    "large_suburban": {
        "base_load_avg_kw": 1.2,
        "ev_capacity_kwh": 100.0,
        "ev_plugin_hour": 18,
        "ev_plugout_hour": 7,
        "ev_daily_discharge_kwh": 15.0,  # ~60 miles @ 0.25 kWh/mile
        "solar_peak_kw": 10.0,
        "battery_capacity_kwh": 20.0,
        "battery_initial_soc_pct": 0.5,
        "ev_initial_soc_pct": 0.3,
    },
    "apartment": {
        "base_load_avg_kw": 0.3,
        "ev_capacity_kwh": 40.0,
        "ev_plugin_hour": 19,   # 7pm
        "ev_plugout_hour": 8,   # 8am
        "ev_daily_discharge_kwh": 8.0,   # ~32 miles @ 0.25 kWh/mile
        "solar_peak_kw": 0.0,   # no rooftop solar
        "battery_capacity_kwh": 5.0,
        "battery_initial_soc_pct": 0.5,
        "ev_initial_soc_pct": 0.3,
    },
}

SEEDS = [42, 43, 44]
DAYS = 30
HOURS = DAYS * 24


def _solar_profile(peak_kw: float, hour_of_day: int) -> float:
    """Simple bell-curve solar generation for a given hour (0-23)."""
    if peak_kw == 0:
        return 0.0
    # Peak at noon (hour 12), zero before 6am and after 8pm
    if hour_of_day < 6 or hour_of_day > 20:
        return 0.0
    angle = np.pi * (hour_of_day - 6) / 14.0  # 14h daylight window
    return round(float(peak_kw * np.sin(angle)), 4)


def generate_household(archetype: str, seed: int) -> pd.DataFrame:
    """
    Generate a 30-day (720-row) hourly load profile DataFrame.
    """
    cfg = ARCHETYPES[archetype]
    rng = np.random.default_rng(seed)

    rows = []
    ev_soc = cfg["ev_capacity_kwh"] * cfg["ev_initial_soc_pct"]
    battery_soc = cfg["battery_capacity_kwh"] * cfg["battery_initial_soc_pct"]

    for h in range(HOURS):
        hour_of_day = h % 24
        day = h // 24

        # Base load: average ± 30% noise with slight diurnal pattern
        diurnal = 1.0 + 0.3 * np.sin(np.pi * (hour_of_day - 6) / 12)
        noise = rng.normal(1.0, 0.1)
        base_load = max(0.05, cfg["base_load_avg_kw"] * diurnal * noise)

        # Solar
        solar_gen = _solar_profile(cfg["solar_peak_kw"], hour_of_day)
        # Add day-to-day cloud cover variation (seed-consistent)
        cloud = rng.beta(5, 2)  # mostly sunny
        solar_gen = round(solar_gen * cloud, 4)

        # EV plug-in status
        plugin = cfg["ev_plugin_hour"]
        plugout = cfg["ev_plugout_hour"]
        if plugin > plugout:
            ev_plugged = hour_of_day >= plugin or hour_of_day < plugout
        else:
            ev_plugged = plugin <= hour_of_day < plugout

        # Apply daily driving discharge at plugout hour (EV just departed)
        if hour_of_day == plugout and h > 0:
            discharge = cfg["ev_daily_discharge_kwh"]
            ev_soc = max(cfg["ev_capacity_kwh"] * 0.10, ev_soc - discharge)

        rows.append({
            "hour": h,
            "day": day,
            "hour_of_day": hour_of_day,
            "base_load_kw": round(float(base_load), 4),
            "solar_gen_kw": solar_gen,
            "ev_plugged_in": int(ev_plugged),
            "ev_soc_kwh": round(float(ev_soc), 4),
            "ev_capacity_kwh": cfg["ev_capacity_kwh"],
            "ev_daily_discharge_kwh": cfg["ev_daily_discharge_kwh"],
            "home_battery_soc_kwh": round(float(battery_soc), 4),
            "home_battery_capacity_kwh": cfg["battery_capacity_kwh"],
        })

    return pd.DataFrame(rows)


def generate_all() -> None:
    """Generate all 9 CSVs (3 archetypes × 3 seeds)."""
    HOUSEHOLDS_DIR.mkdir(parents=True, exist_ok=True)
    for archetype in ARCHETYPES:
        for seed in SEEDS:
            df = generate_household(archetype, seed)
            fname = HOUSEHOLDS_DIR / f"{archetype}_seed{seed}.csv"
            df.to_csv(fname, index=False)
            print(f"Saved {fname} ({len(df)} rows)")


def load_household(archetype: str, seed: int) -> pd.DataFrame:
    """Load a pre-generated household CSV."""
    path = HOUSEHOLDS_DIR / f"{archetype}_seed{seed}.csv"
    return pd.read_csv(path)


if __name__ == "__main__":
    generate_all()
    print("\nAll household profiles generated.")
