"""
Analysis pipeline — reads experiments/results/results.csv and generates:
  - All figures (PNG + PDF) → analysis/figures/
  - LaTeX table snippets → analysis/tables/
  - Summary statistics printed to stdout

Run after experiments complete:
    python analysis/analyze_results.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

RESULTS_CSV = Path(__file__).parent.parent / "experiments" / "results" / "results.csv"
FIGURES_DIR = Path(__file__).parent / "figures"
TABLES_DIR = Path(__file__).parent / "tables"

# IEEE two-column publication style
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.fontsize": 8,
    "legend.framealpha": 0.9,
    "legend.edgecolor": "#cccccc",
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
})

# Colorblind-safe palette (Wong 2011)
MODEL_ORDER = ["Llama 4 Maverick", "DeepSeek-V3", "GPT-4.1", "Claude Sonnet 4.6"]
MODEL_COLORS = {
    "Llama 4 Maverick":  "#CC79A7",  # pink
    "DeepSeek-V3":       "#009E73",  # green
    "GPT-4.1":           "#0072B2",  # blue
    "Claude Sonnet 4.6": "#E69F00",  # amber
}
MODEL_SHORT = {
    "Llama 4 Maverick":  "Llama 4\nMaverick",
    "DeepSeek-V3":       "DeepSeek\nV3",
    "GPT-4.1":           "GPT-4.1",
    "Claude Sonnet 4.6": "Claude\nSonnet 4.6",
}
TARIFF_LABELS = {
    "pge_etou_c":      "PG&E E-TOU-C",
    "sce_tou_d_prime":  "SCE TOU-D-4",
    "comed_hourly":    "ComEd Hourly",
}
HOUSEHOLD_LABELS = {
    "small_suburban": "Small Suburban",
    "large_suburban": "Large Suburban",
    "apartment":      "Apartment",
}


DAILY_API_COST = {
    "Llama 4 Maverick":  0.0044,
    "DeepSeek-V3":       0.0051,
    "GPT-4.1":           0.0386,
    "Claude Sonnet 4.6": 0.0877,
}

# Estimated monthly electricity baseline by household archetype
# Based on archetype load profiles at US avg ~$0.16/kWh
MONTHLY_BASELINE_USD = {
    "small_suburban": 105.0,
    "large_suburban": 223.0,
    "apartment":       65.0,
}


def load_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    label_map = {
        "meta-llama/llama-4-maverick":  "Llama 4 Maverick",
        "deepseek/deepseek-chat":       "DeepSeek-V3",
        "openai/gpt-4.1":               "GPT-4.1",
        "anthropic/claude-sonnet-4-6":  "Claude Sonnet 4.6",
    }
    df["model_label"] = df["model"].map(label_map).fillna(df["model"])
    df["tariff_label"] = df["tariff"].map(TARIFF_LABELS).fillna(df["tariff"])
    df["household_label"] = df["household"].map(HOUSEHOLD_LABELS).fillna(df["household"])

    # Compute breakeven from actual API costs and estimated baseline
    df["daily_api_cost_usd"] = df["model_label"].map(DAILY_API_COST)
    df["monthly_api_cost_usd"] = df["daily_api_cost_usd"] * 30
    df["monthly_baseline_usd"] = df["household"].map(MONTHLY_BASELINE_USD)
    df["monthly_saved_usd"] = df["monthly_baseline_usd"] * (df["energy_cost_reduction_pct"] / 100)
    df["breakeven_months"] = df["monthly_api_cost_usd"] / df["monthly_saved_usd"].clip(lower=0.01)
    return df


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics across seeds — mean ± std per model/tariff/household."""
    agg = df.groupby(["model_label", "tariff", "household"]).agg(
        savings_mean=("energy_cost_reduction_pct", "mean"),
        savings_std=("energy_cost_reduction_pct", "std"),
        oracle_gap_mean=("oracle_gap_pct", "mean"),
        latency_mean=("avg_latency_ms", "mean"),
        daily_cost_mean=("daily_api_cost_usd", "mean"),
        breakeven_mean=("breakeven_months", "mean"),
    ).reset_index()
    return agg


# ── Figure 1: Energy cost reduction by model ─────────────────────────────────
def fig_energy_savings(df: pd.DataFrame):
    agg = df.groupby("model_label").agg(
        mean=("energy_cost_reduction_pct", "mean"),
        std=("energy_cost_reduction_pct", "std"),
    ).reindex(MODEL_ORDER)

    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    colors = [MODEL_COLORS[m] for m in agg.index]
    x = np.arange(len(agg))
    bars = ax.bar(x, agg["mean"], yerr=agg["std"], color=colors,
                  capsize=3, width=0.55, edgecolor="white", linewidth=0.5,
                  error_kw={"linewidth": 0.8, "capthick": 0.8})
    ax.axhline(20, color="#d62728", linestyle="--", linewidth=0.9,
               label="20% target", zorder=0)
    ax.set_ylabel("Cost reduction vs. unmanaged (%)")
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in agg.index], fontsize=7.5)
    ax.set_ylim(0, max(agg["mean"] + agg["std"]) * 1.25)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=7.5)
    for bar, val in zip(bars, agg["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + agg["std"].max() * 0.08,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    fig.tight_layout(pad=0.5)
    _save(fig, "fig1_energy_savings")


# ── Figure 2: Oracle gap by model ────────────────────────────────────────────
def fig_oracle_gap(df: pd.DataFrame):
    agg = df.groupby("model_label").agg(
        mean=("oracle_gap_pct", "mean"),
        std=("oracle_gap_pct", "std"),
    ).reindex(MODEL_ORDER)

    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    colors = [MODEL_COLORS[m] for m in agg.index]
    x = np.arange(len(agg))
    bars = ax.bar(x, agg["mean"], yerr=agg["std"], color=colors,
                  capsize=3, width=0.55, edgecolor="white", linewidth=0.5,
                  error_kw={"linewidth": 0.8, "capthick": 0.8})
    ax.set_ylabel("Oracle gap (% above optimal, ↓ better)")
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in agg.index], fontsize=7.5)
    ax.set_ylim(0, max(agg["mean"] + agg["std"]) * 1.25)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    for bar, val in zip(bars, agg["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + agg["std"].max() * 0.08,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    fig.tight_layout(pad=0.5)
    _save(fig, "fig2_oracle_gap")


# ── Figure 3: Cost-efficiency scatter ────────────────────────────────────────
def fig_cost_efficiency(df: pd.DataFrame):
    agg = df.groupby("model_label").agg(
        savings=("energy_cost_reduction_pct", "mean"),
        daily_cost=("daily_api_cost_usd", "mean"),
    ).reindex(MODEL_ORDER)

    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    offsets = {
        "Llama 4 Maverick":  (-12, 6),
        "DeepSeek-V3":       (6, 6),
        "GPT-4.1":           (6, -11),
        "Claude Sonnet 4.6": (6, 4),
    }
    for model, row in agg.iterrows():
        ax.scatter(row["daily_cost"], row["savings"],
                   color=MODEL_COLORS[model], s=80, zorder=5,
                   edgecolors="white", linewidths=0.5)
        ox, oy = offsets.get(model, (6, 4))
        ax.annotate(MODEL_SHORT[model].replace("\n", " "),
                    (row["daily_cost"], row["savings"]),
                    textcoords="offset points", xytext=(ox, oy),
                    fontsize=7, color=MODEL_COLORS[model], fontweight="bold")
    ax.set_xlabel("Daily API cost (USD)")
    ax.set_ylabel("Energy cost reduction (%)")
    ax.set_xscale("log")
    ax.xaxis.grid(True, zorder=0, which="both")
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.annotate("upper-left = best value", xy=(0.97, 0.05),
                xycoords="axes fraction", ha="right",
                fontsize=6.5, color="gray", style="italic")
    fig.tight_layout(pad=0.5)
    _save(fig, "fig3_cost_efficiency")


# ── Figure 4: Tariff generalization heatmap ───────────────────────────────────
def fig_tariff_heatmap(df: pd.DataFrame):
    pivot = df.groupby(["model_label", "tariff_label"])["energy_cost_reduction_pct"].mean().unstack()
    pivot = pivot.reindex(MODEL_ORDER)

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlGn",
                linewidths=0.4, linecolor="white",
                ax=ax, cbar_kws={"label": "Savings (%)", "shrink": 0.85},
                annot_kws={"size": 8, "weight": "bold"},
                vmin=0, vmax=90)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=7.5)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=20, ha="right", fontsize=7.5)
    fig.tight_layout(pad=0.5)
    _save(fig, "fig4_tariff_heatmap")


# ── Figure 5: Monthly net savings ($) ────────────────────────────────────────
def fig_breakeven(df: pd.DataFrame):
    MONTHLY_BASELINE = {"Small Suburban": 105.0, "Large Suburban": 223.0, "Apartment": 65.0}
    df2 = df.copy()
    df2["monthly_saved"] = df2["household_label"].map(MONTHLY_BASELINE) * (df2["energy_cost_reduction_pct"] / 100)
    df2["monthly_net"] = df2["monthly_saved"] - df2["daily_api_cost_usd"] * 30

    agg = df2.groupby(["model_label", "household_label"])["monthly_net"].mean().unstack()
    agg = agg.reindex(MODEL_ORDER)

    hh_colors = ["#4BACC6", "#70AD47", "#ED7D31"]
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    x = np.arange(len(agg.index))
    width = 0.22
    for i, (household, color) in enumerate(zip(agg.columns, hh_colors)):
        ax.bar(x + i * width, agg[household], width=width,
               label=household, color=color, edgecolor="white", linewidth=0.4)
    ax.set_xticks(x + width)
    ax.set_xticklabels([MODEL_SHORT[m] for m in agg.index], fontsize=7.5)
    ax.set_ylabel("Monthly net savings (USD)")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=7, loc="upper left", ncol=1, framealpha=0.9)
    fig.tight_layout(pad=0.5)
    _save(fig, "fig5_breakeven")


# ── Table 1: Model comparison (LaTeX) ────────────────────────────────────────
def table_model_comparison(df: pd.DataFrame):
    agg = df.groupby("model_label").agg(
        savings_mean=("energy_cost_reduction_pct", "mean"),
        savings_std=("energy_cost_reduction_pct", "std"),
        oracle_gap=("oracle_gap_pct", "mean"),
        latency=("avg_latency_ms", "mean"),
        daily_cost=("daily_api_cost_usd", "mean"),
    ).reindex(MODEL_ORDER)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Model Comparison: Energy Cost Reduction and Efficiency Metrics}",
        r"\label{tab:model_comparison}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Model & Savings (\%) & Oracle Gap (\%) & Latency (ms) & Daily API (\$) \\",
        r"\midrule",
    ]
    for model, row in agg.iterrows():
        lines.append(
            f"{model} & "
            f"${row['savings_mean']:.1f} \\pm {row['savings_std']:.1f}$ & "
            f"${row['oracle_gap']:.1f}$ & "
            f"${row['latency']:.0f}$ & "
            f"${row['daily_cost']:.4f}$ \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]

    _save_table("\n".join(lines), "table1_model_comparison.tex")
    print("\n--- Table 1 preview ---")
    print(agg.to_string())


# ── Table 2: Tariff generalization ───────────────────────────────────────────
def table_tariff_generalization(df: pd.DataFrame):
    pivot = df.groupby(["model_label", "tariff_label"])["energy_cost_reduction_pct"].mean().unstack()
    pivot = pivot.reindex(MODEL_ORDER)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Tariff Generalization: Energy Savings (\%) Across US Utility Structures}",
        r"\label{tab:tariff_generalization}",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        f"Model & {' & '.join(pivot.columns)} \\\\",
        r"\midrule",
    ]
    for model, row in pivot.iterrows():
        lines.append(model + " & " + " & ".join(f"{v:.1f}" for v in row.values) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]

    _save_table("\n".join(lines), "table2_tariff_generalization.tex")
    print("\n--- Table 2 preview ---")
    print(pivot.to_string())


# ── Helpers ───────────────────────────────────────────────────────────────────
def _save(fig, name: str):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        path = FIGURES_DIR / f"{name}.{ext}"
        fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {FIGURES_DIR / name}.png/.pdf")


def _save_table(content: str, filename: str):
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLES_DIR / filename
    path.write_text(content)
    print(f"  Saved {path}")


def main():
    if not RESULTS_CSV.exists():
        print(f"No results found at {RESULTS_CSV}. Run experiments first.")
        sys.exit(1)

    df = load_results()
    print(f"Loaded {len(df)} rows from {RESULTS_CSV}")
    print(f"Models: {sorted(df['model_label'].unique())}")
    print(f"Runs per model: {df.groupby('model_label').size().to_dict()}")

    print("\nGenerating figures...")
    fig_energy_savings(df)
    fig_oracle_gap(df)
    fig_cost_efficiency(df)
    fig_tariff_heatmap(df)
    fig_breakeven(df)

    print("\nGenerating LaTeX tables...")
    table_model_comparison(df)
    table_tariff_generalization(df)

    print(f"\nAll outputs → {FIGURES_DIR.parent}/")


if __name__ == "__main__":
    main()
