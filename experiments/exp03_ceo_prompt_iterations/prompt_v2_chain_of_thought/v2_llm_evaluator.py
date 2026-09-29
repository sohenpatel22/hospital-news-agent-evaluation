import os
import pandas as pd

def run_evaluation():
    # Matches verified from Prompt_V2 (Chain-of-Thought) responses — corrected 2026-09-04
    # Text extracted from: Raw LLM Responses/prompt_v2
    # Gold items in 6-month window (Jan 16 – Jul 16, 2026):
    # C13: Carmine Stumpo (Tier A)
    # C34: Jeremy Stevenson (Tier A)
    # C35: Raeline McGrath (Tier A)
    # C36: Pierre Noel (Tier A)
    # C76: Kristina Fanjoy (Non-Tier A)
    # C103: Dr. Manish Shah (Non-Tier A)
    # C124: Serda Evren (Tier A)

    gold_total = 7
    tier_a_gold = ['C13', 'C34', 'C35', 'C36', 'C124']

    models = ['ChatGPT', 'Claude', 'Gemini', 'Perplexity', 'MS Copilot Agent']

    # Matches from automated v2_find_matches.py against CORRECTED CoT responses
    model_matches = {
        'ChatGPT':        ['C13', 'C34', 'C35', 'C36', 'C76', 'C124'],
        'Claude':         ['C13', 'C34', 'C36', 'C124'],
        'Gemini':         [],
        'Perplexity':     ['C13', 'C34', 'C35', 'C36', 'C76', 'C124'],
        'MS Copilot Agent': ['C13', 'C34', 'C35', 'C36'],
    }

    # Total rows extracted per model from CoT responses (hospital-name rows with arrows)
    model_total_extracted = {
        'ChatGPT':        53,
        'Claude':         21,
        'Gemini':         8,
        'Perplexity':     66,
        'MS Copilot Agent': 21,
    }

    results = []
    
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
