"""
Leadership-facing summary figures — simple, single-message charts for a
non-technical audience, distinct from the detailed Stage 6 figures.
Written to /output/figures/leadership_summary/<task>/ for each of the 3
tasks (ceo, phipa, supervisor).

F1 is not computed anywhere else in this harness (EVALUATION_PLAN.md 1.6
lists it as secondary, "included as requested" but not a primary metric) --
this script computes it here: point estimate = harmonic mean of the
already-computed precision/recall point estimates, and a bootstrap
distribution (1000 resamples) for the box plot, by resampling the same
underlying recall/precision populations used everywhere else in this harness.

All charts use MS Copilot Agent's Run 1 only, matching every other cross-
system number in this project (EVALUATION_PLAN.md 1.6 run-scoping note).

PHIPA and Supervisor have far fewer gold items than CEO (6 and 5 rows total,
vs. 248) -- some systems returned literally 0 items for PHIPA (Claude,
Perplexity), which makes precision/F1 undefined (0/0), not 0 and not 1. This
script marks those cases explicitly ("no items returned") rather than
silently defaulting to a misleading number.

Figures (per task):
  1. recall_vs_specificity.png/pdf    -- dual-axis bar
  2. f1_boxplot.png/pdf               -- bootstrap F1 distribution per system
  3. four_metrics_grouped_bar.png/pdf -- recall / precision / F1 / hallucination
  4. headline_recall_ranking.png/pdf  -- single-metric, sorted, big chart
  5. hallucination_risk.png/pdf       -- single-metric risk chart, that task only

TASK_LABELS below controls the human-readable task name used in titles/captions.
"""

import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figstyle import SYSTEM_COLORS, SYSTEM_ORDER, clean_axes, savefig  # noqa: E402
from match import load_gold  # noqa: E402
from score import build_records  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_DIR = os.path.join(ROOT, "output", "scores")
BASE_OUT_DIR = os.path.join(ROOT, "output", "figures", "leadership_summary")

TASK_LABELS = {"ceo": "CEO task", "phipa": "PHIPA task", "supervisor": "Supervisor task"}

with open(os.path.join(SCORES_DIR, "metrics.json"), encoding="utf-8") as f:
    M = json.load(f)

random.seed(42)
N_BOOTSTRAP = 1000


def write_caption(out_dir, name, text):
    with open(os.path.join(out_dir, f"{name}_caption.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def write_csv(out_dir, name, header, rows):
    with open(os.path.join(out_dir, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def harmonic_mean(p, r):
    if p is None or r is None or (p + r) == 0:
        return None
    return 2 * p * r / (p + r)


# ---------------------------------------------------------------- FIGURE 1
def figure_recall_vs_specificity(task, out_dir):
    label = TASK_LABELS[task]
    fig, ax1 = plt.subplots(figsize=(8, 5))
    x = np.arange(len(SYSTEM_ORDER))
    width = 0.35

    recalls = [M["systems"][s]["recall"][task]["overall"]["point"] for s in SYSTEM_ORDER]
    spec_raw = [M["systems"][s]["specificity"][task]["mean"] for s in SYSTEM_ORDER]
    spec_scaled = [v / 3.0 if v is not None else 0 for v in spec_raw]
    recalls_plot = [v if v is not None else 0 for v in recalls]

    ax1.bar(x - width / 2, recalls_plot, width, color="#0072B2", edgecolor="#333333", linewidth=0.5, label="Recall")
    ax1.bar(x + width / 2, spec_scaled, width, color="#E69F00", edgecolor="#333333", linewidth=0.5, label="Specificity (scaled)")
    for i, v in enumerate(spec_raw):
        if v is None:
            ax1.annotate("no data", (i + width / 2, 0.02), rotation=90, fontsize=7, ha="center", color="#777777")

    ax1.set_xticks(x)
    ax1.set_xticklabels(SYSTEM_ORDER, rotation=15, ha="right")
    ax1.set_ylabel("Recall  (0-1 scale)")
    ax1.set_ylim(0, 1)
    clean_axes(ax1)

    ax2 = ax1.twinx()
    ax2.set_ylim(0, 3)
    ax2.set_ylabel("Specificity  (0-3 scale)")
    ax2.spines["top"].set_visible(False)

    ax1.set_title(f"How much did each system find, and how specific were its claims?\n{label}")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "recall_vs_specificity"))

    write_csv(
        out_dir, "recall_vs_specificity",
        ["system", "recall", "specificity_mean_0_3"],
        [[s, recalls[i], spec_raw[i]] for i, s in enumerate(SYSTEM_ORDER)],
    )
    write_caption(
        out_dir, "recall_vs_specificity",
        f"Recall (how much of the real, gold-verified activity each system found, {label}) "
        "next to specificity (how precise/checkable its claims were on average, 0-3 "
        "scale, shown scaled onto the same 0-1 axis with the true 0-3 scale on the "
        "right). 'no data' means that system returned zero matched items for this task "
        "(no specificity score is possible). "
        + ("PHIPA/Supervisor have very few gold rows (6 and 5 total) -- treat these "
           "as illustrative, not statistically robust, unlike the CEO-task version of "
           "this chart." if task != "ceo" else
           "MS Copilot Agent uses Run 1 only, matching every other system's single-run basis.")
    )


# ---------------------------------------------------------------- FIGURE 2 (F1 box plot)
def bootstrap_recall_distribution(matched_ids, in_scope_ids, seed):
    gold_list = list(in_scope_ids)
    rng = random.Random(seed)
    out = []
    for _ in range(N_BOOTSTRAP):
        if not gold_list:
            out.append(0.0)
            continue
        idxs = [rng.randrange(len(gold_list)) for _ in range(len(gold_list))]
        resampled = [gold_list[i] for i in idxs]
        hit = sum(1 for g in resampled if g in matched_ids)
        out.append(hit / len(resampled))
    return out


def bootstrap_precision_distribution(records_for_system_task, seed):
    denom_records = [r for r in records_for_system_task if r["bucket"] in ("TP", "A", "B", "C")]
    if not denom_records:
        return None  # undefined, not 0 and not 1 -- caller must handle
    rng = random.Random(seed + 1)
    out = []
    for _ in range(N_BOOTSTRAP):
        idxs = [rng.randrange(len(denom_records)) for _ in range(len(denom_records))]
        resampled = [denom_records[i] for i in idxs]
        num = sum(1 for r in resampled if r["bucket"] in ("TP", "A"))
        out.append(num / len(resampled))
    return out


def figure_f1_boxplot(task, out_dir):
    label = TASK_LABELS[task]
    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    records = build_records(gold_by_id, restrict_copilot_run1=True)
    in_scope_ids = {g["gold_item_id"] for g in gold_items if g["task"] == task and g["in_scope"] == "TRUE"}

    box_data = []
    box_positions = []
    no_data_systems = []
    zero_variance = []
    f1_summary_rows = []
    for i, s in enumerate(SYSTEM_ORDER):
        sys_records = [r for r in records if r["system"] == s and r["task"] == task]
        matched_ids = {r["gold_item_id"] for r in sys_records if r["bucket"] == "TP"}
        rec_dist = bootstrap_recall_distribution(matched_ids, in_scope_ids, hash(s + task) % 10000)
        prec_dist = bootstrap_precision_distribution(sys_records, hash(s + task) % 10000)

        point_rec = M["systems"][s]["recall"][task]["overall"]["point"]
        point_prec = M["systems"][s]["precision"][task]["point"]
        point_f1 = harmonic_mean(point_prec, point_rec)

        if prec_dist is None:
            no_data_systems.append(i)
            f1_summary_rows.append([s, point_rec, point_prec, point_f1, None, None, None])
            continue

        f1_dist = [harmonic_mean(p, r) or 0.0 for p, r in zip(prec_dist, rec_dist)]
        box_data.append(f1_dist)
        box_positions.append(i)
        f1_summary_rows.append([s, point_rec, point_prec, point_f1, float(np.median(f1_dist)), float(np.percentile(f1_dist, 2.5)), float(np.percentile(f1_dist, 97.5))])
        if max(f1_dist) - min(f1_dist) < 1e-9:
            zero_variance.append((i, f1_dist[0]))

    fig, ax = plt.subplots(figsize=(8, 5))
    if box_data:
        bp = ax.boxplot(
            box_data, positions=box_positions, widths=0.5, patch_artist=True,
            showfliers=False, medianprops={"color": "#222222", "linewidth": 1.5},
        )
        for patch, pos in zip(bp["boxes"], box_positions):
            patch.set_facecolor(SYSTEM_COLORS[SYSTEM_ORDER[pos]])
            patch.set_alpha(0.7)
            patch.set_edgecolor("#333333")
        for element in ("whiskers", "caps"):
            for line in bp[element]:
                line.set_color("#555555")
        ymax = max(max(d) for d in box_data) * 1.15
    else:
        ymax = 1.0

    for i in no_data_systems:
        ax.annotate("no items\nreturned", (i, ymax * 0.05), ha="center", fontsize=8, color="#777777")
    for i, val in zero_variance:
        va = "top" if val > ymax * 0.5 else "bottom"
        offset = -10 if va == "top" else 10
        ax.annotate("no variance\n(small n)", (i, val), xytext=(0, offset), textcoords="offset points", ha="center", va=va, fontsize=7, color="#555555")

    ax.set_xticks(range(len(SYSTEM_ORDER)))
    ax.set_xticklabels(SYSTEM_ORDER, rotation=15, ha="right")
    ax.set_xlim(-0.5, len(SYSTEM_ORDER) - 0.5)
    ax.set_ylabel("F1 score (bootstrap distribution)")
    ax.set_ylim(0, max(ymax, 0.05))
    ax.set_title(f"F1 score by system — {label}\n(bootstrap distribution, 1000 resamples)")
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "f1_boxplot"))

    write_csv(
        out_dir, "f1_boxplot",
        ["system", "recall_point", "precision_point", "f1_point", "f1_bootstrap_median", "f1_ci_low", "f1_ci_high"],
        f1_summary_rows,
    )
    write_caption(
        out_dir, "f1_boxplot",
        "F1 (harmonic mean of precision and recall) was not computed elsewhere in this "
        "harness -- EVALUATION_PLAN.md 1.6 lists it as secondary, since for a health-"
        "system tool a miss and a hallucination carry different costs that F1 averages "
        "away. Computed here for a leadership-friendly single summary number. Each box "
        "is a bootstrap distribution (1000 resamples) built from the same recall and "
        "precision populations used throughout this harness, resampled independently and "
        "combined via the harmonic mean -- not a true joint resampling, so treat the box "
        "width as an approximate, slightly conservative uncertainty band. 'No items "
        f"returned' means that system's precision (and therefore F1) is mathematically "
        f"undefined for {label} (0 returned items), not zero. "
        + ("PHIPA/Supervisor have very few gold rows -- treat these boxes as illustrative, "
           "not statistically robust." if task != "ceo" else
           f"{label}, MS Copilot Agent Run 1 only.")
    )


# ---------------------------------------------------------------- FIGURE 3
def figure_four_metrics_bar(task, out_dir):
    label = TASK_LABELS[task]
    metrics_names = ["Recall", "Precision", "F1", "Hallucination rate"]
    colors = ["#0072B2", "#009E73", "#CC79A7", "#D55E00"]

    values = {m: [] for m in metrics_names}
    cis = {m: [] for m in metrics_names}
    no_data_flags = []
    for s in SYSTEM_ORDER:
        rec = M["systems"][s]["recall"][task]["overall"]
        prec = M["systems"][s]["precision"][task]
        hall = M["systems"][s]["hallucination_rate"][task]
        f1 = harmonic_mean(prec["point"], rec["point"])
        no_data_flags.append(prec["point"] is None)

        values["Recall"].append(rec["point"] or 0)
        cis["Recall"].append((rec["point"] - rec["ci_low"], rec["ci_high"] - rec["point"]) if rec.get("ci_low") is not None and rec["point"] is not None else (0, 0))
        values["Precision"].append(prec["point"] or 0)
        cis["Precision"].append((prec["point"] - prec["ci_low"], prec["ci_high"] - prec["point"]) if prec.get("ci_low") is not None and prec["point"] is not None else (0, 0))
        values["F1"].append(f1 or 0)
        cis["F1"].append((0, 0))
        values["Hallucination rate"].append(hall["point"] or 0)
        cis["Hallucination rate"].append((hall["point"] - hall["ci_low"], hall["ci_high"] - hall["point"]) if hall.get("ci_low") is not None and hall["point"] is not None else (0, 0))

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(SYSTEM_ORDER))
    width = 0.2
    rows = []
    for i, m in enumerate(metrics_names):
        offset = (i - 1.5) * width
        lo = [c[0] for c in cis[m]]
        hi = [c[1] for c in cis[m]]
        ax.bar(x + offset, values[m], width, yerr=[lo, hi] if any(lo) or any(hi) else None, capsize=2,
               color=colors[i], edgecolor="#333333", linewidth=0.4, label=m)
        for si, s in enumerate(SYSTEM_ORDER):
            rows.append([s, m, values[m][si]])

    for i, flag in enumerate(no_data_flags):
        if flag:
            ax.annotate("no items\nreturned", (i, 0.05), ha="center", fontsize=7, color="#777777")

    ax.set_xticks(x)
    ax.set_xticklabels(SYSTEM_ORDER, rotation=15, ha="right")
    ax.set_ylabel("Score (0-1)")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"The whole picture at once — {label}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4)
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "four_metrics_grouped_bar"))

    write_csv(out_dir, "four_metrics_grouped_bar", ["system", "metric", "value"], rows)
    write_caption(
        out_dir, "four_metrics_grouped_bar",
        f"All four headline metrics side by side, {label}, MS Copilot Agent Run 1 only. "
        "Recall/Precision/Hallucination-rate error bars are bootstrap 95% CIs (1000 "
        "resamples) where computable; F1 has no error bar here (point-estimate harmonic "
        "mean -- see the f1_boxplot chart in this same folder for F1's bootstrap "
        "distribution). 'No items returned' marks a system with 0 returned items for "
        f"this task, where Precision/F1 are undefined, not zero. "
        + ("PHIPA/Supervisor have very few gold rows -- treat as illustrative, not "
           "statistically robust." if task != "ceo" else "")
    )


# ---------------------------------------------------------------- FIGURE 4
def figure_headline_recall(task, out_dir):
    label = TASK_LABELS[task]
    data = [(s, M["systems"][s]["recall"][task]["overall"]) for s in SYSTEM_ORDER]
    data.sort(key=lambda x: -(x[1]["point"] or 0))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(data))
    points = [d[1]["point"] or 0 for d in data]
    los = [(d[1]["point"] - d[1]["ci_low"]) if d[1].get("ci_low") is not None and d[1]["point"] is not None else 0 for d in data]
    his = [(d[1]["ci_high"] - d[1]["point"]) if d[1].get("ci_high") is not None and d[1]["point"] is not None else 0 for d in data]
    colors = [SYSTEM_COLORS[d[0]] for d in data]

    ax.barh(y, points, xerr=[los, his], capsize=3, color=colors, edgecolor="#333333", linewidth=0.5)
    for i, (s, d) in enumerate(data):
        label_x = (d["point"] or 0) + his[i]
        ax.annotate(f"{(d['point'] or 0)*100:.0f}%", (label_x, i), xytext=(8, 0), textcoords="offset points", va="center", fontsize=10)

    ax.set_yticks(y)
    ax.set_yticklabels([d[0] for d in data])
    ax.invert_yaxis()
    ax.set_xlabel(f"Share of real events found ({label})")
    ax.set_xlim(0, 1)
    ax.set_title("Headline: how much did each system actually find?")
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "headline_recall_ranking"))

    write_csv(out_dir, "headline_recall_ranking", ["system", "recall", "ci_low", "ci_high"], [[d[0], d[1]["point"], d[1].get("ci_low"), d[1].get("ci_high")] for d in data])
    write_caption(
        out_dir, "headline_recall_ranking",
        f"The single number leadership usually wants first: of the real, gold-verified "
        f"{label} events, what share did each system find? Sorted highest to lowest. "
        "Error bars are bootstrap 95% CIs -- overlapping bars mean this dataset cannot "
        "statistically distinguish those systems; see RESULTS_SUMMARY.md section 1 for "
        "the CEO-task pairwise overlap analysis before treating any ranking as a "
        "confident ordering. MS Copilot Agent uses Run 1 only. "
        + ("PHIPA has only 3 in-scope gold rows and Supervisor only 4 -- with n this "
           "small, a single extra or missed item swings the percentage by 25-33 points; "
           "treat these two task versions as directional, not precise." if task != "ceo" else "")
    )


# ---------------------------------------------------------------- FIGURE 5
def figure_hallucination_risk(task, out_dir):
    label = TASK_LABELS[task]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(SYSTEM_ORDER))
    points = []
    rows = []
    no_data = []
    for s in SYSTEM_ORDER:
        h = M["systems"][s]["hallucination_rate"][task]
        no_data.append(h["n"] == 0)
        p = h["point"] if h["point"] is not None else 0
        points.append(p)
        rows.append([s, h["bucket_B"], h["n"], h["point"]])

    ax.bar(x, points, color="#D55E00", edgecolor="#333333", linewidth=0.5)
    for i, p in enumerate(points):
        if no_data[i]:
            ax.annotate("no items\nreturned", (i, 0.01), ha="center", fontsize=8, color="#777777")
        else:
            ax.annotate(f"{p*100:.0f}%", (i, p), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels(SYSTEM_ORDER, rotation=15, ha="right")
    ax.set_ylabel(f"Hallucination rate ({label})")
    ax.set_ylim(0, max(0.05, max(points) * 1.4 if points else 0.05))
    ax.set_title("Risk check: how often did each system make something up?")
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "hallucination_risk"))

    write_csv(out_dir, "hallucination_risk", ["system", "bucket_B_count", "total_returned", "hallucination_rate"], rows)
    write_caption(
        out_dir, "hallucination_risk",
        f"Share of everything each system returned for {label} that was a confirmed "
        "fabrication (bucket B -- a named person/event with no corroborating source "
        "anywhere, verified by hand). This is the risk-focused companion to the recall "
        "chart: a system can find a lot (high recall) while still being safe (low "
        "hallucination), or vice versa. 'No items returned' means the rate is undefined "
        "(0/0), not necessarily safe. MS Copilot Agent uses Run 1 only -- a confirmed "
        "CEO-task fabrication in a later run (Brenda Donnelly, Run 4) is not counted "
        "here or anywhere in this project's cross-system numbers; see RESULTS_SUMMARY.md."
    )


def run_task(task):
    out_dir = os.path.join(BASE_OUT_DIR, task)
    os.makedirs(out_dir, exist_ok=True)
    figure_recall_vs_specificity(task, out_dir)
    print(f"[{task}] recall_vs_specificity done")
    figure_f1_boxplot(task, out_dir)
    print(f"[{task}] f1_boxplot done")
    figure_four_metrics_bar(task, out_dir)
    print(f"[{task}] four_metrics_grouped_bar done")
    figure_headline_recall(task, out_dir)
    print(f"[{task}] headline_recall_ranking done")
    figure_hallucination_risk(task, out_dir)
    print(f"[{task}] hallucination_risk done")


def main():
    for task in ("ceo", "phipa", "supervisor"):
        run_task(task)


if __name__ == "__main__":
    main()
