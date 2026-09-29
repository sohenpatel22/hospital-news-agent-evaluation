import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import json

def visualize_metrics():
    df = pd.read_csv('Metrics/summary_metrics.csv')
    
    # 1. Recall by Tier
    plt.figure(figsize=(10, 6))
    x = np.arange(len(df['Model']))
    width = 0.2
    
    plt.bar(x - width, df['Recall (Overall)'], width, label='Overall Recall')
    plt.bar(x, df['Recall (Tier A)'], width, label='Tier A Recall')
    plt.bar(x + width, df['Recall (Tier C)'], width, label='Tier C Recall')
    
    plt.xlabel('Model')
    plt.ylabel('Recall Score')
    plt.title('Recall by Confidence Tier')
    plt.xticks(x, df['Model'], rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig('Visualizations/recall_by_tier.png')
    plt.close()
    
    # 2. Precision vs Hallucination Rate
    plt.figure(figsize=(8, 6))
    plt.bar(df['Model'], df['Precision'], color='blue', alpha=0.6, label='Precision')
    plt.bar(df['Model'], df['Hallucination Rate'], bottom=df['Precision'], color='red', alpha=0.6, label='Hallucination Rate')
    plt.title('Precision and Hallucination Rate Breakdown')
    plt.xticks(rotation=45)
    plt.ylabel('Proportion of Outputs')
    plt.legend()
    plt.tight_layout()
    plt.savefig('Visualizations/precision_hallucination.png')
    plt.close()

    # 3. Specificity Radar Chart (simplified to bar chart for 3 models)
    plt.figure(figsize=(8, 6))
    sns.barplot(x='Model', y='% Specificity=3', data=df)
    plt.title('% of Items with Max Specificity Score (3)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('Visualizations/specificity.png')
    plt.close()
    
def calculate_consistency():
    path = "Parsed_Responses/MS Copilot Agent.json"
    if not os.path.exists(path):
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        sys_items = json.load(f)
        
    runs = {}
    for i in range(1, 6):
        runs[i] = set()
        
    for item in sys_items:
        run = item.get('_meta', {}).get('run')
        if not run: continue
        # Normalize to name and hospital
        name = item.get('Issue', '').split('-')[0].strip()
        hosp = item.get('Hospital', '').strip()
        ident = f"{hosp}|{name}".lower()
        
        # parse run number
        if 'Run 1' in run: runs[1].add(ident)
        elif 'Run 2' in run: runs[2].add(ident)
        elif 'Run 3' in run: runs[3].add(ident)
        elif 'Run 4' in run: runs[4].add(ident)
        elif 'Run 5' in run: runs[5].add(ident)
        
    # calculate jaccard pairs
    jaccards = []
    keys = list(runs.keys())
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            set1 = runs[keys[i]]
            set2 = runs[keys[j]]
            if not set1 and not set2: continue
            intersect = len(set1.intersection(set2))
            union = len(set1.union(set2))
            jaccards.append(intersect / union if union > 0 else 0)
            
    mean_jaccard = sum(jaccards) / max(len(jaccards), 1)
    
    # items in all 5
    all_union = set()
    for s in runs.values(): all_union.update(s)
    
    in_all = 0
    for ident in all_union:
        if all(ident in runs[r] for r in runs):
            in_all += 1
            
    stability = in_all / max(len(all_union), 1)
    
    res = f"MS Copilot Consistency:\nMean Pairwise Jaccard: {mean_jaccard:.2f}\nPer-item Stability (% in all 5): {stability:.2%}"
    print(res)
    with open('Metrics/copilot_consistency.txt', 'w') as f:
        f.write(res)

if __name__ == '__main__':
    visualize_metrics()
    calculate_consistency()
