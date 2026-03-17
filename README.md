# HEMS LLM Benchmark

**Benchmarking Multi-Agent LLM Architectures for Home Energy Management: Real-World Tariff Validation and Cross-Model Cost-Efficiency Analysis**

![Python](https://img.shields.io/badge/Python-3.11-blue) ![OpenRouter](https://img.shields.io/badge/API-OpenRouter-orange) ![Format](https://img.shields.io/badge/Format-IEEE-lightgrey) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19074522.svg)](https://doi.org/10.5281/zenodo.19074522)

---

## Abstract

Multi-agent large language model (LLM) systems have recently been proposed for home energy management (HEMS), but existing work evaluates only a single model against simplified tariff structures. This paper addresses two open questions: (1) which LLM backend delivers the best cost-performance tradeoff for multi-agent HEMS scheduling, and (2) does the agentic HEMS architecture generalize to real-world US utility tariff structures beyond simplified simulation? We extend the open-source agentic-ai-hems architecture by benchmarking four LLMs spanning open-source, mid-tier, and frontier tiers (Llama 4 Maverick, DeepSeek-V3, GPT-4.1, Claude Sonnet 4.6) against three real US utility time-of-use structures (PG&E E-TOU-C, SCE TOU-D-4, ComEd Hourly Pricing) across three household archetypes and 7-day simulations (108 runs total). Our results show that three of four tested models achieve >20% energy cost reduction over an unmanaged baseline, with Claude Sonnet 4.6 reaching 49.3% reduction at $0.09/day in API cost, and DeepSeek-V3 delivering 37.8% reduction at only $0.005/day. We derive a deployment decision framework mapping LLM API cost against monthly energy savings by household size and model tier, providing the first economic viability assessment for agentic HEMS deployment.

---

## Repository Structure

```
hems-research/
├── src/
│   ├── agents/
│   │   ├── orchestrator.py       # Central LLM orchestrator agent
│   │   ├── battery_agent.py      # Home battery state + dispatch
│   │   ├── ev_charger_agent.py   # EV charging state + urgency
│   │   ├── solar_agent.py        # Solar generation + forecast
│   │   └── tariff_agent.py       # Tariff price reporting
│   ├── simulation/
│   │   ├── household.py          # Synthetic load profile generator
│   │   └── baseline.py           # Unmanaged + oracle baselines
│   ├── data/
│   │   ├── tariff_data.py        # Hardcoded 2024 US tariff structures
│   │   ├── tariff_parser.py      # Tariff normalization
│   │   └── openei_client.py      # OpenEI API client (reference)
│   └── utils/
│       ├── llm_client.py         # OpenRouter LLM wrapper
│       └── metrics.py            # Evaluation metrics
├── experiments/
│   ├── experiment_config.py      # 4 models × 3 tariffs × 3 households × 3 seeds
│   ├── run_experiments.py        # Parallel experiment runner
│   └── results/
│       └── results.csv           # 108-run experiment results
├── analysis/
│   └── analyze_results.py        # Reproduces all figures and tables
├── data/
│   ├── households/               # 9 synthetic household CSVs (3 archetypes × 3 seeds)
│   └── tariffs/                  # Parsed tariff JSON files
├── paper/
│   └── main.tex                  # IEEE-format paper source
├── notebooks/                    # Exploratory notebooks
├── requirements.txt
└── .env.template
```

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/besniksulmataj/hems-research.git
cd hems-research

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API key
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# 5. Verify pipeline with a smoke test (1 run, 24 hours, ~$0.001)
python experiments/run_experiments.py --smoke-test
```

---

## Reproducing Results

### Run all 108 experiments

```bash
# Runs 4 models × 3 tariffs × 3 households × 3 seeds in parallel
# Estimated cost: ~$25, estimated time: ~4 hours with 5 workers
python experiments/run_experiments.py --workers 5 --max-hours 168
```

Results are appended to `experiments/results/results.csv` after each run. The runner skips already-completed runs on restart.

### Generate all figures and tables

```bash
python analysis/analyze_results.py
```

Outputs:
- `analysis/figures/fig1_energy_savings.{png,pdf}`
- `analysis/figures/fig2_oracle_gap.{png,pdf}`
- `analysis/figures/fig3_cost_efficiency.{png,pdf}`
- `analysis/figures/fig4_tariff_heatmap.{png,pdf}`
- `analysis/figures/fig5_breakeven.{png,pdf}`
- `analysis/tables/table1_model_comparison.tex`
- `analysis/tables/table2_tariff_generalization.tex`

---

## Key Findings

1. **Claude Sonnet 4.6 achieves the highest energy savings (49.3%)** and the smallest oracle gap (31.8%), coming within 6.2% of theoretically optimal scheduling on large suburban households with full solar + EV + battery assets.

2. **DeepSeek-V3 dominates the cost-efficiency frontier**: 37.8% savings at $0.005/day in API cost, breaking even against energy savings in under 2 days for all household types.

3. **Tariff complexity is a stronger model differentiator than household size**: On ComEd real-time pricing, all models perform well (37-85% savings). On PG&E's complex 3-tier structure, only frontier and mid-tier models consistently exceed 20% savings — Llama 4 Maverick achieves only 3.8%.

---

## Citation

```bibtex
@article{sulmataj2025hems,
  title={Benchmarking Multi-Agent LLM Architectures for Home Energy Management:
         Real-World Tariff Validation and Cross-Model Cost-Efficiency Analysis},
  author={Sulmataj, Besnik},
  year={2025},
  url={https://doi.org/10.5281/zenodo.19074522}
}
```

---

## Acknowledgments

This work extends the multi-agent HEMS architecture developed by Makroum et al. (arXiv:2510.26603). Experiments conducted via the [OpenRouter](https://openrouter.ai) API. Tariff data sourced from 2024 utility tariff filings (PG&E, SCE, ComEd).

---

## License

MIT License. Copyright (c) 2025 Besnik Sulmataj. See [LICENSE](LICENSE) for details.
