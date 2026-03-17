"""
Experiment configuration — 4-model design.
36 runs total: 4 models × 3 tariffs × 3 households × 3 seeds.

Open-source tier has two models:
  - DeepSeek-V3: cloud-hosted benchmark reference
  - Llama 4 Maverick: self-hostable, recommended for data-sovereign deployments

Verify OpenRouter model IDs at openrouter.ai/models before running.
"""

MODELS = [
    # Frontier
    {"id": "anthropic/claude-sonnet-4-6", "tier": "frontier", "label": "Claude Sonnet 4.6"},
    # Mid-tier
    {"id": "openai/gpt-4.1", "tier": "mid", "label": "GPT-4.1"},
    # Open source — cloud
    {"id": "deepseek/deepseek-chat", "tier": "open", "label": "DeepSeek-V3"},
    # Open source — self-hostable
    {"id": "meta-llama/llama-4-maverick", "tier": "open", "label": "Llama 4 Maverick"},
]

TARIFFS = ["pge_etou_c", "sce_tou_d_prime", "comed_hourly"]

HOUSEHOLDS = ["small_suburban", "large_suburban", "apartment"]

SEEDS = [42, 43, 44]

# Run cheap models first to validate pipeline before spending on frontier
RUN_ORDER = (
    [m for m in MODELS if m["tier"] == "open"]
    + [m for m in MODELS if m["tier"] == "mid"]
    + [m for m in MODELS if m["tier"] == "frontier"]
)
