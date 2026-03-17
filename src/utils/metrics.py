"""
Evaluation metrics calculator.
All metrics from research.md §11.
"""


def compute_metrics(
    agent_cost_usd: float,
    baseline_cost_usd: float,
    oracle_cost_usd: float,
    total_token_cost_usd: float,
    avg_latency_ms: float,
    days: int = 30,
) -> dict:
    """
    Compute all paper metrics for one experiment run.

    Returns:
        energy_cost_reduction_pct   — % savings vs unmanaged baseline
        oracle_gap_pct              — % above oracle optimum (lower = better)
        daily_api_cost_usd          — token cost per day
        avg_latency_ms              — mean LLM latency per decision
        breakeven_months            — months until API cost equals energy savings
    """
    # Energy cost reduction: how much cheaper than doing nothing
    if baseline_cost_usd > 0:
        energy_cost_reduction_pct = (baseline_cost_usd - agent_cost_usd) / baseline_cost_usd * 100
    else:
        energy_cost_reduction_pct = 0.0

    # Oracle gap: how far from theoretically optimal
    if oracle_cost_usd > 0:
        oracle_gap_pct = (agent_cost_usd - oracle_cost_usd) / oracle_cost_usd * 100
    else:
        oracle_gap_pct = 0.0

    daily_api_cost_usd = total_token_cost_usd / days if days > 0 else 0.0

    # Break-even: months for energy savings to cover API cost
    monthly_energy_savings = (baseline_cost_usd - agent_cost_usd) / (days / 30)
    monthly_api_cost = daily_api_cost_usd * 30
    if monthly_energy_savings > 0:
        breakeven_months = monthly_api_cost / monthly_energy_savings
    else:
        breakeven_months = float("inf")

    return {
        "energy_cost_reduction_pct": round(energy_cost_reduction_pct, 3),
        "oracle_gap_pct": round(oracle_gap_pct, 3),
        "daily_api_cost_usd": round(daily_api_cost_usd, 6),
        "avg_latency_ms": round(avg_latency_ms, 1),
        "breakeven_months": round(breakeven_months, 2) if breakeven_months != float("inf") else None,
        "agent_cost_usd": round(agent_cost_usd, 4),
        "baseline_cost_usd": round(baseline_cost_usd, 4),
        "oracle_cost_usd": round(oracle_cost_usd, 4),
        "total_token_cost_usd": round(total_token_cost_usd, 6),
    }
