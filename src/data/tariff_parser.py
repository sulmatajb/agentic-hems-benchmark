"""
Tariff parser — saves the 2024 utility tariff structures to data/tariffs/ as parsed JSON.

Uses hardcoded 2024 rate structures from tariff_data.py (sourced from utility tariff filings).
OpenEI data was consulted but not used due to outdated rate schedules.
"""

import json
from pathlib import Path
from src.data.tariff_data import TARIFF_STRUCTURES

TARIFFS_DIR = Path(__file__).parents[2] / "data" / "tariffs"


def parse_all() -> dict:
    """Write all 3 tariff structures to data/tariffs/ and return dict keyed by tariff_id."""
    TARIFFS_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for tariff_id, tariff in TARIFF_STRUCTURES.items():
        out_path = TARIFFS_DIR / f"{tariff_id}_parsed.json"
        with open(out_path, "w") as f:
            json.dump(tariff, f, indent=2)
        print(f"Saved {tariff_id} → {out_path}")
        results[tariff_id] = tariff
    return results


def load_parsed_tariff(tariff_id: str) -> dict:
    """Load a tariff from data/tariffs/, writing it first if not present."""
    path = TARIFFS_DIR / f"{tariff_id}_parsed.json"
    if not path.exists():
        parse_all()
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    results = parse_all()
    for tid, t in results.items():
        print(f"\n{tid}: {t['label']}")
        print(f"  Structure: {t['structure']}")
        print(f"  Weekday prices ($/kWh): {t['weekday_prices']}")
        print(f"  Price range: ${min(t['weekday_prices']):.3f} - ${max(t['weekday_prices']):.3f}")
