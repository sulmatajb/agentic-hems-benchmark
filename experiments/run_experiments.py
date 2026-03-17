"""
Main experiment loop — 27 runs (3 models × 3 tariffs × 3 households × 3 seeds).

Usage:
    python experiments/run_experiments.py                        # all runs, 5 workers
    python experiments/run_experiments.py --workers 3            # limit concurrency
    python experiments/run_experiments.py --model deepseek/deepseek-chat
    python experiments/run_experiments.py --smoke-test           # 1 run, 24 hours
"""

import argparse
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parents[1]))

import pandas as pd
from src.data.tariff_parser import load_parsed_tariff
from src.simulation.household import load_household
from src.simulation.baseline import run_unmanaged, run_oracle, compute_hourly_cost
from src.agents import battery_agent, ev_charger_agent
from src.agents.orchestrator import run_hour
from src.utils.metrics import compute_metrics
from src.utils.llm_client import append_result
from experiments.experiment_config import TARIFFS, HOUSEHOLDS, SEEDS, RUN_ORDER


def hours_until_plugout(df: pd.DataFrame, current_hour: int) -> int:
    """How many hours until the EV is next unplugged (looking forward from current_hour)."""
    for offset in range(1, 25):
        future_h = current_hour + offset
        if future_h >= len(df):
            return 24
        prev_plugged = bool(df.iloc[current_hour]["ev_plugged_in"])
        curr_plugged = bool(df.iloc[future_h]["ev_plugged_in"])
        if prev_plugged and not curr_plugged:
            return offset
    return 24


def run_single(model_id: str, tariff_id: str, archetype: str, seed: int, max_hours: int = None) -> dict:
    """Run one simulation and return metrics dict. max_hours limits for testing."""
    tariff = load_parsed_tariff(tariff_id)
    df = load_household(archetype, seed)
    if max_hours:
        df = df.iloc[:max_hours].reset_index(drop=True)

    # Pre-compute baselines (deterministic, no LLM)
    unmanaged = run_unmanaged(df, tariff)
    oracle = run_oracle(df, tariff)

    # LLM-managed simulation state
    ev_soc = float(df.iloc[0]["ev_soc_kwh"])
    battery_soc = float(df.iloc[0]["home_battery_soc_kwh"])
    ev_cap = float(df.iloc[0]["ev_capacity_kwh"])
    bat_cap = float(df.iloc[0]["home_battery_capacity_kwh"])
    ev_daily_discharge = float(df.iloc[0].get("ev_daily_discharge_kwh", 12.0))
    prev_ev_plugged = int(df.iloc[0]["ev_plugged_in"])

    total_agent_cost = 0.0
    total_token_cost = 0.0
    total_latency_ms = 0.0
    decision_count = 0

    schedule = tariff["weekday_prices"]

    for i, row in df.iterrows():
        # Update mutable state in row copy
        row_dict = row.to_dict()
        row_dict["ev_soc_kwh"] = ev_soc
        row_dict["home_battery_soc_kwh"] = battery_soc

        horizon = []
        for offset in range(1, 7):
            if i + offset < len(df):
                h_row = df.iloc[i + offset].to_dict()
            else:
                h_row = row_dict.copy()
            horizon.append(h_row)

        departure_hours = hours_until_plugout(df, i)

        ctx = {
            "tariff": tariff_id,
            "household": archetype,
            "run_seed": seed,
            "hour": int(row["hour"]),
        }

        try:
            result = run_hour(
                model_id=model_id,
                tariff=tariff,
                row=row_dict,
                horizon_rows=horizon,
                hours_until_ev_departure=departure_hours,
                day_of_week=int(row["hour"]) // 24 % 7,
                context=ctx,
            )
            decision = result["decision"]
            total_token_cost += result["cost_usd"]
            total_latency_ms += result["latency_ms"]
            decision_count += 1
        except Exception as e:
            print(f"  [ERROR] hour {row['hour']}: {e}")
            decision = {
                "ev_charge_rate_pct": 0,
                "home_battery_action": "idle",
                "solar_action": "store",
            }

        # Apply EV departure discharge
        curr_ev_plugged = int(row_dict["ev_plugged_in"])
        if prev_ev_plugged == 1 and curr_ev_plugged == 0:
            ev_soc = max(ev_cap * 0.10, ev_soc - ev_daily_discharge)
        prev_ev_plugged = curr_ev_plugged

        # Apply decisions to simulation state
        ev_charge_kw = 0.0
        if row_dict["ev_plugged_in"]:
            ev_charge_kw = 7.2 * (decision["ev_charge_rate_pct"] / 100.0)
            ev_soc = ev_charger_agent.apply_ev_charge(
                ev_soc, ev_cap, decision["ev_charge_rate_pct"]
            )

        bat_net_kw = 0.0
        solar_kw = row_dict["solar_gen_kw"]
        bat_action = decision["home_battery_action"]
        new_bat_soc = battery_agent.apply_battery_action(battery_soc, bat_cap, bat_action, solar_kw)
        bat_net_kw = new_bat_soc - battery_soc
        battery_soc = new_bat_soc

        # Solar always offsets grid import; "store" means surplus charges battery
        # (already handled via battery action above), "export" sends surplus to grid
        effective_solar = solar_kw

        hour_cost = compute_hourly_cost(
            base_load_kw=row_dict["base_load_kw"],
            ev_charge_kw=ev_charge_kw,
            battery_charge_kw=bat_net_kw,
            solar_gen_kw=effective_solar,
            price_per_kwh=schedule[int(row["hour_of_day"])],
        )
        total_agent_cost += hour_cost

    avg_latency = total_latency_ms / decision_count if decision_count > 0 else 0.0
    days_run = len(df) / 24
    metrics = compute_metrics(
        agent_cost_usd=total_agent_cost,
        baseline_cost_usd=unmanaged["total_cost_usd"],
        oracle_cost_usd=oracle["total_cost_usd"],
        total_token_cost_usd=total_token_cost,
        avg_latency_ms=avg_latency,
        days=days_run,
    )

    row_out = {
        "model": model_id,
        "tariff": tariff_id,
        "household": archetype,
        "run_seed": seed,
        **{k: metrics[k] for k in [
            "energy_cost_reduction_pct", "oracle_gap_pct",
            "total_token_cost_usd", "avg_latency_ms",
            "daily_api_cost_usd", "breakeven_months"
        ]},
    }

    append_result(row_out)
    print(
        f"  ✓ {model_id} | {tariff_id} | {archetype} | seed={seed} "
        f"| savings={metrics['energy_cost_reduction_pct']:.1f}% "
        f"| oracle_gap={metrics['oracle_gap_pct']:.1f}% "
        f"| token_cost=${metrics['total_token_cost_usd']:.4f}"
    )
    return row_out


def _run_task(task: tuple) -> tuple:
    """Worker function for parallel execution. Returns (label, success, error)."""
    model_id, tariff_id, archetype, seed, label, max_hours = task
    try:
        run_single(model_id, tariff_id, archetype, seed, max_hours=max_hours)
        return (label, True, None)
    except Exception as e:
        traceback.print_exc()
        return (label, False, str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Run only this model ID")
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel workers (default: 5). Lower if hitting rate limits.")
    parser.add_argument("--smoke-test", action="store_true",
                        help="Single 24-hour run with DeepSeek to verify pipeline")
    parser.add_argument("--max-hours", type=int, default=None,
                        help="Limit simulation to N hours per run (e.g. 168 for 7 days)")
    args = parser.parse_args()

    if args.smoke_test:
        print("\n=== SMOKE TEST (24 hours, DeepSeek) ===")
        run_single("deepseek/deepseek-chat", "pge_etou_c", "small_suburban", 42, max_hours=24)
        print("Smoke test complete.")
        return

    models_to_run = RUN_ORDER
    if args.model:
        models_to_run = [m for m in RUN_ORDER if m["id"] == args.model]
        if not models_to_run:
            print(f"Model '{args.model}' not found in config.")
            sys.exit(1)

    # Load already-completed runs to skip on restart
    from src.utils.llm_client import RESULTS_CSV
    completed = set()
    if RESULTS_CSV.exists():
        existing = pd.read_csv(RESULTS_CSV)
        for _, row in existing.iterrows():
            completed.add((row["model"], row["tariff"], row["household"], int(row["run_seed"])))
        if completed:
            print(f"Skipping {len(completed)} already-completed runs.")

    max_hours = args.max_hours

    # Build flat task list, skipping completed
    tasks = [
        (m["id"], tariff_id, archetype, seed,
         f"{m['label']} | {tariff_id} | {archetype} | seed={seed}", max_hours)
        for m in models_to_run
        for tariff_id in TARIFFS
        for archetype in HOUSEHOLDS
        for seed in SEEDS
        if (m["id"], tariff_id, archetype, seed) not in completed
    ]

    total = len(tasks)
    done = 0
    errors = 0
    workers = min(args.workers, total)

    hours_label = f"{max_hours}h" if max_hours else "720h"
    print(f"\nStarting {total} runs with {workers} parallel workers ({hours_label}/run)...\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_run_task, t): t for t in tasks}
        for future in as_completed(futures):
            done += 1
            label, success, error = future.result()
            status = "✓" if success else "✗"
            if not success:
                errors += 1
                print(f"  [{done}/{total}] {status} {label} — ERROR: {error}")
            else:
                print(f"  [{done}/{total}] {status} {label}")

    print(f"\nDone. {done - errors}/{done} runs succeeded.")
    print(f"Results → experiments/results/results.csv")


if __name__ == "__main__":
    main()
