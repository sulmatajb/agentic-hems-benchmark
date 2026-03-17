# Agentic HEMS Research Project
## Benchmarking Multi-Agent LLM Architectures for Home Energy Management: Real-World Tariff Validation and Cross-Model Cost-Efficiency Analysis

---

## 1. Project Overview

This is an independent research project targeting an **ArXiv preprint submission by end of March 2026**.

The research extends the open-source agentic-ai-hems architecture (ArXiv 2510.26603, RedaElMakroum) by:
- Validating it against **real US utility tariff structures** (vs. simplified simulated tariffs in the original paper)
- Running a **cross-model benchmark** across 7 LLMs spanning frontier, mid-tier, and open-source tiers
- Producing a **cost-efficiency analysis** showing the break-even point between energy savings and LLM API cost

The researcher is a Senior Business Operations Analyst / DBA at Schneider Electric (Prosumer division). This is independent research but should be framed to resonate with the residential energy management and V2G space (SE's EcoStruxure, Wiser HEMS, EVlink product lines).

---

## 2. Research Question

> *"Which LLM backend delivers the best cost-performance tradeoff for multi-agent home energy management, and does the agentic HEMS architecture generalize to real-world US utility tariff structures beyond simplified simulation?"*

---

## 3. Novel Contributions (What Makes This Publishable)

**C1 — First cross-model benchmark for agentic HEMS**
No published paper has compared GPT, Claude, Gemini, and open-source models on the same HEMS scheduling task. This paper produces a concrete comparison: energy cost reduction %, scheduling accuracy, latency, and token cost per decision across 7 models.

**C2 — Real tariff validation**
The baseline paper (ArXiv 2510.26603) used only simplified/simulated tariff structures. This paper runs the same architecture against 3 real US utility TOU structures from the OpenEI database (PG&E, SCE, ComEd), providing the first real-world tariff validation of this architecture.

**C3 — Economic break-even analysis**
No published HEMS paper has answered: "At what LLM API cost does the energy saving stop being worth it?" This paper produces a deployment decision framework — which model tier makes economic sense at what household size.

---

## 4. Hypothesis

> Multi-agent LLM coordination achieves meaningful energy cost reduction (>20%) against real US TOU tariffs, but LLM choice significantly affects the cost-efficiency ratio — making model selection a deployable design decision, not just an academic one.

---

## 5. Models to Test

All models accessed via **OpenRouter** (single API, OpenAI-compatible SDK).
Base URL: `https://openrouter.ai/api/v1`
API Key: stored in `.env` as `OPENROUTER_API_KEY`

**IMPORTANT:** Verify exact model IDs on openrouter.ai/models before running — IDs below are approximate and may need updating.

| Tier | Model | OpenRouter ID (verify) |
|------|-------|----------------------|
| Frontier | GPT-5.4 | `openai/gpt-5.4` |
| Frontier | Claude Opus 4.6 | `anthropic/claude-opus-4-6` |
| Frontier | Gemini 3.1 Pro | `google/gemini-3.1-pro` |
| Mid-tier | Claude Sonnet 4.6 | `anthropic/claude-sonnet-4-6` |
| Mid-tier | GPT-4o | `openai/gpt-4o` |
| Open source | DeepSeek-V3.2 | `deepseek/deepseek-chat` |
| Open source | Llama 4 | `meta-llama/llama-4-maverick` |

---

## 6. Tech Stack

| Tool | Role |
|------|------|
| Python 3.11+ | Core language |
| OpenRouter API | Unified LLM access (all 7 models via one key) |
| OpenAI SDK (`openai` package) | Client for OpenRouter (compatible) |
| OpenEI API | Real US utility tariff data |
| pandas / numpy | Data processing and simulation |
| matplotlib / seaborn | Results visualization |
| python-dotenv | API key management |
| Jupyter | Interactive experimentation |
| Git | Version control |

---

## 7. Project File Structure

Build the following structure:

```
hems-research/
├── .env                          # API keys (never commit)
├── .gitignore                    # includes .env
├── research.md                   # this file
├── agentic-ai-hems/              # cloned baseline repo
├── data/
│   ├── tariffs/                  # OpenEI tariff JSON files
│   └── households/               # synthetic load profile CSVs
├── src/
│   ├── agents/
│   │   ├── orchestrator.py       # main orchestrator agent
│   │   ├── ev_charger_agent.py   # EV charging scheduler
│   │   ├── solar_agent.py        # solar generation tracker
│   │   ├── battery_agent.py      # home battery manager
│   │   └── tariff_agent.py       # grid tariff monitor
│   ├── simulation/
│   │   ├── household.py          # household load profile generator
│   │   └── baseline.py           # unmanaged baseline (no AI)
│   ├── data/
│   │   ├── openei_client.py      # OpenEI API client
│   │   └── tariff_parser.py      # parse and normalize tariff structures
│   └── utils/
│       ├── llm_client.py         # OpenRouter wrapper with token logging
│       └── metrics.py            # evaluation metrics calculator
├── experiments/
│   ├── run_experiments.py        # main experiment loop (all models × tariffs × households)
│   ├── experiment_config.py      # defines all combinations to run
│   └── results/                  # auto-generated CSV results
├── analysis/
│   ├── analyze_results.py        # generate tables and charts for paper
│   └── figures/                  # output charts
├── paper/
│   └── main.tex                  # LaTeX paper (Overleaf compatible)
└── notebooks/
    └── exploration.ipynb         # scratch space
```

---

## 8. Data Sources

### 8.1 OpenEI Tariff Data (Real US Utility Rates)

Register free at: `openei.org/services/api/signup`
Store key in `.env` as `OPENEI_API_KEY`

Pull these 3 tariff structures:
- **PG&E E-TOU-C** — Pacific Gas & Electric, California (Time-of-Use residential)
- **SCE TOU-D-PRIME** — Southern California Edison (Time-of-Use with solar)
- **ComEd Hourly Pricing** — Commonwealth Edison, Illinois (real-time pricing)

These represent different TOU structures: 2-tier, 3-tier, and real-time — good coverage for generalization testing.

API endpoint: `https://api.openei.org/utility_rates`

### 8.2 Synthetic Household Load Profiles

Generate 3 household archetypes (30 days each, hourly resolution):

**Small Suburban:**
- Base load: 0.5 kW average
- EV battery: 60 kWh (plugged in 6pm-7am)
- Solar: 5 kW peak
- Home battery: 10 kWh

**Large Suburban:**
- Base load: 1.2 kW average
- EV battery: 100 kWh (plugged in 6pm-7am)
- Solar: 10 kW peak
- Home battery: 20 kWh

**Apartment:**
- Base load: 0.3 kW average
- EV battery: 40 kWh (plugged in 7pm-8am)
- Solar: 0 kW (no rooftop)
- Home battery: 5 kWh

Use fixed random seeds (42, 43, 44) for reproducibility.

---

## 9. Experiment Design

### 9.1 What to Run

Full factorial experiment:
- **7 models** × **3 tariff structures** × **3 household archetypes** = **63 experiment runs**
- Each run: 30-day simulation, hourly scheduling decisions
- Each run repeated **3 times** with different seeds for statistical validity
- Total: 189 LLM-powered simulations + 9 unmanaged baselines (one per tariff × household)

### 9.2 What Each Run Does

For each hour in the 30-day simulation:
1. **Tariff Agent** reads current and upcoming electricity prices from the tariff structure
2. **Solar Agent** reports current and forecast solar generation
3. **Battery Agent** reports current home battery SoC and capacity
4. **EV Charger Agent** reports EV SoC, departure time, and charging constraints
5. **Orchestrator Agent** receives all agent reports, makes scheduling decision:
   - Should we charge the EV now or wait?
   - Should we store solar in home battery or export to grid?
   - Should we discharge home battery to avoid peak tariff?
6. Decision is executed in simulation, cost is logged

### 9.3 Unmanaged Baseline

Same simulation but EV charges immediately when plugged in at max rate, no solar optimization, no battery dispatch. This is what a typical homeowner does today. All results reported as % improvement over this baseline.

### 9.4 Oracle Baseline

Linear programming optimal solution (scipy.optimize) — knows future prices perfectly. Used to measure how close each LLM gets to theoretical optimum.

### 9.5 Token Logging

Log for every LLM call:
- Model name
- Prompt tokens
- Completion tokens
- Latency (ms)
- Cost ($ via OpenRouter usage API)

This data feeds the cost-efficiency analysis (Contribution C3).

---

## 10. LLM Client Setup

Use this pattern for all model calls — swapping model ID is the only change needed:

```python
from openai import OpenAI
import os, time
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def call_llm(model_id: str, system_prompt: str, user_message: str) -> dict:
    start = time.time()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.0  # deterministic for reproducibility
    )
    latency = (time.time() - start) * 1000

    return {
        "content": response.choices[0].message.content,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "latency_ms": latency,
        "model": model_id
    }
```

**Important:** Set `temperature=0.0` on all calls for reproducibility. This is required for a credible paper.

---

## 11. Evaluation Metrics

For every experiment run, calculate and log:

| Metric | Formula | Unit |
|--------|---------|------|
| Energy cost reduction | `(baseline_cost - agent_cost) / baseline_cost × 100` | % |
| Oracle gap | `(oracle_cost - agent_cost) / oracle_cost × 100` | % (lower = better) |
| Token cost per day | `total_token_cost / 30` | $/day |
| Avg scheduling latency | `mean(latency_ms per decision)` | ms |
| Break-even months | `token_cost_annual / monthly_energy_savings` | months |
| Daily API cost | `total_token_cost / 30` | $ |

---

## 12. Results Format

Save all results to `experiments/results/results.csv` with columns:

```
model, tariff, household, run_seed, energy_cost_reduction_pct,
oracle_gap_pct, total_token_cost_usd, avg_latency_ms,
daily_api_cost_usd, breakeven_months
```

---

## 13. Key Agent Prompts

### Orchestrator System Prompt
```
You are an intelligent home energy management system. Your goal is to minimize
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

Prioritize: avoid peak tariff hours, charge EV when electricity is cheapest,
ensure EV is at required SoC by departure time.
```

---

## 14. Paper Outline

Target: ArXiv preprint (cs.AI + eess.SY cross-list)
Format: IEEE two-column, 6-8 pages
Write in Overleaf (LaTeX)

**Sections:**
1. Abstract
2. Introduction — problem statement, why it matters for residential energy
3. Related Work — ArXiv 2510.26603 baseline, existing HEMS literature
4. Methodology — agent architecture, experiment design, model selection rationale
5. Experimental Setup — tariffs, household archetypes, evaluation metrics
6. Results — comparison tables, cost-efficiency charts, oracle gap analysis
7. Discussion — which model tier makes sense for deployment, open-source viability
8. Conclusion — key findings, future work (V2H extension, V2G incentive design)

---

## 15. Success Criteria

The paper is ready to submit when:
- [ ] 63 experiment runs completed and logged
- [ ] Statistical significance confirmed (3 seeds per condition)
- [ ] At least one model achieves >20% energy cost reduction on real tariffs
- [ ] Clear cost-efficiency ranking across all 7 models
- [ ] Break-even analysis table complete
- [ ] All figures generated (model comparison bar chart, cost vs savings scatter, tariff generalization heatmap)
- [ ] Paper draft complete (6-8 pages IEEE format)

---

## 16. Timeline

| Day | Tasks |
|-----|-------|
| Day 1 (Mon Mar 16) | Repo cloned, environment set up, OpenEI tariff data pulled, synthetic households generated |
| Day 2 (Tue Mar 17) | Agent architecture built, all 7 models tested on single run, experiment loop running |
| Day 3 (Wed Mar 18) | All 189 runs complete, results logged to CSV |
| Day 4 (Thu Mar 19) | Analysis complete, all figures generated, paper draft written |
| Day 5 (Fri Mar 20) | Paper review, polish, ArXiv submission |

---

## 17. Important Notes for Claude Code

1. **Never hardcode API keys** — always read from `.env` via `python-dotenv`
2. **Always set temperature=0.0** on LLM calls for reproducibility
3. **Log everything** — every LLM call should log model, tokens, cost, latency to results CSV
4. **Fixed random seeds** — use seeds 42, 43, 44 for the 3 simulation repeats
5. **Check OpenRouter model IDs** at openrouter.ai/models before running — IDs in Section 5 are approximate
6. **Build the oracle baseline first** — needed as reference point for all other metrics
7. **Run cheap models first** (DeepSeek, Llama 4) to validate the pipeline before spending on frontier models
8. **Save intermediate results** — don't wait for all 189 runs to finish before saving, append to CSV after each run
9. **The agentic-ai-hems repo** is the architectural reference — study its agent structure before building, adapt rather than copy
10. **Paper audience** — residential energy practitioners and AI researchers, not just ML specialists. Keep methodology section accessible.

---

## 18. Reference Papers

- **Baseline:** ArXiv 2510.26603 — "Agentic AI for Home Energy Management Systems" (RedaElMakroum)
- **V2G Digital Twins:** ArXiv 2504.01423 — "LLM Digital Twin for EV Charging Demand Response"
- **DOE VGI Assessment:** energy.gov VGI Report January 2025
- **RL Battery Management:** IEEE 2025, ieeexplore.ieee.org/document/11376761

---

*Last updated: March 16, 2026*
*Researcher: Senior Business Operations Analyst / DBA — Schneider Electric Prosumer*
*Status: Day 1 — Setup*
