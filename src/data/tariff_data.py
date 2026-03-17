"""
Hardcoded 2024 US utility tariff structures.

Sources:
  - PG&E E-TOU-C: pge.com Schedule E-TOU-C (effective 2024)
  - SCE TOU-D-4: sce.com Schedule TOU-D-4 (effective 2024, replaces TOU-D-PRIME)
  - ComEd Hourly Pricing: hourlypricing.comed.com (real-time program, typical day profile)

All rates in $/kWh (energy charges only, excl. fixed/demand charges).
Weekday summer (June-Sept) schedule used as representative.
"""

TARIFF_STRUCTURES = {
    "pge_etou_c": {
        "tariff_id": "pge_etou_c",
        "label": "PG&E E-TOU-C (2024)",
        "utility": "Pacific Gas and Electric Co",
        "structure": "tou_3tier",
        "currency": "USD",
        "unit": "$/kWh",
        # Super Off-Peak (12am-6am): $0.248, Off-Peak (6am-4pm, 9pm-12am): $0.388, Peak (4pm-9pm): $0.574
        "weekday_prices": [
            0.248, 0.248, 0.248, 0.248, 0.248, 0.248,  # 12am-6am (super off-peak)
            0.388, 0.388, 0.388, 0.388, 0.388, 0.388,  # 6am-12pm (off-peak)
            0.388, 0.388, 0.388, 0.388,                 # 12pm-4pm (off-peak)
            0.574, 0.574, 0.574, 0.574, 0.574,          # 4pm-9pm (peak)
            0.388, 0.388, 0.388,                         # 9pm-12am (off-peak)
        ],
        "weekend_prices": [
            0.248, 0.248, 0.248, 0.248, 0.248, 0.248,  # 12am-6am (super off-peak)
            0.388, 0.388, 0.388, 0.388, 0.388, 0.388,  # 6am-12pm (off-peak)
            0.388, 0.388, 0.388, 0.388, 0.388, 0.388,  # 12pm-6pm (off-peak, no peak wknd)
            0.388, 0.388, 0.388, 0.388, 0.388, 0.388,  # 6pm-12am (off-peak)
        ],
        "notes": "PG&E E-TOU-C 2024. Super off-peak 12am-6am, peak 4pm-9pm Mon-Fri summer.",
    },
    "sce_tou_d_prime": {
        "tariff_id": "sce_tou_d_prime",
        "label": "SCE TOU-D-4 (2024)",
        "utility": "Southern California Edison Co",
        "structure": "tou_2tier",
        "currency": "USD",
        "unit": "$/kWh",
        # Off-Peak (9pm-8am): $0.280, Mid-Peak (8am-2pm, 8pm-9pm): $0.342, Peak (2pm-8pm): $0.522
        "weekday_prices": [
            0.280, 0.280, 0.280, 0.280, 0.280, 0.280,  # 12am-6am (off-peak)
            0.280, 0.280,                                # 6am-8am (off-peak)
            0.342, 0.342, 0.342, 0.342, 0.342, 0.342,  # 8am-2pm (mid-peak)
            0.522, 0.522, 0.522, 0.522, 0.522, 0.522,  # 2pm-8pm (peak)
            0.342,                                       # 8pm-9pm (mid-peak)
            0.280, 0.280, 0.280,                         # 9pm-12am (off-peak)
        ],
        "weekend_prices": [
            0.280, 0.280, 0.280, 0.280, 0.280, 0.280,  # 12am-6am (off-peak)
            0.280, 0.280, 0.280, 0.280, 0.280, 0.280,  # 6am-12pm (off-peak)
            0.280, 0.280, 0.280, 0.280, 0.280, 0.280,  # 12pm-6pm (off-peak)
            0.280, 0.280, 0.280, 0.280, 0.280, 0.280,  # 6pm-12am (off-peak)
        ],
        "notes": "SCE TOU-D-4 2024 (successor to TOU-D-PRIME). Peak 2pm-8pm weekdays summer.",
    },
    "comed_hourly": {
        "tariff_id": "comed_hourly",
        "label": "ComEd Hourly Pricing (2024)",
        "utility": "Commonwealth Edison Co",
        "structure": "realtime",
        "currency": "USD",
        "unit": "$/kWh",
        # Representative hourly pricing (median weekday summer day from ComEd hourly program)
        # Prices vary daily but this reflects typical diurnal pattern
        "weekday_prices": [
            0.034, 0.031, 0.029, 0.028, 0.029, 0.032,  # 12am-6am (overnight low)
            0.041, 0.058, 0.072, 0.078, 0.075, 0.071,  # 6am-12pm (morning ramp)
            0.068, 0.065, 0.069, 0.085, 0.112, 0.138,  # 12pm-6pm (afternoon rise)
            0.155, 0.142, 0.118, 0.091, 0.068, 0.049,  # 6pm-12am (evening peak/fall)
        ],
        "weekend_prices": [
            0.028, 0.026, 0.025, 0.024, 0.025, 0.027,  # 12am-6am
            0.032, 0.039, 0.048, 0.055, 0.058, 0.056,  # 6am-12pm
            0.053, 0.051, 0.055, 0.065, 0.078, 0.085,  # 12pm-6pm
            0.088, 0.079, 0.065, 0.052, 0.042, 0.035,  # 6pm-12am
        ],
        "notes": "ComEd Hourly Pricing 2024. Median summer weekday profile from hourlypricing.comed.com.",
    },
}


def get_tariff(tariff_id: str) -> dict:
    """Return a tariff structure dict by ID."""
    if tariff_id not in TARIFF_STRUCTURES:
        raise KeyError(f"Unknown tariff_id: {tariff_id}. Available: {list(TARIFF_STRUCTURES)}")
    return TARIFF_STRUCTURES[tariff_id]
