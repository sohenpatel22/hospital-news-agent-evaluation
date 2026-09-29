import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.makedirs('Visualizations', exist_ok=True)

metrics = pd.read_csv('Metrics/llm_summary_metrics.csv')
metrics_dict = {row['Model']: row for _, row in metrics.iterrows()}

models     = metrics['Model'].tolist()
recall     = metrics['Recall'].tolist()
precision  = metrics['Precision'].tolist()
f1         = metrics['F1 Score'].tolist()
tier_a     = metrics['Tier A Recall'].tolist()
hall_rate  = metrics['Hallucination Rate'].tolist()

STYLE = {
    'ChatGPT':          '#4C72B0',
    'Claude':           '#DD8452',
    'Gemini':           '#55A868',
    'Perplexity':       '#C44E52',
    'MS Copilot Agent': '#8172B2',
}

def save(name):
    path = f'Visualizations/{name}.png'
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  saved: {path}')

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
        ax.scatter(r, p, s=200, color=STYLE[m], zorder=5, label=m)
        ax.annotate(m, xy=(r, p), xytext=(6, 4),
                    textcoords='offset points', fontsize=9)

    ax.set_xlabel('Recall', fontsize=12)
    ax.set_ylabel('Precision', fontsize=12)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.set_title('Precision vs Recall — CEO Leadership Task (V2 Gold)\n(n = 7 gold items)', fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    save('fig_PR_scatter_V2')

def fig_overall_recall():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, recall, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, recall):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Recall  (TP / 7 gold items)', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('Overall Recall by Model — CEO Leadership Task (V2 Gold)\n(gold dataset: 7 verified items)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_Overall_Recall_V2')

def fig_precision():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, precision, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, precision):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Precision  (TP / total extracted)', fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.set_title('Precision by Model — CEO Leadership Task (V2 Gold)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_Precision_V2')

def fig_f1():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, f1, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, f1):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('F1 Score', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('F1 Score by Model — CEO Leadership Task (V2 Gold)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_F1_V2')

def fig_tier_a_recall():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, tier_a, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, tier_a):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Tier A Recall  (TP_A / 5 Tier-A items)', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('Tier A Recall by Model (V2 Gold)\n(Tier A = 5 items)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_TierA_Recall_V2')

def fig_hallucination():
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE[m] for m in models]
    bars = ax.bar(models, hall_rate, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, hall_rate):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.005,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Hallucination Rate  ((Extracted − TP) / Extracted)', fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('Hallucination / Out-of-Scope Rate by Model (V2 Gold)\n(0 = no spurious extractions)', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save('fig_Hallucination_Rate_V2')

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
    for j in range(len(cols)):
        tbl[(0, j)].set_facecolor('#2C3E50')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold')
    for i in range(1, len(rows)+1):
        for j in range(len(cols)):
            tbl[(i, j)].set_facecolor('#F7F9FC' if i % 2 == 0 else 'white')
    ax.set_title('Summary Metrics — CEO Leadership Task (V2 Gold)\n(n = 7 gold items)', 
                 fontsize=13, pad=20)
    save('fig_Summary_Table_V2')

if __name__ == '__main__':
    fig_precision_recall_scatter()
    fig_overall_recall()
    fig_precision()
    fig_f1()
    fig_tier_a_recall()
    fig_hallucination()
    fig_summary_table()
