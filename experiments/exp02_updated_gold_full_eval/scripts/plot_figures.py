"""
Stage 6 — figures. Reads /output/scores/metrics.json (written by score.py)
plus the raw records (via build_records) for figures that need per-item
data not already aggregated into metrics.json. Writes each figure as
.png (300dpi) + .pdf, its underlying data as .csv, and a .txt caption,
all to /output/figures/.
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figstyle import SYSTEM_COLORS, SYSTEM_ORDER, TASK_MARKERS, clean_axes, savefig  # noqa: E402
from match import load_gold, split_gold_name_or_issue  # noqa: E402
from score import build_records  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_DIR = os.path.join(ROOT, "output", "scores")
FIGURES_DIR = os.path.join(ROOT, "output", "figures")
CEO_TIERS = ["A - dated announcement", "B - directory confirmed, undated", "C - inferred / approximate date"]
TIER_LABELS = {"A - dated announcement": "Tier A", "B - directory confirmed, undated": "Tier B", "C - inferred / approximate date": "Tier C"}

with open(os.path.join(SCORES_DIR, "metrics.json"), encoding="utf-8") as f:
    METRICS = json.load(f)


def write_caption(name, text):
    with open(os.path.join(FIGURES_DIR, f"{name}_caption.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def write_csv(name, header, rows):
    with open(os.path.join(FIGURES_DIR, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- FIGURE 1
def figure1():
    systems = SYSTEM_ORDER
    tiers = CEO_TIERS
    x = np.arange(len(systems))
    width = 0.25
    rows = []
    for tier in tiers:
        for s in systems:
            d = METRICS["systems"][s]["recall"]["ceo"][tier]
            rows.append([s, tier, d["point"], d["ci_low"], d["ci_high"], d["n_gold"]])

    fig, ax = plt.subplots(figsize=(8, 4.5))
    tier_shades = {"A - dated announcement": 0.95, "B - directory confirmed, undated": 0.6, "C - inferred / approximate date": 0.3}
    for ti, tier in enumerate(tiers):
        vals, los, his = [], [], []
        for s in systems:
            d = METRICS["systems"][s]["recall"]["ceo"][tier]
            vals.append(d["point"] or 0)
            los.append((d["point"] - d["ci_low"]) if d["point"] is not None and d["ci_low"] is not None else 0)
            his.append((d["ci_high"] - d["point"]) if d["point"] is not None and d["ci_high"] is not None else 0)
        offset = (ti - 1) * width
        color = "#0072B2"
        alpha = tier_shades[tier]
        ax.bar(x + offset, vals, width, yerr=[los, his], capsize=2, color=color, alpha=alpha,
               edgecolor="#333333", linewidth=0.5, label=TIER_LABELS[tier])

    ax.set_xticks(x)
    ax.set_xticklabels(systems, rotation=15, ha="right")
    ax.set_ylabel("Recall")
    ax.set_ylim(0, 1)
    ax.set_title("Recall by confidence tier — CEO task")
    ax.legend(loc="upper right")
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig1_recall_by_tier"))

    write_csv("fig1_recall_by_tier", ["system", "tier", "recall", "ci_low", "ci_high", "n_gold"], rows)
    write_caption(
        "fig1_recall_by_tier",
        "Figure 1: Recall by confidence tier, CEO task only. Tier A = dated announcement "
        "(n=175 gold rows), Tier B = directory-confirmed but undated (n=44), Tier C = "
        "inferred/approximate date (n=27). Error bars are bootstrap 95% CIs (1000 "
        "resamples). MS Copilot Agent uses Run 1 only, matching every other system's "
        "single-run basis. Limitation: recall is computed against a gold set that is "
        "itself partly derived from these systems' own outputs (see Figure 3 for the "
        "circularity control) and n is small per tier, so CIs are wide.",
    )


# ---------------------------------------------------------------- FIGURE 2
def figure2():
    fig, ax = plt.subplots(figsize=(8, 6))
    rows = []
    for task in ("ceo", "phipa", "supervisor"):
        for s in SYSTEM_ORDER:
            rec = METRICS["systems"][s]["recall"][task]["overall"]["point"]
            prec = METRICS["systems"][s]["precision"][task]["point"]
            if rec is None or prec is None:
                continue
            ax.scatter(rec, prec, marker=TASK_MARKERS[task], s=70, color=SYSTEM_COLORS[s],
                       edgecolor="#333333", linewidth=0.5, zorder=3)
            rows.append([s, task, rec, prec])

    # iso-F1 contours
    r = np.linspace(0.001, 1, 200)
    for f1 in (0.2, 0.4, 0.6, 0.8):
        with np.errstate(divide="ignore", invalid="ignore"):
            p = (f1 * r) / (2 * r - f1)
        p = np.where((p > 0) & (p <= 1), p, np.nan)
        ax.plot(r, p, color="#bbbbbb", linewidth=0.8, zorder=1)
        valid = ~np.isnan(p)
        if valid.any():
            # label partway along the visible curve, not at its endpoint,
            # so it doesn't collide with data points near recall=1
            mid_idx = np.where(valid)[0]
            mid_idx = mid_idx[len(mid_idx) // 3]
            ax.annotate(f"F1={f1}", (r[mid_idx], p[mid_idx]), fontsize=7, color="#999999", ha="center", va="bottom")

    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=SYSTEM_COLORS[s],
                       markeredgecolor="#333333", markersize=8, label=s) for s in SYSTEM_ORDER]
    handles.append(Line2D([0], [0], color="none", label=""))  # spacer
    handles += [Line2D([0], [0], marker=TASK_MARKERS[t], color="none", markerfacecolor="#888888",
                        markeredgecolor="#333333", markersize=8, label=t) for t in ("ceo", "phipa", "supervisor")]
    leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
    fig.savefig_extra_artists = [leg]

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.set_title("Precision vs recall")
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig2_precision_recall"))

    write_csv("fig2_precision_recall", ["system", "task", "recall", "precision"], rows)
    write_caption(
        "fig2_precision_recall",
        "Figure 2: Precision vs recall, one point per system per task (n=15 points: 5 "
        "systems x 3 tasks). Grey diagonal lines are iso-F1 contours (F1=0.2/0.4/0.6/0.8). "
        "Precision is computed after adjudication, excluding buckets D and E and matches "
        "to out-of-scope gold rows (section 1.6). MS Copilot Agent uses Run 1 only. "
        "Precision is uniformly high across systems in this dataset because every system "
        "under test rarely names a person/event with no basis in reality within its "
        "extracted, in-scope claims -- the real differentiator here is recall, not "
        "precision; read this figure alongside Figure 1.",
    )


# ---------------------------------------------------------------- FIGURE 3
def figure3():
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    rows = []
    for i, s in enumerate(SYSTEM_ORDER):
        ov = METRICS["systems"][s]["recall"]["ceo"]["overall"]["point"]
        ind = METRICS["systems"][s]["recall"]["ceo"]["independent"]["point"]
        if ov is None or ind is None:
            continue
        ax.plot([0, 1], [i, i], color="#dddddd", linewidth=6, solid_capstyle="round", zorder=1)
        ax.plot([ind, ov], [i, i], color="#999999", linewidth=1.5, zorder=2)
        ax.scatter([ov], [i], color=SYSTEM_COLORS[s], s=90, zorder=3, label="Overall" if i == 0 else None,
                   marker="o", edgecolor="#333333", linewidth=0.6)
        ax.scatter([ind], [i], facecolor="white", s=90, zorder=3, label="Independent subset" if i == 0 else None,
                   marker="o", edgecolor=SYSTEM_COLORS[s], linewidth=2)
        rows.append([s, ov, ind])

    ax.set_yticks(range(len(SYSTEM_ORDER)))
    ax.set_yticklabels(SYSTEM_ORDER)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Recall (CEO task)")
    ax.set_title("Recall: overall vs independent-provenance subset")
    ax.legend(loc="lower right")
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig3_recall_independent"))

    write_csv("fig3_recall_independent", ["system", "recall_overall", "recall_independent"], rows)
    write_caption(
        "fig3_recall_independent",
        "Figure 3: Recall on the full CEO gold set (filled dot) vs recall restricted to "
        "the independent-provenance subset (open dot) -- gold rows whose status is "
        "'NEWLY ADDED - please verify' (section 1.10), i.e. not sourced from a system "
        "under test's own output. This is the circularity control: every system's "
        "independent-subset recall is lower than its overall recall, consistent with "
        "some of each system's 'overall' credit coming from gold rows that entered the "
        "dataset because a system (possibly the same one) surfaced them. Limitation: the "
        "'NEWLY ADDED' status only exists on the CEO sheet -- PHIPA and Supervisor have "
        "no provenance tag and are not shown here.",
    )


# ---------------------------------------------------------------- FIGURE 4
ERROR_CATS = ["fabricated_person_or_event", "wrong_role", "wrong_date", "organisational_confusion", "stale"]
ERROR_LABELS = {
    "fabricated_person_or_event": "Fabricated",
    "wrong_role": "Wrong role",
    "wrong_date": "Wrong date",
    "organisational_confusion": "Org. confusion",
    "stale": "Stale",
}
ERROR_COLORS = ["#D55E00", "#E69F00", "#56B4E9", "#009E73", "#999999"]


def figure4():
    fig, ax = plt.subplots(figsize=(8, 4))
    rows = []
    totals = {}
    for s in SYSTEM_ORDER:
        counts = Counter()
        for task in ("ceo", "phipa", "supervisor"):
            for cat, n in METRICS["systems"][s]["error_taxonomy"][task].items():
                counts[cat] += n
        totals[s] = counts

    y = np.arange(len(SYSTEM_ORDER))
    left = np.zeros(len(SYSTEM_ORDER))
    for cat, color in zip(ERROR_CATS, ERROR_COLORS):
        vals = []
        for s in SYSTEM_ORDER:
            total = sum(totals[s].values())
            share = (totals[s].get(cat, 0) / total) if total else 0
            vals.append(share)
            rows.append([s, cat, totals[s].get(cat, 0), total, share])
        ax.barh(y, vals, left=left, color=color, edgecolor="white", linewidth=0.5, label=ERROR_LABELS[cat])
        left += np.array(vals)

    ax.set_yticks(y)
    ax.set_yticklabels(SYSTEM_ORDER)
    ax.set_xlabel("Share of tagged errors")
    ax.set_xlim(0, 1)
    ax.set_title("Error taxonomy composition (all tasks combined)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=5)
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig4_error_taxonomy"))

    write_csv("fig4_error_taxonomy", ["system", "category", "count", "total_tagged", "share"], rows)
    n_note = ", ".join(f"{s} n={sum(totals[s].values())}" for s in SYSTEM_ORDER)
    write_caption(
        "fig4_error_taxonomy",
        "Figure 4: Error taxonomy composition, all 3 tasks combined, normalised to 100% "
        "per system. Applied to matched (TP) items with a field-level role or date error, "
        "plus every bucket B (fabricated) and bucket C (wrong attribution) item. "
        f"{n_note}. 'Unsupported citation' (the plan's 6th category) is not shown -- "
        "citation validity was not computed this round (see EVALUATION_PLAN.md 1.4 "
        "addendum). 'Stale' is not automatically detected this round (always 0) and "
        "should be read as not-yet-measured, not as zero occurrences.",
    )


# ---------------------------------------------------------------- FIGURE 5 (specificity)
# Reuses plot_specificity.py, restyled to match this file's system colour
# palette and simpler chart conventions.
def figure5():
    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    records = build_records(gold_by_id, restrict_copilot_run1=True)

    from score import specificity_score

    scores_by_system = defaultdict(list)
    for r in records:
        if r["bucket"] == "TP":
            scores_by_system[r["system"]].append(specificity_score(r["item"]))

    systems = [s for s in SYSTEM_ORDER if s in scores_by_system]
    counts_by_system = {s: Counter(scores_by_system[s]) for s in systems}
    means = {s: sum(scores_by_system[s]) / len(scores_by_system[s]) for s in systems}
    ns = {s: len(scores_by_system[s]) for s in systems}

    score_shades = {0: 0.25, 1: 0.45, 2: 0.7, 3: 1.0}
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(systems))
    bottoms = np.zeros(len(systems))
    rows = []
    for score in (0, 1, 2, 3):
        heights = np.array([counts_by_system[s].get(score, 0) / ns[s] if ns[s] else 0 for s in systems])
        ax.bar(x, heights, bottom=bottoms, color="#0072B2", alpha=score_shades[score],
               edgecolor="#333333", linewidth=0.4, label=f"score {score}")
        bottoms += heights
        for s, h in zip(systems, heights):
            rows.append([s, score, counts_by_system[s].get(score, 0), ns[s], h])

    for i, s in enumerate(systems):
        ax.annotate(f"{means[s]:.2f}", (i, 1.02), ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(systems, rotation=15, ha="right")
    ax.set_ylabel("Share of matched items")
    ax.set_ylim(0, 1.12)
    ax.set_title("Specificity of matched items (substitute for citation validity)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4)
    clean_axes(ax)
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig5_specificity"))

    write_csv("fig5_specificity", ["system", "score", "count", "n", "share"], rows)
    write_caption(
        "fig5_specificity",
        "Figure 5: Specificity of matched items by system, all tasks combined, MS Copilot "
        "Agent Run 1 only. Numbers above each bar are the mean specificity score (0-3). "
        "Specificity substitutes for citation validity this round because the raw "
        "responses were not all copied with citations intact during data collection -- "
        "see EVALUATION_PLAN.md 1.4 addendum and 1.4a. It scores whether a claim LOOKS "
        "checkable (exact date, named source, stated role), not whether it is actually "
        "correct or whether any citation given resolves and supports it.",
    )


# ---------------------------------------------------------------- FIGURE 6
def figure6():
    fields = ["role", "date", "direction"]
    field_labels = {"role": "Role", "date": "Date", "direction": "Direction"}
    acc = {}
    rows = []
    for s in SYSTEM_ORDER:
        acc[s] = {}
        for field in fields:
            correct = sum(METRICS["systems"][s]["field_accuracy"][task][field]["correct"] for task in ("ceo", "phipa", "supervisor"))
            n = sum(METRICS["systems"][s]["field_accuracy"][task][field]["n"] for task in ("ceo", "phipa", "supervisor"))
            a = correct / n if n else None
            acc[s][field] = a
            rows.append([s, field, correct, n, a])

    matrix = np.array([[acc[s][f] if acc[s][f] is not None else np.nan for f in fields] for s in SYSTEM_ORDER])

    fig, ax = plt.subplots(figsize=(5.5, 4))
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(fields)))
    ax.set_xticklabels([field_labels[f] for f in fields])
    ax.set_yticks(range(len(SYSTEM_ORDER)))
    ax.set_yticklabels(SYSTEM_ORDER)
    for i in range(len(SYSTEM_ORDER)):
        for j in range(len(fields)):
            v = matrix[i, j]
            if np.isnan(v):
                continue
            color = "white" if v > 0.6 else "#222222"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=color, fontsize=9)
    ax.set_title("Field accuracy (matched items, all tasks combined)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.06, label="Accuracy")
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig6_field_accuracy"))

    write_csv("fig6_field_accuracy", ["system", "field", "correct", "n", "accuracy"], rows)
    write_caption(
        "fig6_field_accuracy",
        "Figure 6: Field accuracy for role, date, and direction, all 3 tasks combined, "
        "conditional on entity match (matched/TP items only -- a system gets no credit or "
        "penalty here for items it never matched to gold). Date accuracy applies the "
        "documented tolerances in EVALUATION_PLAN.md 1.3 (multi-date announcements, "
        "month/year-precision gold rows). n varies by cell -- see the underlying CSV; "
        "cells are excluded from the denominator only when the GOLD field itself is "
        "blank, not when the system's field is blank (a blank system field where gold "
        "has a value counts as incorrect).",
    )


# ---------------------------------------------------------------- FIGURE 7
def figure7():
    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    all_records = build_records(gold_by_id, restrict_copilot_run1=False)
    copilot = [r for r in all_records if r["system"] == "MS Copilot Agent" and r["task"] == "ceo"]

    ceo_in_scope_ids = sorted({g["gold_item_id"] for g in gold_items if g["task"] == "ceo" and g["in_scope"] == "TRUE"},
                               key=lambda x: int(x[1:]))
    matched_ids_ever = {r["gold_item_id"] for r in copilot if r["bucket"] == "TP"}
    gold_rows_touched = [g for g in ceo_in_scope_ids if g in matched_ids_ever]

    presence = np.zeros((len(gold_rows_touched), 5), dtype=int)
    gid_index = {g: i for i, g in enumerate(gold_rows_touched)}
    for r in copilot:
        if r["bucket"] == "TP" and r["gold_item_id"] in gid_index:
            presence[gid_index[r["gold_item_id"]], r["run_number"] - 1] = 1

    fig, axes = plt.subplots(1, 2, figsize=(10, 7), gridspec_kw={"width_ratios": [1, 1.3]})

    ax = axes[0]
    ax.imshow(presence, cmap="Greys", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"R{i+1}" for i in range(5)])
    # too many gold items to label every row legibly -- show every 5th
    n = len(gold_rows_touched)
    tick_idx = list(range(0, n, 5))
    ax.set_yticks(tick_idx)
    ax.set_yticklabels([gold_rows_touched[i] for i in tick_idx], fontsize=6)
    ax.set_title("A: item presence (CEO)", fontsize=10)
    ax.set_xlabel("Run")

    def entity_key(r):
        if r["gold_item_id"]:
            return "G:" + r["gold_item_id"]
        from match import name_variants
        item = r["item"]
        nv = sorted(name_variants(item.get("person_or_issue") or ""))
        key_name = nv[0] if nv else (item.get("person_or_issue") or "")
        return f"U:{key_name}@{r['hospital']}@{item.get('direction')}"

    run_sets = {run: {entity_key(r) for r in copilot if r["run_number"] == run} for run in range(1, 6)}
    jac_matrix = np.zeros((5, 5))
    jac_rows = []
    for i in range(1, 6):
        for j in range(1, 6):
            a, b = run_sets[i], run_sets[j]
            union = a | b
            jac_matrix[i - 1, j - 1] = (len(a & b) / len(union)) if union else np.nan
            if i < j:
                jac_rows.append([i, j, jac_matrix[i - 1, j - 1]])

    ax2 = axes[1]
    im = ax2.imshow(jac_matrix, cmap="Blues", vmin=0, vmax=1)
    ax2.set_xticks(range(5))
    ax2.set_xticklabels([f"R{i+1}" for i in range(5)])
    ax2.set_yticks(range(5))
    ax2.set_yticklabels([f"R{i+1}" for i in range(5)])
    for i in range(5):
        for j in range(5):
            v = jac_matrix[i, j]
            color = "white" if v > 0.6 else "#222222"
            ax2.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color=color)
    ax2.set_title("B: pairwise Jaccard (CEO)", fontsize=10)
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.08)

    fig.suptitle(
        "MS Copilot Agent repeat-run consistency, Runs 1-5\nSINGLE-SYSTEM RELIABILITY, not a cross-system comparison",
        fontsize=11, y=1.04,
    )
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig7_copilot_consistency"))

    write_csv("fig7a_item_presence", ["gold_item_id"] + [f"run{i+1}" for i in range(5)],
              [[gold_rows_touched[i]] + list(presence[i]) for i in range(len(gold_rows_touched))])
    write_csv("fig7b_pairwise_jaccard", ["run_a", "run_b", "jaccard"], jac_rows)
    write_caption(
        "fig7_copilot_consistency",
        "Figure 7: MS Copilot Agent's own repeat-run consistency across its 5 CEO-task "
        f"runs. Panel A: presence of each of the {len(gold_rows_touched)} distinct "
        "in-scope CEO gold items Copilot matched in AT LEAST ONE of its 5 runs (rows), "
        "by run (columns) -- filled = returned that run. Panel B: pairwise Jaccard "
        "similarity of Copilot's full returned entity sets (gold-matched AND unmatched/"
        "hallucinated items both counted) between each pair of runs. THIS IS SINGLE-"
        "SYSTEM RELIABILITY, NOT A CROSS-SYSTEM COMPARISON -- every other system in this "
        "study has only 1 run and cannot be shown here. PHIPA and Supervisor tasks have "
        "far too few gold items (6 and 5 respectively) for a meaningful presence matrix "
        "and are not shown; see metrics.json 'consistency' for their Jaccard/stability "
        "numbers.",
    )


# ---------------------------------------------------------------- FIGURE 8
def figure8():
    tasks = ["ceo", "phipa", "supervisor"]
    metric_defs = [
        ("Recall", lambda s, t: METRICS["systems"][s]["recall"][t]["overall"]["point"]),
        ("Precision", lambda s, t: METRICS["systems"][s]["precision"][t]["point"]),
        ("Hallucination", lambda s, t: METRICS["systems"][s]["hallucination_rate"][t]["point"]),
        ("Specificity", lambda s, t: METRICS["systems"][s]["specificity"][t]["mean"]),
        ("Omission", lambda s, t: METRICS["systems"][s]["omission_rate"][t]["rate"]),
    ]

    n_rows = len(SYSTEM_ORDER) * len(tasks)
    fig, ax = plt.subplots(figsize=(12, 0.34 * n_rows + 1.0))
    ax.axis("off")

    col_labels = ["System", "Task"] + [m[0] for m in metric_defs]
    table_rows = []
    csv_rows = []
    for s in SYSTEM_ORDER:
        for t in tasks:
            row = [s, t]
            for label, fn in metric_defs:
                v = fn(s, t)
                if v is None:
                    row.append("--")
                elif label == "Specificity":
                    row.append(f"{v:.2f}")
                else:
                    row.append(f"{v:.2f}")
            table_rows.append(row)
            csv_rows.append(row)

    tbl = ax.table(cellText=table_rows, colLabels=col_labels, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.4)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if r == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#f2f2f2")
        else:
            cell.set_facecolor("white")

    ax.set_title("Per-task metric summary (Run 1 only for every system, incl. MS Copilot Agent)", pad=20)
    fig.tight_layout()
    savefig(fig, os.path.join(FIGURES_DIR, "fig8_metric_table"))

    write_csv("fig8_metric_table", col_labels, csv_rows)
    write_caption(
        "fig8_metric_table",
        "Figure 8 (supplementary): per-system, per-task summary of the five headline "
        "point-estimate metrics. Recall = overall recall (not independent-subset -- see "
        "Figure 3). Precision excludes buckets D/E and out-of-scope matches. "
        "Hallucination rate = bucket B / all returned items. Specificity is the 0-3 "
        "substitute metric for citation validity (1.4a). Omission rate = share of "
        "matched items with a required field blank. All values use Run 1 only, "
        "including MS Copilot Agent, for cross-system comparability (see 1.6 run-"
        "scoping note). '--' means the denominator was 0 for that cell.",
    )


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)
    figure1()
    print("figure 1 done")
    figure2()
    print("figure 2 done")
    figure3()
    print("figure 3 done")
    figure4()
    print("figure 4 done")
    figure5()
    print("figure 5 done")
    figure6()
    print("figure 6 done")
    figure7()
    print("figure 7 done")
    figure8()
    print("figure 8 done")


if __name__ == "__main__":
    main()
