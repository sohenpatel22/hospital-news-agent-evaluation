"""
05_visualize_llm.py
===================
Generates rich visualizations for the LLM evaluation pipeline:
  1. Radar chart — all 7 metrics per model (averaged across all tasks)
  2. Grouped bar chart — metric comparison by task and model
  3. Heatmap — all metrics × all models per task
  4. Abstention & Citation accuracy bar chart
"""

import pathlib
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns

BASE = pathlib.Path(__file__).parent
METRICS_DIR = BASE / "metrics"
OUT_DIR = BASE / "visualizations"

METRICS = ["recall", "precision", "f1", "relevance", "groundedness", "completeness", "answer_relevancy", "citation_accuracy"]
METRIC_LABELS = ["Recall", "Precision", "F1 Score", "Relevance", "Groundedness", "Completeness", "Ans. Relevancy", "Citation Acc."]

MODEL_COLORS = {
    "MS Copilot Agent": "#2196F3",
    "ChatGPT":          "#4CAF50",
    "Claude":           "#FF9800",
    "Gemini":           "#9C27B0",
    "Perplexity":       "#F44336",
}

def run_visualize():
    print("--- Stage 5: Visualizations ---")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    combined_path = METRICS_DIR / "combined_scores.csv"
    if not combined_path.exists():
        print("ERROR: Run 04_combine_results.py first.")
        return
    
    df = pd.read_csv(combined_path)
    available_metrics = [m for m in METRICS if m in df.columns]
    available_labels = [METRIC_LABELS[METRICS.index(m)] for m in available_metrics]
    
    models = [m for m in MODEL_COLORS if m in df["model"].unique()]
    tasks = df["task"].unique()
    
    # -----------------------------------------------------------------------
    # 1. Radar Chart — overall performance per model (averaged across tasks)
    # -----------------------------------------------------------------------
    overall = df.groupby("model")[available_metrics].mean()
    
    N = len(available_metrics)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    ax.set_facecolor("#0f1117")
    fig.patch.set_facecolor("#0f1117")
    
    for model in models:
        if model not in overall.index:
            continue
        values = overall.loc[model, available_metrics].fillna(0).tolist()
        values += values[:1]
        color = MODEL_COLORS[model]
        ax.plot(angles, values, 'o-', linewidth=2, color=color, label=model)
        ax.fill(angles, values, alpha=0.08, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(available_labels, size=11, color="white")
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], color="gray", size=8)
    ax.grid(color="gray", linestyle="--", alpha=0.3)
    ax.spines["polar"].set_color("gray")
    
    legend = ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15),
                       facecolor="#1a1a2e", labelcolor="white", edgecolor="gray")
    ax.set_title("Overall Model Performance — All Metrics", color="white", size=15, pad=20)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "radar_overall.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    print("  Saved radar_overall.png")
    
    # -----------------------------------------------------------------------
    # 2. Grouped bar chart — F1, Completeness, Groundedness by task × model
    # -----------------------------------------------------------------------
    plot_metrics = [m for m in ["f1", "completeness", "groundedness"] if m in df.columns]
    plot_labels = [METRIC_LABELS[METRICS.index(m)] for m in plot_metrics]
    
    task_model_avg = df.groupby(["task","model"])[plot_metrics].mean().reset_index()
    
    fig, axes = plt.subplots(1, len(tasks), figsize=(6*len(tasks), 6), sharey=True)
    if len(tasks) == 1:
        axes = [axes]
    fig.patch.set_facecolor("#0f1117")
    
    bar_width = 0.2
    x = np.arange(len(models))
    
    for ax, task in zip(axes, sorted(tasks)):
        ax.set_facecolor("#1a1a2e")
        task_df = task_model_avg[task_model_avg["task"] == task]
        
        for i, (metric, label) in enumerate(zip(plot_metrics, plot_labels)):
            offsets = (i - len(plot_metrics)/2 + 0.5) * bar_width
            values = [task_df[task_df["model"]==m][metric].values[0] 
                      if not task_df[task_df["model"]==m].empty else 0 
                      for m in models]
            bars = ax.bar(x + offsets, values, bar_width, label=label,
                          color=plt.cm.Set2(i / len(plot_metrics)), alpha=0.85, edgecolor="white", linewidth=0.3)
        
        ax.set_title(task.upper(), color="white", fontsize=13, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([m.replace(" ", "\n") for m in models], color="white", fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.tick_params(axis='y', colors='white')
        ax.spines[:].set_color("gray")
        for spine in ax.spines.values():
            spine.set_color("gray")
        ax.yaxis.label.set_color("white")
        ax.grid(axis='y', color='gray', alpha=0.3, linestyle='--')
    
    handles, labels_leg = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_leg, loc='upper center', ncol=len(plot_metrics),
               facecolor="#1a1a2e", labelcolor="white", edgecolor="gray", fontsize=10)
    fig.suptitle("Key Metrics by Task and Model", color="white", fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "grouped_bar_by_task.png", dpi=200, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print("  Saved grouped_bar_by_task.png")
    
    # -----------------------------------------------------------------------
    # 3. Heatmap — all metrics × all models
    # -----------------------------------------------------------------------
    heat_data = df.groupby("model")[available_metrics].mean().reindex(models).fillna(0)
    heat_data.columns = available_labels
    
    fig, ax = plt.subplots(figsize=(max(10, len(available_labels)*1.4), max(5, len(models)*0.9)))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")
    
    sns.heatmap(
        heat_data,
        annot=True, fmt=".2f",
        cmap="RdYlGn",
        vmin=0, vmax=1,
        linewidths=0.5,
        linecolor="#0f1117",
        ax=ax,
        cbar_kws={"shrink": 0.8}
    )
    ax.set_title("All Metrics × All Models (averaged)", color="white", fontsize=14, pad=12)
    ax.tick_params(colors="white")
    ax.set_yticklabels(ax.get_yticklabels(), color="white", rotation=0)
    ax.set_xticklabels(ax.get_xticklabels(), color="white", rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "heatmap_all_metrics.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    print("  Saved heatmap_all_metrics.png")
    
    # -----------------------------------------------------------------------
    # 4. Citation Accuracy + Abstention bar chart
    # -----------------------------------------------------------------------
    cite_agg_cols = [m for m in ["citation_accuracy", "abstention_correct"] if m in df.columns]
    if cite_agg_cols:
        cite_data = df.groupby("model")[cite_agg_cols].mean().reindex(models).fillna(0)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#0f1117")
        ax.set_facecolor("#1a1a2e")
        
        x = np.arange(len(models))
        w = 0.35
        colors_list = [MODEL_COLORS.get(m, "gray") for m in models]
        
        if "citation_accuracy" in cite_data.columns:
            ax.bar(x - w/2, cite_data["citation_accuracy"].values, w,
                   label="Citation Accuracy", color="#2196F3", alpha=0.85, edgecolor="white", linewidth=0.3)
        if "abstention_correct" in cite_data.columns:
            ax.bar(x + w/2, cite_data["abstention_correct"].values, w,
                   label="Abstention Correct", color="#4CAF50", alpha=0.85, edgecolor="white", linewidth=0.3)
        
        ax.set_xticks(x)
        ax.set_xticklabels([m.replace(" ","\n") for m in models], color="white", fontsize=9)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Score (0-1)", color="white")
        ax.tick_params(axis='y', colors='white')
        ax.set_title("Citation Accuracy & Abstention Correctness", color="white", fontsize=13)
        ax.legend(facecolor="#1a1a2e", labelcolor="white", edgecolor="gray")
        ax.grid(axis='y', color='gray', alpha=0.3, linestyle='--')
        for spine in ax.spines.values():
            spine.set_color("gray")
        
        plt.tight_layout()
        plt.savefig(OUT_DIR / "citation_abstention.png", dpi=200, facecolor=fig.get_facecolor())
        plt.close()
        print("  Saved citation_abstention.png")
    
    print(f"\nAll visualizations saved to {OUT_DIR}/")

if __name__ == "__main__":
    run_visualize()
