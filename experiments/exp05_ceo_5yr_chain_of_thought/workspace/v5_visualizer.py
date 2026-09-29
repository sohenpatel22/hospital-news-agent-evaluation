import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from docx import Document

os.makedirs('Visualizations', exist_ok=True)

metrics = pd.read_csv('Metrics/v5_metrics.csv')

# ─── Full model display names ─────────────────────────────────────────────────
MODEL_LABELS = {
    'ChatGPT':          'ChatGPT — GPT 5.6 Luna',
    'Claude':           'Claude — Sonnet 5',
    'Gemini':           'Gemini — 3.1 Pro',
    'MS Copilot Agent': 'Microsoft Copilot Studio — GPT 5 Reasoning',
    'Perplexity':       'Perplexity — Sonar (Default)',
}

STYLE = {
    'ChatGPT':          '#4C72B0',
    'Claude':           '#DD8452',
    'Gemini':           '#55A868',
    'MS Copilot Agent': '#8172B2',
    'Perplexity':       '#C44E52'
}

models      = metrics['Model'].tolist()
labels      = [MODEL_LABELS[m] for m in models]
recall      = metrics['Recall'].tolist()
precision   = metrics['Precision'].tolist()
f1          = metrics['F1 Score'].tolist()
tier1       = metrics['Tier 1 Recall'].tolist()
tier2       = metrics['Tier 2 Recall'].tolist()
tier3       = metrics['Tier 3 Recall'].tolist()
field_acc   = metrics['Field-level Accuracy'].tolist()
specificity = metrics['Specificity'].tolist()
hallucin    = metrics['Hallucination Rate'].tolist()
omission    = metrics['Omission Rate'].tolist()
completeness= metrics['Completeness'].tolist()
consistency = metrics['Consistency'].tolist()
metrics_dict = {row['Model']: row for _, row in metrics.iterrows()}

# ─── Compute per-hospital recall variance for box-plot whiskers ───────────────
LLM_DIR  = '../raw_responses'
GOLD_PATH = '../gold/CEO_Gold_Dataset.xlsx'

gold_df = pd.read_excel(GOLD_PATH, header=1)

# Build a map: hospital -> list of gold item core names
hosp_gold = {}
for _, row in gold_df.iterrows():
    hosp = str(row['hospital']).strip().lower()
    core = str(row['name_or_issue']).split('-')[0].strip().lower()
    hosp_gold.setdefault(hosp, []).append(core)

all_hospitals = list(hosp_gold.keys())
total_gold_per_hosp = {h: len(v) for h, v in hosp_gold.items()}

def get_model_per_hosp_recall(model):
    """Compute recall separately for each hospital for variance estimation."""
    model_dir = os.path.join(LLM_DIR, model)
    hosp_tp = {h: 0 for h in all_hospitals}
    if not os.path.exists(model_dir):
        return [0.0] * len(all_hospitals)
    for root, dirs, files in os.walk(model_dir):
        for f in files:
            if f.endswith('.docx') and not f.startswith('~'):
                doc = Document(os.path.join(root, f))
                full_text = ' '.join([p.text.lower() for p in doc.paragraphs])
                for hosp, gold_names in hosp_gold.items():
                    for name in gold_names:
                        if len(name) > 4 and name in full_text:
                            hosp_tp[hosp] = hosp_tp.get(hosp, 0) + 1
    recalls = []
    for h in all_hospitals:
        denom = total_gold_per_hosp.get(h, 1)
        tp_capped = min(hosp_tp[h], denom)
        recalls.append(tp_capped / denom)
    return recalls

# Pre-compute per-hospital recall for whisker variance
per_hosp_recall = {}
for m in models:
    per_hosp_recall[m] = get_model_per_hosp_recall(m)

# ─── Helper ───────────────────────────────────────────────────────────────────
def save(name):
    path = f'Visualizations/{name}.png'
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  saved: {path}')

# ─── 1. Overall Recall — HORIZONTAL BAR with variance whiskers ───────────────
def fig_overall_recall():
    fig, ax = plt.subplots(figsize=(11, 6))

    colors = [STYLE[m] for m in models]
    y_pos  = np.arange(len(models))

    # Whisker values: std across hospitals
    xerr_vals = [np.std(per_hosp_recall[m]) for m in models]

    bars = ax.barh(y_pos, recall, xerr=xerr_vals,
                   color=colors, edgecolor='white', linewidth=0.8,
                   error_kw=dict(ecolor='#555555', capsize=5, capthick=1.5, elinewidth=1.5),
                   height=0.55)

    # Value labels at end of bars
    for bar, val, xe in zip(bars, recall, xerr_vals):
        ax.text(val + xe + 0.01, bar.get_y() + bar.get_height() / 2,
                f'{val:.3f}', va='center', fontsize=10, fontweight='bold', color='#222222')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Recall  (TP / 133 gold items)', fontsize=11)
    ax.set_xlim(0, 0.75)
    ax.set_title('Overall Recall by Model — Chain-of-Thought Longitudinal Dataset\n'
                 '(Whiskers = ± std across hospitals; n = 133 gold events)',
                 fontsize=13, pad=12)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    save('fig_Overall_Recall_V5')

# ─── Generic horizontal bar helper ───────────────────────────────────────────
def plot_hbar(metric_name, values, title, xlabel, xlim=(0, 1.05), add_variance=False):
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = [STYLE[m] for m in models]
    y_pos  = np.arange(len(models))

    xerr_vals = [np.std(per_hosp_recall[m]) for m in models] if add_variance else None

    if xerr_vals:
        bars = ax.barh(y_pos, values, xerr=xerr_vals, color=colors,
                       edgecolor='white', linewidth=0.8,
                       error_kw=dict(ecolor='#555555', capsize=5, capthick=1.5, elinewidth=1.5),
                       height=0.55)
    else:
        bars = ax.barh(y_pos, values, color=colors,
                       edgecolor='white', linewidth=0.8, height=0.55)

    for bar, val in zip(bars, values):
        offset = (xerr_vals[bars.patches.index(bar)] + 0.01) if xerr_vals else 0.01
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f'{val:.3f}', va='center', fontsize=10, fontweight='bold', color='#222222')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_xlim(*xlim)
    ax.set_title(title, fontsize=13, pad=12)
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    save(metric_name)

# ─── Grouped horizontal bar (tiered recall) ──────────────────────────────────
def fig_recall_by_tier():
    fig, ax = plt.subplots(figsize=(12, 7))
    height = 0.22
    y = np.arange(len(models))
    tier_colors = ['#2166AC', '#4DAC26', '#D01C8B']
    tier_labels  = ['Tier 1 — CEO / President', 'Tier 2 — VP / C-Suite', 'Tier 3 — Board / Other']

    for i, (tier_data, tlabel, tcol) in enumerate(zip([tier1, tier2, tier3], tier_labels, tier_colors)):
        offset = (i - 1) * height
        bars = ax.barh(y + offset, tier_data, height, label=tlabel, color=tcol,
                       edgecolor='white', linewidth=0.7)
        for bar, val in zip(bars, tier_data):
            if val > 0.02:
                ax.text(val + 0.005, bar.get_y() + bar.get_height() / 2,
                        f'{val:.2f}', va='center', fontsize=8.5, color='#222222')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Recall', fontsize=11)
    ax.set_xlim(0, 1.0)
    ax.set_title('Recall by Confidence Tier — Chain-of-Thought Longitudinal Dataset\n'
                 '(Tier 1: 17 items | Tier 2: 23 items | Tier 3: 93 items)',
                 fontsize=13, pad=12)
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    save('fig_Recall_By_Tier_V5')

# ─── Precision-Recall Scatter ─────────────────────────────────────────────────
def fig_precision_recall_scatter():
    fig, ax = plt.subplots(figsize=(8, 8))
    xv = np.linspace(0.01, 1, 300)
    yv = np.linspace(0.01, 1, 300)
    Xg, Yg = np.meshgrid(xv, yv)
    F1g = 2 * (Xg * Yg) / (Xg + Yg)
    cs = ax.contour(Xg, Yg, F1g, levels=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                    colors='lightgrey', linestyles='--', linewidths=0.8)
    ax.clabel(cs, inline=True, fontsize=9, fmt='F1=%.1f')

    for m, p, r in zip(models, precision, recall):
        ax.scatter(r, p, s=220, color=STYLE[m], zorder=5, label=MODEL_LABELS[m])
        ax.annotate(MODEL_LABELS[m], xy=(r, p), xytext=(6, 4),
                    textcoords='offset points', fontsize=8)

    ax.set_xlabel('Recall', fontsize=12)
    ax.set_ylabel('Precision', fontsize=12)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.set_title('Precision vs Recall — Chain-of-Thought Dataset (n = 133)', fontsize=13)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3)
    save('fig_PR_scatter_V5')

# ─── Summary Table ────────────────────────────────────────────────────────────
def fig_summary_table():
    rows = []
    for m in models:
        r = metrics_dict[m]
        rows.append([
            MODEL_LABELS[m],
            f"{r['Recall']:.3f}",
            f"{r['Precision']:.3f}",
            f"{r['F1 Score']:.3f}",
            f"{r['Hallucination Rate']:.3f}",
            f"{r['Omission Rate']:.3f}",
            f"{r['Field-level Accuracy']:.3f}",
            f"{r['Consistency']:.3f}",
            f"{r['Specificity']:.3f}",
        ])
    cols = ['Model', 'Recall', 'Precision', 'F1', 'Hall.%', 'Omiss.%', 'Field Acc.', 'Consist.', 'Specif.']
    fig, ax = plt.subplots(figsize=(18, 3.5))
    ax.axis('off')
    tbl = ax.table(cellText=rows, colLabels=cols, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)
    tbl.scale(1.0, 2.2)
    for j in range(len(cols)):
        tbl[(0, j)].set_facecolor('#2C3E50')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold')
    for i in range(1, len(rows) + 1):
        bg = '#F0F4FA' if i % 2 == 0 else 'white'
        for j in range(len(cols)):
            tbl[(i, j)].set_facecolor(bg)
    ax.set_title('Summary Metrics — Chain-of-Thought Longitudinal Dataset Evaluation\n(n = 133 gold events)',
                 fontsize=13, pad=20)
    save('fig_Summary_Table_V5')

# ─── Run all ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    fig_overall_recall()
    fig_recall_by_tier()
    plot_hbar('fig_Precision_V5', precision,
              'Precision by Model — Chain-of-Thought Dataset', 'Precision')
    plot_hbar('fig_F1_V5', f1,
              'F1 Score by Model — Chain-of-Thought Dataset', 'F1 Score')
    plot_hbar('fig_Field_Accuracy_V5', field_acc,
              'Field-Level Accuracy (Conditional on Entity Match)', 'Accuracy')
    plot_hbar('fig_Specificity_V5', specificity,
              'Specificity (Exact Role Extraction Accuracy)', 'Specificity')
    plot_hbar('fig_Hallucination_V5', hallucin,
              'Hallucination Rate — Chain-of-Thought Dataset', 'Hallucination Rate')
    plot_hbar('fig_Omission_V5', omission,
              'Omission Rate (1 − Recall) — Chain-of-Thought Dataset', 'Omission Rate')
    plot_hbar('fig_Completeness_V5', completeness,
              'Completeness (Valid Fields / Total Fields)', 'Completeness')
    plot_hbar('fig_Consistency_V5', consistency,
              'Format Consistency (Followed → Delimiter Structure)', 'Consistency')
    fig_precision_recall_scatter()
    fig_summary_table()
