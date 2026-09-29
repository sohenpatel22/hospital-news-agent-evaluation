import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.makedirs('Visualizations', exist_ok=True)

metrics = pd.read_csv('Metrics/v4_metrics.csv')
metrics_dict = {row['Model']: row for _, row in metrics.iterrows()}

models = metrics['Model'].tolist()
recall = metrics['Recall'].tolist()
precision = metrics['Precision'].tolist()
f1 = metrics['F1 Score'].tolist()
tier1 = metrics['Tier 1 Recall'].tolist()
tier2 = metrics['Tier 2 Recall'].tolist()
tier3 = metrics['Tier 3 Recall'].tolist()
field_acc = metrics['Field-level Accuracy'].tolist()
specificity = metrics['Specificity'].tolist()
hallucination = metrics['Hallucination Rate'].tolist()
omission = metrics['Omission Rate'].tolist()
completeness = metrics['Completeness'].tolist()
consistency = metrics['Consistency'].tolist()

STYLE = {
    'ChatGPT':          '#4C72B0',
    'Claude':           '#DD8452',
    'Gemini':           '#55A868',
    'MS Copilot Agent': '#8172B2',
    'Perplexity':       '#C44E52'
}

def save(name):
    path = f'Visualizations/{name}.png'
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  saved: {path}')

def plot_bar(metric_name, values, title, ylabel, ylim=(0, 1.05)):
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [STYLE.get(m, '#333333') for m in models]
    bars = ax.bar(models, values, color=colors, edgecolor='white', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    save(metric_name)

def plot_grouped_bar(metric_name, grouped_data, labels, title, ylabel, ylim=(0, 1.05)):
    x = np.arange(len(models))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10, 5))
    
    offsets = [-width, 0, width]
    colors = ['#4C72B0', '#DD8452', '#55A868']
    
    for i, (label, data) in enumerate(zip(labels, grouped_data)):
        ax.bar(x + offsets[i], data, width, label=label, color=colors[i], edgecolor='white')
        
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(*ylim)
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    save(metric_name)

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
        ax.scatter(r, p, s=200, color=STYLE.get(m, 'k'), zorder=5, label=m)
        ax.annotate(m, xy=(r, p), xytext=(6, 4),
                    textcoords='offset points', fontsize=9)

    ax.set_xlabel('Recall', fontsize=12)
    ax.set_ylabel('Precision', fontsize=12)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.set_title('Precision vs Recall — 5-Year Dataset (n=133)', fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    save('fig_PR_scatter_5Years')

def fig_summary_table():
    rows = []
    for m in models:
        r = metrics_dict[m]
        rows.append([
            m,
            f"{r['Recall']:.3f}",
            f"{r['Precision']:.3f}",
            f"{r['F1 Score']:.3f}",
            f"{r['Hallucination Rate']:.3f}",
            f"{r['Omission Rate']:.3f}",
            f"{r['Field-level Accuracy']:.3f}",
            f"{r['Consistency']:.3f}"
        ])
    cols = ['Model', 'Recall', 'Precision', 'F1', 'Hall. Rate', 'Omiss. Rate', 'Field Acc.', 'Consistency']
    fig, ax = plt.subplots(figsize=(14, 3))
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
    ax.set_title('Summary Metrics — 5-Year Longitudinal Dataset Evaluation', fontsize=14, pad=20)
    save('fig_Summary_Table_5Years')

if __name__ == '__main__':
    plot_bar('fig_Overall_Recall_5Years', recall, 'Overall Recall by Model', 'Recall')
    plot_bar('fig_Precision_5Years', precision, 'Precision by Model', 'Precision')
    plot_bar('fig_F1_5Years', f1, 'F1 Score by Model', 'F1 Score')
    
    plot_grouped_bar('fig_Recall_By_Tier_5Years', [tier1, tier2, tier3], 
                     ['Tier 1 (CEO)', 'Tier 2 (VP/C-Suite)', 'Tier 3 (Board)'], 
                     'Recall by Confidence Tier', 'Recall')
                     
    plot_bar('fig_Field_Accuracy_5Years', field_acc, 'Field-Level Accuracy (Conditional on Entity Match)', 'Accuracy')
    plot_bar('fig_Specificity_5Years', specificity, 'Specificity (Exact Role Extraction)', 'Specificity')
    
    plot_bar('fig_Hallucination_5Years', hallucination, 'Hallucination Rate', 'Hallucination Rate')
    plot_bar('fig_Omission_5Years', omission, 'Omission Rate (1 - Recall)', 'Omission Rate')
    
    plot_bar('fig_Completeness_5Years', completeness, 'Completeness (Valid Fields / Total Fields)', 'Completeness')
    plot_bar('fig_Consistency_5Years', consistency, 'Format Consistency (Followed Delimiter Structure)', 'Consistency')
    
    fig_precision_recall_scatter()
    fig_summary_table()
