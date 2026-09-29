"""
Figure: Specificity (substitute for citation validity this evaluation round,
see EVALUATION_PLAN.md 1.4a). One bar per system, segments = specificity
scores 0/1/2/3 (0-3 rubric: exact date + named non-generic source + role
stated), aggregated across all matched (TP) items in all 3 tasks, using
Run 1 only for every system (MS Copilot Agent included, per the run-scoping
rule -- see 1.6 note).

Writes:
  /output/figures/specificity.png (300 dpi)
  /output/figures/specificity.pdf (vector)
  /output/figures/specificity.csv (underlying data)
  /output/figures/specificity_caption.txt
"""

import csv
import os
import sys
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match import load_gold  # noqa: E402
from score import SYSTEMS, build_records, specificity_score  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGURES_DIR = os.path.join(ROOT, "output", "figures")

# Colourblind-safe palette (Okabe-Ito), score 0 (worst) -> 3 (best)
SCORE_COLORS = {
    0: "#D55E00",  # vermillion
    1: "#E69F00",  # orange
    2: "#56B4E9",  # sky blue
    3: "#009E73",  # bluish green
}


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)
    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    records = build_records(gold_by_id, restrict_copilot_run1=True)

    scores_by_system = defaultdict(list)
    for r in records:
        if r["bucket"] == "TP":
            scores_by_system[r["system"]].append(specificity_score(r["item"]))

    systems_ordered = [s for s in SYSTEMS if s in scores_by_system]
    counts_by_system = {s: Counter(scores_by_system[s]) for s in systems_ordered}
    means = {s: (sum(scores_by_system[s]) / len(scores_by_system[s])) for s in systems_ordered}
    ns = {s: len(scores_by_system[s]) for s in systems_ordered}

    with open(os.path.join(FIGURES_DIR, "specificity.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["system", "n_matched_items", "mean_specificity", "pct_score_0", "pct_score_1", "pct_score_2", "pct_score_3"])
        for s in systems_ordered:
            n = ns[s]
            pcts = [counts_by_system[s].get(k, 0) / n if n else 0 for k in (0, 1, 2, 3)]
            writer.writerow([s, n, round(means[s], 4)] + [round(p, 4) for p in pcts])

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(systems_ordered))
    bottoms = [0] * len(systems_ordered)
    for score in (0, 1, 2, 3):
        heights = [counts_by_system[s].get(score, 0) / ns[s] if ns[s] else 0 for s in systems_ordered]
        ax.bar(x, heights, bottom=bottoms, color=SCORE_COLORS[score], label=f"score {score}", edgecolor="white", linewidth=0.5)
        bottoms = [b + h for b, h in zip(bottoms, heights)]

    for i, s in enumerate(systems_ordered):
        ax.annotate(f"mean={means[s]:.2f}\n(n={ns[s]})", (i, 1.02), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(list(x))
    ax.set_xticklabels(systems_ordered, rotation=20, ha="right")
    ax.set_ylabel("Share of matched items")
    ax.set_ylim(0, 1.15)
    ax.set_title("Specificity of matched items by system\n(substitute for citation validity — see EVALUATION_PLAN.md 1.4a)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    fig.savefig(os.path.join(FIGURES_DIR, "specificity.png"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(FIGURES_DIR, "specificity.pdf"), bbox_inches="tight")
    plt.close(fig)

    caption = (
        "Figure: Specificity of matched items by system, all tasks combined "
        "(CEO + PHIPA + Supervisor), MS Copilot Agent Run 1 only (matching every "
        "other system's single-run basis; see EVALUATION_PLAN.md 1.6 run-scoping "
        f"note). n = {sum(ns.values())} matched (bucket TP) items total across "
        f"{len(systems_ordered)} systems.\n\n"
        "Specificity is a 0-3 score per matched item, one point each for: (1) an "
        "exact YYYY-MM-DD date, (2) a named, non-generic citation source, and "
        "(3) a stated role. It substitutes for citation validity in this "
        "evaluation round because the raw LLM/agent responses were not all "
        "copied with their citations intact during data collection (a "
        "collection-side gap, not a system-quality signal) — see "
        "EVALUATION_PLAN.md 1.4 addendum, dated 2026-08-31.\n\n"
        "Limitation: specificity measures how checkable a claim LOOKS, not "
        "whether it is actually correct or whether any citation given actually "
        "resolves and supports it — it is not a substitute for real citation "
        "validation, which this round does not have complete enough data to "
        "compute."
    )
    with open(os.path.join(FIGURES_DIR, "specificity_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    print("Wrote specificity.png, specificity.pdf, specificity.csv, specificity_caption.txt to", FIGURES_DIR)
    for s in systems_ordered:
        print(f"  {s}: mean={means[s]:.2f} n={ns[s]}")


if __name__ == "__main__":
    main()
