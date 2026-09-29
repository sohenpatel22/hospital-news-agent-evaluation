"""
Regenerate ONLY figures backed by genuinely computed metrics,
then rename ALL files in Visualizations/ to make status clear.

REAL DATA figures  -> keep as-is, regenerate fresh
SIMULATED figures  -> prefix filename with NOT_TO_USE_
"""

import os, json, shutil
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

VIZ = 'Visualizations'
os.makedirs(VIZ, exist_ok=True)

# ── Load actual metrics ────────────────────────────────────────────────────────
metrics = pd.read_csv('Metrics/llm_summary_metrics.csv')
metrics_dict = {row['Model']: row for _, row in metrics.iterrows()}

models     = metrics['Model'].tolist()
recall     = metrics['Recall'].tolist()
precision  = metrics['Precision'].tolist()
f1         = metrics['F1 Score'].tolist()
tier_a     = metrics['Tier A Recall'].tolist()
hall_rate  = metrics['Hallucination Rate'].tolist()

# ── Helper ─────────────────────────────────────────────────────────────────────
STYLE = {
    'ChatGPT':          '#4C72B0',
    'Claude':           '#DD8452',
    'Gemini':           '#55A868',
    'Perplexity':       '#C44E52',
    'MS Copilot Agent': '#8172B2',
}

def save(name):
    path = f'{VIZ}/{name}.png'
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  saved: {path}')
    return path

# ==============================================================================
# FIGURE A: Precision vs Recall scatter with iso-F1 contours   [REAL DATA]
# ==============================================================================
def fig_precision_recall_scatter():
    fig, ax = plt.subplots(figsize=(8, 8))

    # iso-F1 contours
    xv = np.linspace(0.01, 1, 300)
    yv = np.linspace(0.01, 1, 300)
    Xg, Yg = np.meshgrid(xv, yv)
    F1g = 2 * (Xg * Yg) / (Xg + Yg)
    cs = ax.contour(Xg, Yg, F1g, levels=[0.3, 0.5, 0.6, 0.7, 0.8],
                    colors='lightgrey', linestyles='--', linewidths=0.8)
    ax.clabel(cs, inline=True, fontsize=9, fmt='F1=%.1f')

    for m, p, r in zip(models, precision, recall):
        ax.scatter(r, p, s=200, color=STYLE[m], zorder=5, label=m)
        ax.annotate(m, xy=(r, p), xytext=(6, 4),
                    textcoords='offset points', fontsize=9)

    ax.set_xlabel('Recall', fontsize=12)
    ax.set_ylabel('Precision', fontsize=12)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.set_title('Precision vs Recall — CEO Leadership Task\n(n = 16 gold items)', fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    save('fig_PR_scatter_REAL')

# ==============================================================================
# FIGURE B: Overall Recall bar chart                            [REAL DATA]
# ==============================================================================
def fig_overall_recall():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, recall, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, recall):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Recall  (TP / 16 gold items)', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('Overall Recall by Model — CEO Leadership Task\n(gold dataset: 16 verified items)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_Overall_Recall_REAL')

# ==============================================================================
# FIGURE C: Precision bar chart                                 [REAL DATA]
# ==============================================================================
def fig_precision():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, precision, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, precision):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Precision  (TP / total extracted)', fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.set_title('Precision by Model — CEO Leadership Task', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_Precision_REAL')

# ==============================================================================
# FIGURE D: F1 Score bar chart                                  [REAL DATA]
# ==============================================================================
def fig_f1():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, f1, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, f1):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('F1 Score', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('F1 Score by Model — CEO Leadership Task', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_F1_REAL')

# ==============================================================================
# FIGURE E: Tier A Recall bar chart                             [REAL DATA]
# Tier A gold items: C13,C45,C46,C47,C76,C78,C126,C127,C128,C129,C130,C132,C133
# ==============================================================================
def fig_tier_a_recall():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, tier_a, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, tier_a):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Tier A Recall  (TP_A / 13 Tier-A items)', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('Tier A Recall by Model\n(Tier A = 13 items with dated public announcements)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_TierA_Recall_REAL')

# ==============================================================================
# FIGURE F: Hallucination / Out-of-scope Rate                   [REAL DATA]
# ==============================================================================
def fig_hallucination():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, hall_rate, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, hall_rate):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.005,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Hallucination Rate  ((Extracted − TP) / Extracted)', fontsize=11)
    ax.set_ylim(0, 0.55)
    ax.set_title('Hallucination / Out-of-Scope Rate by Model\n(0 = no spurious extractions)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_Hallucination_Rate_REAL')

# ==============================================================================
# FIGURE G: Summary metric table                                [REAL DATA]
# ==============================================================================
def fig_summary_table():
    rows = []
    for m in models:
        r = metrics_dict[m]
        rows.append([
            m,
            f"{r['Recall']:.3f}",
            f"{r['Precision']:.3f}",
            f"{r['F1 Score']:.3f}",
            f"{r['Tier A Recall']:.3f}",
            f"{r['Hallucination Rate']:.3f}",
        ])
    cols = ['Model', 'Recall', 'Precision', 'F1', 'Tier A Recall', 'Hall. Rate']
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.axis('off')
    tbl = ax.table(cellText=rows, colLabels=cols, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.1, 2.0)
    # Header styling
    for j in range(len(cols)):
        tbl[(0, j)].set_facecolor('#2C3E50')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold')
    # Row colours
    for i in range(1, len(rows)+1):
        for j in range(len(cols)):
            tbl[(i, j)].set_facecolor('#F7F9FC' if i % 2 == 0 else 'white')
    ax.set_title('Summary Metrics — CEO Leadership Task  (n = 16 gold items)', 
                 fontsize=13, pad=20)
    save('fig_Summary_Table_REAL')

# ==============================================================================
# RENAME stale / simulated files with NOT_TO_USE_ prefix
# ==============================================================================
SIMULATED_STEMS = {
    # Old paper figures with random data
    'fig1_recall_tier',
    'fig3_provenance',
    'fig4_errors',
    'fig5_citations',
    'fig6_heatmap',
    'fig7_consistency',
    # Old evaluator figures (superseded by cleaner versions above)
    'llm_precision_recall',
    'llm_tier_a_recall',
    'llm_hallucination_rate',
    # Very old first-pass figures
    'precision_hallucination',
    'recall_by_tier',
    'specificity',
}

# fig2 and fig8 had real data but are superseded — keep them but mark clearly
SUPERSEDED_STEMS = {'fig2_pr_scatter', 'fig8_table'}

def rename_stale():
    for fname in os.listdir(VIZ):
        stem, ext = os.path.splitext(fname)
        if ext.lower() != '.png':
            continue
        if stem in SIMULATED_STEMS and not stem.startswith('NOT_TO_USE_'):
            src  = os.path.join(VIZ, fname)
            dest = os.path.join(VIZ, f'NOT_TO_USE_{fname}')
            shutil.move(src, dest)
            print(f'  renamed -> NOT_TO_USE_{fname}')
        elif stem in SUPERSEDED_STEMS and not stem.startswith('SUPERSEDED_'):
            src  = os.path.join(VIZ, fname)
            dest = os.path.join(VIZ, f'SUPERSEDED_{fname}')
            shutil.move(src, dest)
            print(f'  renamed -> SUPERSEDED_{fname}')

# ==============================================================================
# RUN
# ==============================================================================
if __name__ == '__main__':
    print('\n=== Generating REAL-DATA figures ===')
    fig_precision_recall_scatter()
    fig_overall_recall()
    fig_precision()
    fig_f1()
    fig_tier_a_recall()
    fig_hallucination()
    fig_summary_table()

    print('\n=== Renaming stale / simulated figures ===')
    rename_stale()

    print('\n=== Done. Visualizations folder contents:')
    for f in sorted(os.listdir(VIZ)):
        print(' ', f)
