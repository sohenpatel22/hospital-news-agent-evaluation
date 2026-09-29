import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def create_visualizations():
    print("--- Phase 6: Visualizations ---")
    
    out_dir = "visualizations"
    os.makedirs(out_dir, exist_ok=True)
    
    summary_file = "metrics/tool_summary.csv"
    if not os.path.exists(summary_file):
        print(f"Error: {summary_file} not found.")
        return
        
    df = pd.read_csv(summary_file)
    
    # 1. Grouped bar chart by task and model (F1 Score)
    plt.figure(figsize=(12, 6))
    sns.set_theme(style="whitegrid")
    
    # Capitalize tasks for better display
    df['Task (Title)'] = df['task'].str.title()
    
    ax = sns.barplot(
        data=df,
        x='Task (Title)',
        y='f1',
        hue='tool',
        palette='viridis'
    )
    plt.title('F1 Score by Tool and Task', fontsize=16)
    plt.xlabel('Task', fontsize=12)
    plt.ylabel('F1 Score', fontsize=12)
    plt.ylim(0, 1)
    plt.legend(title='Model', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'f1_by_tool_and_task.png'), dpi=300)
    plt.close()
    
    # 2. Precision vs Recall Scatter Plot
    plt.figure(figsize=(10, 8))
    sns.scatterplot(
        data=df,
        x='recall',
        y='precision',
        hue='tool',
        style='Task (Title)',
        s=200,
        palette='viridis'
    )
    # add diagonal line for F1 intuition
    plt.plot([0, 1], [0, 1], 'k--', alpha=0.3)
    plt.title('Precision vs Recall Trade-off', fontsize=16)
    plt.xlabel('Recall', fontsize=12)
    plt.ylabel('Precision', fontsize=12)
    plt.xlim(0, 1.05)
    plt.ylim(0, 1.05)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'precision_vs_recall.png'), dpi=300)
    plt.close()
    
    # 3. Heatmap of overall metrics by tool (averaging across tasks)
    plt.figure(figsize=(10, 6))
    df_avg = df.groupby('tool')[['precision', 'recall', 'f1', 'hallucination_rate']].mean()
    sns.heatmap(
        df_avg,
        annot=True,
        cmap='coolwarm',
        vmin=0, vmax=1,
        fmt='.2f',
        linewidths=.5
    )
    plt.title('Average Metrics by Tool (Across all tasks)', fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'metrics_heatmap.png'), dpi=300)
    plt.close()
    
    print(f"Done. Saved visualizations to {out_dir}/")

if __name__ == "__main__":
    create_visualizations()
