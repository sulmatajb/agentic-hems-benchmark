"""
OpenEI API client — fetches real US utility tariff structures.
Saves raw JSON to data/tariffs/ for reproducibility.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TARIFFS_DIR = Path(__file__).parents[2] / "data" / "tariffs"
OPENEI_BASE = "https://api.openei.org/utility_rates"

# Target tariffs: (label, search parameters)
TARGET_TARIFFS = [
    {
        "id": "pge_etou_c",
        "label": "PG&E E-TOU-C",
        "utility": "Pacific Gas and Electric Co",
        "name_contains": "E-TOU-C",
    },
    {
        "id": "sce_tou_d_prime",
        "label": "SCE TOU-D-PRIME",
        "utility": "Southern California Edison Co",
        "name_contains": "TOU-D-PRIME",
    },
    {
        "id": "comed_hourly",
        "label": "ComEd Hourly Pricing",
        "utility": "Commonwealth Edison Co",
        "name_contains": "Hourly",
    },
]


def fetch_tariff(tariff_cfg: dict, api_key: str) -> dict:
    """Fetch a tariff from OpenEI by utility name and rate name pattern."""
    params = {
        "version": 8,
        "format": "json",
        "api_key": api_key,
        "approved": "true",
        "residential": "true",
        "limit": 25,
        "sector": "Residential",
        "ratesforutility": tariff_cfg["utility"],
    }

    resp = requests.get(OPENEI_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    name_filter = tariff_cfg["name_contains"].lower()
    matches = [r for r in items if name_filter in r.get("name", "").lower()]

    if not matches:
        print(f"  [WARN] No exact match for '{tariff_cfg['name_contains']}' at {tariff_cfg['utility']}")
        print(f"  Available rates: {[r.get('name') for r in items[:10]]}")
        # Return all rates for this utility so user can inspect
        return {"utility": tariff_cfg["utility"], "query": tariff_cfg, "items": items}

    # Take the most recently updated match
    best = sorted(matches, key=lambda r: r.get("startdate", 0) or 0, reverse=True)[0]
    print(f"  [OK] Found: {best.get('name')} (label: {best.get('label')}, eia: {best.get('eiaid')})")
    return best


def fetch_all_tariffs() -> dict:
    """Fetch all 3 target tariffs and save to data/tariffs/."""
    api_key = os.getenv("OPENEI_API_KEY")
    if not api_key:
        raise ValueError("OPENEI_API_KEY not set in .env")

    TARIFFS_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    for cfg in TARGET_TARIFFS:
        print(f"\nFetching {cfg['label']}...")
        try:
            tariff = fetch_tariff(cfg, api_key)
            path = TARIFFS_DIR / f"{cfg['id']}_raw.json"
            with open(path, "w") as f:
                json.dump(tariff, f, indent=2)
            print(f"  Saved to {path}")
            results[cfg["id"]] = tariff
        except requests.HTTPError as e:
            print(f"  [ERROR] HTTP {e.response.status_code}: {e.response.text[:200]}")
            results[cfg["id"]] = None

    return results


if __name__ == "__main__":
    fetch_all_tariffs()
    print("\nDone. Check data/tariffs/ for raw JSON files.")
