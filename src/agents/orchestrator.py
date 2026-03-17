"""
Orchestrator Agent — the main LLM-powered decision maker.

Each hour it:
1. Collects reports from all 4 specialist agents
2. Builds a prompt and calls the LLM
3. Parses the JSON decision
4. Returns the decision + token usage for logging

Decision JSON schema (from research.md §13):
{
  "ev_charge_rate_pct": 0-100,
  "home_battery_action": "charge|discharge|idle",
  "solar_action": "export|store",
  "reasoning": "<one sentence>"
}
"""

import json
import re
from typing import Optional

from src.agents import tariff_agent, solar_agent, battery_agent, ev_charger_agent
from src.utils.llm_client import call_llm

SYSTEM_PROMPT = """You are an intelligent home energy management system. Your goal is to minimize \
electricity costs for a household with solar panels, a home battery, and an EV.

You receive hourly reports from specialist agents and must decide:
1. EV charging rate (0-100% of max rate)
2. Home battery action (charge / discharge / idle)
3. Solar export decision (export to grid / store in battery)

Always respond in JSON format:
{
  "ev_charge_rate_pct": <0-100>,
  "home_battery_action": "charge|discharge|idle",
  "solar_action": "export|store",
  "reasoning": "<one sentence>"
}

Prioritize: avoid peak tariff hours, charge EV when electricity is cheapest, \
ensure EV is at required SoC by departure time."""

DEFAULT_DECISION = {
    "ev_charge_rate_pct": 0,
    "home_battery_action": "idle",
    "solar_action": "store",
    "reasoning": "parse_error_fallback"
}


def _parse_decision(content: str) -> dict:
    """Extract JSON decision from LLM response. Handles markdown code fences."""
    # Strip markdown fences if present
    content = re.sub(r"```(?:json)?", "", content).strip()
    # Find first {...} block
    match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
    if not match:
        return DEFAULT_DECISION.copy()
    try:
        decision = json.loads(match.group(0))
    except json.JSONDecodeError:
        return DEFAULT_DECISION.copy()

    # Validate and clamp fields
    ev_rate = decision.get("ev_charge_rate_pct", 0)
    battery_action = decision.get("home_battery_action", "idle")
    solar_action = decision.get("solar_action", "store")
    reasoning = decision.get("reasoning", "")

    return {
        "ev_charge_rate_pct": max(0, min(100, int(ev_rate))),
        "home_battery_action": battery_action if battery_action in ("charge", "discharge", "idle") else "idle",
        "solar_action": solar_action if solar_action in ("export", "store") else "store",
        "reasoning": str(reasoning)[:200],
    }


def run_hour(
    model_id: str,
    tariff: dict,
    row: dict,
    horizon_rows: list,
    hours_until_ev_departure: int,
    day_of_week: int = 0,
    context: Optional[dict] = None,
) -> dict:
    """
    Run one hour of orchestration.

    Args:
        model_id: OpenRouter model ID
        tariff: Parsed tariff dict
        row: Current hour household row (dict)
        horizon_rows: Next 6 hours of household rows
        hours_until_ev_departure: Hours until EV must leave
        day_of_week: 0=Mon … 6=Sun
        context: Optional logging context (tariff, household, run_seed, hour)

    Returns:
        dict with: decision (ev_charge_rate_pct, home_battery_action, solar_action, reasoning),
                   prompt_tokens, completion_tokens, latency_ms, cost_usd, raw_content
    """
    hour_of_day = int(row["hour_of_day"])

    t_report = tariff_agent.get_tariff_report(tariff, hour_of_day, day_of_week)
    s_report = solar_agent.get_solar_report(row, horizon_rows)
    b_report = battery_agent.get_battery_report(row)
    e_report = ev_charger_agent.get_ev_report(row, hours_until_ev_departure)

    user_message = "\n\n".join([
        tariff_agent.format_for_prompt(t_report),
        solar_agent.format_for_prompt(s_report),
        battery_agent.format_for_prompt(b_report),
        ev_charger_agent.format_for_prompt(e_report),
    ])

    llm_result = call_llm(
        model_id=model_id,
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        context=context,
    )

    decision = _parse_decision(llm_result["content"])

    return {
        "decision": decision,
        "prompt_tokens": llm_result["prompt_tokens"],
        "completion_tokens": llm_result["completion_tokens"],
        "latency_ms": llm_result["latency_ms"],
        "cost_usd": llm_result["cost_usd"],
        "raw_content": llm_result["content"],
    }
