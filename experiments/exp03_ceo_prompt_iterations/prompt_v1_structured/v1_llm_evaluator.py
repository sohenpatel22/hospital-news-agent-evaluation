import os
import pandas as pd

def run_evaluation():
    # Total Gold items = 16 (since C78 counts as 2, wait, 16 items in total in the gold standard in the baseline)
    # The baseline used gold_total = 16, and tier_a_gold = 13.
    gold_total = 16
    
    models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']
    
    # Based on our manual and script adjudication of the Prompt V1 text dump
    model_matches = {
        'ChatGPT': ['C13', 'C14', 'C45', 'C47', 'C127', 'C46', 'C76', 'C78', 'C128'], 
        'Claude': ['C13', 'C14', 'C16', 'C45', 'C78', 'C128'],
        'Gemini': ['C13', 'C14', 'C15', 'C45', 'C76'],
        'MS Copilot Agent': ['C13', 'C14', 'C15', 'C45', 'C46', 'C76', 'C78', 'C127'],
        'Perplexity': ['C14', 'C15', 'C45', 'C76']
    }

    model_total_extracted = {
        'ChatGPT': 15,
        'Claude': 12,
        'Gemini': 9,
        'MS Copilot Agent': 13,
        'Perplexity': 30
    }

    results = []
    
    tier_a_gold = ['C13', 'C45', 'C46', 'C47', 'C76', 'C78', 'C126', 'C127', 'C128', 'C129', 'C130', 'C132', 'C133']

    for model in models:
        matched_ids = model_matches[model]
        tp = len(matched_ids)
        total_extracted = model_total_extracted[model]
        
        recall = tp / gold_total if gold_total > 0 else 0
        precision = tp / total_extracted if total_extracted > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        hallucination_rate = (total_extracted - tp) / total_extracted if total_extracted > 0 else 0
        
        tier_a_matched = len([i for i in matched_ids if i in tier_a_gold])
        tier_a_recall = tier_a_matched / len(tier_a_gold)
        
        results.append({
            'Model': model,
            'Recall': recall,
            'Precision': precision,
            'F1 Score': f1,
            'Tier A Recall': tier_a_recall,
            'Hallucination Rate': hallucination_rate
        })

    df = pd.DataFrame(results)
    
    os.makedirs('Metrics', exist_ok=True)
    df.to_csv('Metrics/llm_summary_metrics.csv', index=False)
    print("Metrics written successfully.")
    print(df.to_string())

if __name__ == "__main__":
    run_evaluation()
