"""
generate_report_visualizations.py
===================================
Generates 4 publication-quality charts for the manager's report:

SET 1 — Deterministic Evaluation (evaluation/)
  Vis 1A: Copilot Agent vs Commercial LLMs — Performance by Metric & Task
  Vis 1B: Copilot Prompt Run Comparison — Consistency across 5 runs

SET 2 — LLM-as-Judge Evaluation (evaluation_llm/)
  Vis 2A: Copilot Agent vs Commercial LLMs — All 7 Quality Metrics
  Vis 2B: Copilot vs Commercial LLMs — Qualitative Dimension Deep Dive
"""

import pathlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import warnings
warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE = pathlib.Path(__file__).resolve().parent.parent
DET_DIR  = BASE / "deterministic_pipeline" / "metrics"
LLM_DIR  = BASE / "llm_judge_pipeline" / "metrics"
OUT_DET  = BASE / "visualizations_report" / "deterministic"
OUT_LLM  = BASE / "visualizations_report" / "llm_judge"
OUT_DET.mkdir(parents=True, exist_ok=True)
OUT_LLM.mkdir(parents=True, exist_ok=True)

# ─── Style constants ─────────────────────────────────────────────────────────
BG       = "#0D1117"
PANEL_BG = "#161B22"
GRID_C   = "#21262D"
TEXT_W   = "#E6EDF3"
TEXT_DIM = "#8B949E"

MODEL_COLORS = {
    "MS Copilot Agent": "#58A6FF",   # blue
    "ChatGPT":          "#3FB950",   # green
    "Claude":           "#FFA657",   # orange
    "Gemini":           "#BC8CFF",   # purple
    "Perplexity":       "#FF7B72",   # red
}
TASK_COLORS = {
    "ceo":          "#58A6FF",
    "phipa":        "#3FB950",
    "supervisors":  "#FFA657",
}
TASK_LABELS = {"ceo": "CEO / Board", "phipa": "PHIPA", "supervisors": "Supervisors"}
MODELS_ORDER = ["MS Copilot Agent", "ChatGPT", "Claude", "Gemini", "Perplexity"]
COPILOT = "MS Copilot Agent"

def apply_dark_style(fig, axes_list):
    fig.patch.set_facecolor(BG)
    for ax in axes_list:
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=TEXT_W, labelsize=9)
        ax.xaxis.label.set_color(TEXT_DIM)
        ax.yaxis.label.set_color(TEXT_DIM)
        ax.title.set_color(TEXT_W)
        for spine in ax.spines.values():
            spine.set_color(GRID_C)
        ax.grid(True, color=GRID_C, linestyle="--", linewidth=0.5, alpha=0.8)
        ax.set_axisbelow(True)

def add_watermark(ax, text):
    ax.text(0.99, 0.01, text, transform=ax.transAxes,
            fontsize=7, color=TEXT_DIM, alpha=0.6,
            ha="right", va="bottom", style="italic")

# ════════════════════════════════════════════════════════════════════════════
# SET 1 — DETERMINISTIC
# ════════════════════════════════════════════════════════════════════════════

det_tool = pd.read_csv(DET_DIR / "tool_summary.csv")
det_hosp = pd.read_csv(DET_DIR / "hospital_summary.csv")

# ── VIS 1A: Copilot vs Commercial LLMs — Performance by Metric & Task ──────
print("Generating Vis 1A: Copilot vs LLMs — Deterministic...")

metrics_det = ["recall", "precision", "f1", "hallucination_rate"]
metric_labels_det = ["Recall", "Precision", "F1 Score", "Hallucination Rate"]
tasks = ["ceo", "phipa", "supervisors"]

fig = plt.figure(figsize=(20, 14), facecolor=BG)
fig.suptitle(
    "Visualization 1  ·  Copilot Agent vs Commercial LLMs — Deterministic Evaluation",
    color=TEXT_W, fontsize=16, fontweight="bold", y=0.98
)
sub_title = "Metrics: Recall · Precision · F1 Score · Hallucination Rate    |    Tasks: CEO/Board · PHIPA · Supervisors"
fig.text(0.5, 0.955, sub_title, color=TEXT_DIM, fontsize=10, ha="center")

gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.55, wspace=0.35,
                       left=0.06, right=0.97, top=0.93, bottom=0.09)

for row_idx, task in enumerate(tasks):
    task_df = det_tool[det_tool["task"] == task].copy()
    task_df = task_df.set_index("tool").reindex(MODELS_ORDER).reset_index()
    task_df.columns = ["model"] + list(task_df.columns[1:])

    for col_idx, (metric, mlabel) in enumerate(zip(metrics_det, metric_labels_det)):
        ax = fig.add_subplot(gs[row_idx, col_idx])
        apply_dark_style(fig, [ax])

        values = task_df[metric].fillna(0).values
        colors = [MODEL_COLORS.get(m, "#888") for m in task_df["model"]]
        edge_colors = ["#FFD700" if m == COPILOT else "#333" for m in task_df["model"]]
        edge_widths = [2.5 if m == COPILOT else 0.5 for m in task_df["model"]]

        bars = ax.bar(range(len(MODELS_ORDER)), values, color=colors,
                      edgecolor=edge_colors, linewidth=edge_widths,
                      width=0.65, zorder=3)

        # value labels
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                        f"{val:.2f}", ha="center", va="bottom",
                        color=TEXT_W, fontsize=7.5, fontweight="bold", zorder=5)

        ax.set_ylim(0, 1.18)
        ax.set_xticks(range(len(MODELS_ORDER)))
        ax.set_xticklabels(
            [m.replace("MS Copilot Agent", "Copilot").replace(" ", "\n") for m in MODELS_ORDER],
            fontsize=7.5, color=TEXT_W
        )
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.yaxis.set_tick_params(labelsize=8)

        # Row label (task) only on first column
        if col_idx == 0:
            ax.set_ylabel(TASK_LABELS[task], color=TASK_COLORS[task],
                          fontsize=11, fontweight="bold", labelpad=8)
        # Column label (metric) only on first row
        if row_idx == 0:
            ax.set_title(mlabel, color=TEXT_W, fontsize=11, fontweight="bold", pad=8)

        add_watermark(ax, "Ontario Health Evaluation")

# Legend
legend_handles = [
    mpatches.Patch(color=MODEL_COLORS[m],
                   label=m.replace("MS Copilot Agent","★ MS Copilot Agent"))
    for m in MODELS_ORDER
]
legend_handles.append(
    mpatches.Patch(facecolor="none", edgecolor="#FFD700", linewidth=2, label="← Copilot (gold border)")
)
fig.legend(handles=legend_handles, loc="lower center", ncol=6,
           facecolor=PANEL_BG, edgecolor=GRID_C, labelcolor=TEXT_W, fontsize=9,
           framealpha=0.9, bbox_to_anchor=(0.5, 0.01))

plt.savefig(OUT_DET / "Vis1A_Copilot_vs_LLMs_Deterministic.png",
            dpi=200, bbox_inches="tight", facecolor=BG)
plt.close()
print("  ✓ Saved Vis1A")


# ── VIS 1B: Copilot Run Comparison — Consistency across 5 runs ──────────────
print("Generating Vis 1B: Copilot Run Comparison — Deterministic...")

copilot_runs = det_hosp[det_hosp["tool"] == COPILOT].copy()
copilot_runs["run_number"] = copilot_runs["run_number"].astype(int)

run_agg = copilot_runs.groupby(["task", "run_number"])[
    ["recall", "precision", "f1"]
].mean().reset_index()

fig, axes = plt.subplots(1, 3, figsize=(18, 7), facecolor=BG)
fig.suptitle(
    "Visualization 2  ·  MS Copilot Agent — Prompt Run Consistency (5 Runs × 3 Tasks)",
    color=TEXT_W, fontsize=16, fontweight="bold", y=1.01
)
fig.text(0.5, 0.97, "Each run uses identical prompts — variance reveals response consistency. Lower spread = more stable, reliable agent.",
         color=TEXT_DIM, fontsize=10, ha="center")

apply_dark_style(fig, axes)

run_metric_colors = {"recall": "#58A6FF", "precision": "#3FB950", "f1": "#FFA657"}
markers = {"recall": "o", "precision": "s", "f1": "D"}

for ax, task in zip(axes, tasks):
    task_data = run_agg[run_agg["task"] == task]
    runs = task_data["run_number"].values

    for metric in ["recall", "precision", "f1"]:
        vals = task_data[metric].fillna(0).values
        label = {"recall": "Recall", "precision": "Precision", "f1": "F1 Score"}[metric]
        ax.plot(runs, vals, color=run_metric_colors[metric],
                marker=markers[metric], linewidth=2.5, markersize=9,
                label=label, zorder=4)
        ax.fill_between(runs, vals, alpha=0.10, color=run_metric_colors[metric])

        # Annotate each point
        for r, v in zip(runs, vals):
            if v > 0:
                ax.annotate(f"{v:.2f}", (r, v),
                            textcoords="offset points", xytext=(0, 9),
                            ha="center", fontsize=7.5, color=run_metric_colors[metric])

    # Highlight best run
    f1_vals = task_data["f1"].fillna(0).values
    best_run = runs[f1_vals.argmax()] if f1_vals.max() > 0 else None
    if best_run:
        ax.axvline(best_run, color="#FFD700", linewidth=1.5, linestyle="--", alpha=0.6, zorder=2)
        ax.text(best_run + 0.05, 0.05, f"Best Run\n(Run {best_run})",
                color="#FFD700", fontsize=8, va="bottom", style="italic")

    ax.set_title(TASK_LABELS[task], color=TASK_COLORS[task],
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Prompt Run Number (1 = Baseline)", color=TEXT_DIM, fontsize=10)
    ax.set_ylabel("Score", color=TEXT_DIM, fontsize=10) if task == "ceo" else None
    ax.set_xticks(range(1, 6))
    ax.set_xticklabels([f"Run {i}\n({'Baseline' if i==1 else f'Rep {i}'})" for i in range(1,6)],
                        color=TEXT_W, fontsize=8.5)
    ax.set_ylim(-0.05, 1.35)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.yaxis.set_tick_params(labelcolor=TEXT_W)
    add_watermark(ax, "Ontario Health Evaluation")

legend_handles2 = [
    Line2D([0],[0], color=run_metric_colors[m], marker=markers[m], linewidth=2,
           markersize=8, label={"recall":"Recall","precision":"Precision","f1":"F1 Score"}[m])
    for m in ["recall","precision","f1"]
] + [Line2D([0],[0], color="#FFD700", linewidth=1.5, linestyle="--", label="Best Run (by F1)")]

fig.legend(handles=legend_handles2, loc="lower center", ncol=4,
           facecolor=PANEL_BG, edgecolor=GRID_C, labelcolor=TEXT_W, fontsize=10,
           framealpha=0.9, bbox_to_anchor=(0.5, -0.04))

plt.tight_layout()
plt.savefig(OUT_DET / "Vis1B_Copilot_Run_Comparison_Deterministic.png",
            dpi=200, bbox_inches="tight", facecolor=BG)
plt.close()
print("  ✓ Saved Vis1B")


# ════════════════════════════════════════════════════════════════════════════
# SET 2 — LLM-AS-JUDGE
# ════════════════════════════════════════════════════════════════════════════

llm_tool = pd.read_csv(LLM_DIR / "tool_summary_llm.csv")
llm_comb = pd.read_csv(LLM_DIR / "combined_scores.csv")

# ── VIS 2A: Copilot vs LLMs — All 7 Metrics (LLM Judge) ────────────────────
print("Generating Vis 2A: Copilot vs LLMs — LLM-as-Judge...")

llm_metrics = ["recall", "precision", "f1", "relevance", "groundedness",
               "completeness", "answer_relevancy"]
llm_labels  = ["Recall", "Precision", "F1 Score", "Relevance\n(LLM)", "Groundedness\n(LLM)",
               "Completeness\n(LLM)", "Answer\nRelevancy"]
DET_BADGE   = ["recall","precision","f1"]  # deterministic
LLM_BADGE   = ["relevance","groundedness","completeness","answer_relevancy"]  # LLM-judged

fig = plt.figure(figsize=(22, 15), facecolor=BG)
fig.suptitle(
    "Visualization 3  ·  Copilot Agent vs Commercial LLMs — LLM-as-Judge Evaluation (7 Metrics)",
    color=TEXT_W, fontsize=16, fontweight="bold", y=0.99
)
fig.text(0.5, 0.965,
         "Deterministic metrics (Recall · Precision · F1)  +  LLM-judged metrics (Relevance · Groundedness · Completeness · Answer Relevancy)",
         color=TEXT_DIM, fontsize=10, ha="center")

gs2 = gridspec.GridSpec(3, 7, figure=fig, hspace=0.6, wspace=0.30,
                        left=0.05, right=0.98, top=0.94, bottom=0.10)

for row_idx, task in enumerate(tasks):
    task_df = llm_tool[llm_tool["task"] == task].copy()
    task_df = task_df.set_index("model").reindex(MODELS_ORDER).reset_index()

    for col_idx, (metric, mlabel) in enumerate(zip(llm_metrics, llm_labels)):
        ax = fig.add_subplot(gs2[row_idx, col_idx])
        apply_dark_style(fig, [ax])

        values = task_df[metric].fillna(0).values
        is_llm_metric = metric in LLM_BADGE

        colors = [MODEL_COLORS.get(m, "#888") for m in MODELS_ORDER]
        # Make LLM-judged metrics slightly more vivid
        if is_llm_metric:
            colors = [c + "CC" if len(c) == 7 else c for c in colors]

        edge_colors = ["#FFD700" if m == COPILOT else "#1E1E1E" for m in MODELS_ORDER]
        edge_widths = [2.5 if m == COPILOT else 0.4 for m in MODELS_ORDER]

        bars = ax.bar(range(len(MODELS_ORDER)), values, color=colors,
                      edgecolor=edge_colors, linewidth=edge_widths,
                      width=0.68, zorder=3)

        for bar, val in zip(bars, values):
            if val > 0.01:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.025,
                        f"{val:.2f}", ha="center", va="bottom",
                        color=TEXT_W, fontsize=6.8, fontweight="bold", zorder=5)

        # LLM metric badge
        badge_color = "#BC8CFF" if is_llm_metric else "#58A6FF"
        badge_text  = "🤖 LLM" if is_llm_metric else "📐 Det."
        ax.text(0.97, 0.97, badge_text, transform=ax.transAxes,
                fontsize=7, color=badge_color, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=PANEL_BG, edgecolor=badge_color, linewidth=0.8))

        ax.set_ylim(0, 1.25)
        ax.set_xticks(range(len(MODELS_ORDER)))
        ax.set_xticklabels(
            [m.replace("MS Copilot Agent","Copilot").replace(" ","\n") for m in MODELS_ORDER],
            fontsize=6.5, color=TEXT_W
        )
        ax.set_yticks([0, 0.5, 1.0])
        ax.yaxis.set_tick_params(labelsize=7.5, labelcolor=TEXT_W)

        if col_idx == 0:
            ax.set_ylabel(TASK_LABELS[task], color=TASK_COLORS[task],
                          fontsize=11, fontweight="bold")
        if row_idx == 0:
            ax.set_title(mlabel, color=TEXT_W, fontsize=9.5, fontweight="bold", pad=6)

        add_watermark(ax, "Ontario Health")

legend_h = [mpatches.Patch(color=MODEL_COLORS[m],
             label=m.replace("MS Copilot Agent","★ MS Copilot Agent")) for m in MODELS_ORDER]
legend_h += [
    mpatches.Patch(facecolor="none", edgecolor="#FFD700", linewidth=2, label="Copilot (gold border)"),
    mpatches.Patch(color="#58A6FF", alpha=0.6, label="📐 Deterministic"),
    mpatches.Patch(color="#BC8CFF", alpha=0.6, label="🤖 LLM-judged"),
]
fig.legend(handles=legend_h, loc="lower center", ncol=8,
           facecolor=PANEL_BG, edgecolor=GRID_C, labelcolor=TEXT_W, fontsize=8.5,
           framealpha=0.9, bbox_to_anchor=(0.5, 0.01))

plt.savefig(OUT_LLM / "Vis2A_Copilot_vs_LLMs_LLM_Judge.png",
            dpi=200, bbox_inches="tight", facecolor=BG)
plt.close()
print("  ✓ Saved Vis2A")


# ── VIS 2B: Qualitative Deep-Dive — Copilot vs LLMs per Hospital (LLM Judge)
print("Generating Vis 2B: Qualitative Deep-Dive — LLM Judge...")

qual_metrics = ["relevance", "groundedness", "completeness", "answer_relevancy"]
qual_labels  = ["Relevance", "Groundedness", "Completeness", "Answer Relevancy"]

# Radar + grouped breakdown per task
fig = plt.figure(figsize=(22, 8), facecolor=BG)
fig.suptitle(
    "Visualization 4  ·  Qualitative Dimension Deep-Dive — LLM-as-Judge Scoring by Task",
    color=TEXT_W, fontsize=16, fontweight="bold", y=1.02
)
fig.text(0.5, 0.975,
         "All 4 LLM-judged quality metrics compared across every model and task  |  Scores normalised 0–1",
         color=TEXT_DIM, fontsize=10, ha="center")

# 3 tasks → each has a radar + bar pair
gs3 = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35, left=0.04, right=0.97, top=0.92, bottom=0.12)

N = len(qual_metrics)
angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
angles += angles[:1]

for col_idx, task in enumerate(tasks):
    task_df = llm_tool[llm_tool["task"] == task].copy()
    task_df = task_df.set_index("model").reindex(MODELS_ORDER)

    ax = fig.add_subplot(gs3[col_idx], polar=True)
    ax.set_facecolor(PANEL_BG)
    fig.patch.set_facecolor(BG)

    for model in MODELS_ORDER:
        if model not in task_df.index:
            continue
        vals = task_df.loc[model, qual_metrics].fillna(0).tolist()
        vals += vals[:1]
        color = MODEL_COLORS[model]
        lw = 3.5 if model == COPILOT else 1.5
        alpha_fill = 0.15 if model == COPILOT else 0.04
        zorder = 10 if model == COPILOT else 3
        label = "★ " + model if model == COPILOT else model
        ax.plot(angles, vals, "o-", linewidth=lw, color=color, label=label, zorder=zorder)
        ax.fill(angles, vals, alpha=alpha_fill, color=color, zorder=zorder-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(qual_labels, size=10, color=TEXT_W, fontweight="bold")
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25","0.50","0.75","1.00"], color=TEXT_DIM, size=7.5)
    ax.grid(color=GRID_C, linestyle="--", alpha=0.5)
    ax.spines["polar"].set_color(GRID_C)
    ax.set_title(TASK_LABELS[task], color=TASK_COLORS[task],
                 fontsize=14, fontweight="bold", pad=16)

# Single legend for all radars
legend_handles3 = [
    Line2D([0],[0], color=MODEL_COLORS[m], linewidth=3 if m==COPILOT else 1.5,
           marker="o", markersize=7,
           label=("★ " + m if m==COPILOT else m))
    for m in MODELS_ORDER
]
fig.legend(handles=legend_handles3, loc="lower center", ncol=5,
           facecolor=PANEL_BG, edgecolor=GRID_C, labelcolor=TEXT_W, fontsize=10,
           framealpha=0.9, bbox_to_anchor=(0.5, -0.02))

plt.savefig(OUT_LLM / "Vis2B_Qualitative_DeepDive_LLM_Judge.png",
            dpi=200, bbox_inches="tight", facecolor=BG)
plt.close()
print("  ✓ Saved Vis2B")

print(f"\n{'='*60}")
print(f"All 4 visualizations generated!")
print(f"  SET 1 (Deterministic): {OUT_DET}")
print(f"    - Vis1A_Copilot_vs_LLMs_Deterministic.png")
print(f"    - Vis1B_Copilot_Run_Comparison_Deterministic.png")
print(f"  SET 2 (LLM-as-Judge): {OUT_LLM}")
print(f"    - Vis2A_Copilot_vs_LLMs_LLM_Judge.png")
print(f"    - Vis2B_Qualitative_DeepDive_LLM_Judge.png")
