"""
OpenRouter LLM client for HEMS research.
Wraps OpenAI SDK to call any model via OpenRouter with token/cost/latency logging.
"""

import os
import time
import csv
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

RESULTS_CSV = Path(__file__).parents[2] / "experiments" / "results" / "results.csv"
LOG_CSV = Path(__file__).parents[2] / "experiments" / "results" / "llm_calls.csv"

RESULTS_HEADERS = [
    "model", "tariff", "household", "run_seed",
    "energy_cost_reduction_pct", "oracle_gap_pct",
    "total_token_cost_usd", "avg_latency_ms",
    "daily_api_cost_usd", "breakeven_months"
]

LOG_HEADERS = [
    "model", "tariff", "household", "run_seed", "hour",
    "prompt_tokens", "completion_tokens", "latency_ms", "cost_usd"
]


def _ensure_csv(path: Path, headers: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()


def get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in .env")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )


def call_llm(
    model_id: str,
    system_prompt: str,
    user_message: str,
    context: Optional[dict] = None
) -> dict:
    """
    Call an LLM via OpenRouter and return response with token/latency data.

    Args:
        model_id: OpenRouter model ID (e.g. 'deepseek/deepseek-chat')
        system_prompt: System prompt string
        user_message: User message string
        context: Optional dict with tariff/household/seed for logging

    Returns:
        dict with keys: content, prompt_tokens, completion_tokens, latency_ms,
                        model, cost_usd (from usage if available)
    """
    client = get_client()
    start = time.time()

    # Retry up to 3 times on timeout or server error
    last_err = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,
                timeout=60.0,  # 60s hard timeout per call
            )
            break
        except Exception as e:
            last_err = e
            wait = 5 * (attempt + 1)
            print(f"  [RETRY {attempt+1}/3] {model_id} — {e} — waiting {wait}s")
            time.sleep(wait)
    else:
        raise last_err

    latency_ms = (time.time() - start) * 1000
    usage = response.usage

    # OpenRouter may return cost in usage.prompt_tokens_details or as a separate field
    # Fall back to 0.0 if not available — costs can be tracked via OpenRouter dashboard
    cost_usd = getattr(usage, "prompt_tokens_details", None)
    if cost_usd and hasattr(cost_usd, "cost"):
        cost_usd = cost_usd.cost
    else:
        cost_usd = 0.0

    result = {
        "content": response.choices[0].message.content,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "latency_ms": round(latency_ms, 1),
        "model": model_id,
        "cost_usd": cost_usd,
    }

    # Append to call log if context provided
    if context:
        _ensure_csv(LOG_CSV, LOG_HEADERS)
        with open(LOG_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
            writer.writerow({
                "model": model_id,
                "tariff": context.get("tariff", ""),
                "household": context.get("household", ""),
                "run_seed": context.get("run_seed", ""),
                "hour": context.get("hour", ""),
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "latency_ms": round(latency_ms, 1),
                "cost_usd": cost_usd,
            })

    return result


def append_result(row: dict) -> None:
    """Append one experiment result row to results.csv."""
    _ensure_csv(RESULTS_CSV, RESULTS_HEADERS)
    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_HEADERS)
        writer.writerow({k: row.get(k, "") for k in RESULTS_HEADERS})
