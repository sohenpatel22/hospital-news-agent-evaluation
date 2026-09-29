import json
import re
import os
import difflib
import pandas as pd
from datetime import datetime

def load_gold():
    with open('Gold_Parsed/gold.json', 'r', encoding='utf-8') as f:
        raw_gold = json.load(f)
    
    header_row = None
    for item in raw_gold:
        if item.get('Unnamed: 0') == 'item_id' or item.get('Unnamed: 1') == 'task':
            header_row = item
            break
            
    key_map = {k: str(v) for k, v in header_row.items() if v}
    gold = []
    for item in raw_gold:
        if item == header_row or item.get('Unnamed: 0') == 'item_id': continue
        if not item.get('Unnamed: 0') or str(item.get('Unnamed: 0')).lower() == 'nan': continue
        clean_item = {}
        for k, v in item.items():
            if k in key_map:
                clean_item[key_map[k]] = v
        gold.append(clean_item)
    return gold

def normalize_name(name):
    if not name: return ""
    name = name.lower()
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'[^a-z0-9\s]', '', name)
    for prefix in ['dr ', 'dr. ']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()

def match_entity(sys_item, gold_item):
    # Match Hospital
    gold_aliases = [a.strip().lower() for a in gold_item.get('hospital_aliases', '').split(';')]
    sys_hosp = sys_item.get('Hospital', '').strip().lower()
    if sys_hosp not in gold_aliases and not any(ga in sys_hosp for ga in gold_aliases):
        return False
        
    # Match Name
    gold_name_raw = gold_item.get('name_or_issue', '').split(' - ')[0]
    gold_name = normalize_name(gold_name_raw)
    gold_words = gold_name.split()
    if not gold_words: return False
    
    combined_sys = normalize_name(sys_item.get('Issue', '')) + " " + normalize_name(sys_item.get('Paragraph blurb', ''))
    
    match_count = sum(1 for gw in gold_words if len(gw) > 2 and gw in combined_sys)
    valid_words = [gw for gw in gold_words if len(gw) > 2]
    
    if len(valid_words) > 0 and match_count >= len(valid_words) * 0.5:
        return True
    return False

def evaluate():
    gold = load_gold()
    in_scope_gold = [g for g in gold if str(g.get('in_scope')).strip().upper() == 'TRUE']
    models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']
    
    metrics = []
    
    for model in models:
        path = f"Parsed_Responses/{model}.json"
        if not os.path.exists(path): continue
        with open(path, 'r', encoding='utf-8') as f:
            sys_items = json.load(f)
            
        run1_items = [i for i in sys_items if i.get('_meta', {}).get('run') == 'Run 1']
        if not run1_items:
            run1_items = sys_items
            
        # Matching
        matched_sys = []
        unmatched_sys = []
        matched_gold_ids = set()
        
        for s_item in run1_items:
            match_found = False
            for g_item in gold:
                if str(g_item.get('in_scope')).strip().upper() == 'FALSE': continue
                if match_entity(s_item, g_item):
                    matched_sys.append((s_item, g_item))
                    matched_gold_ids.add(g_item.get('item_id'))
                    match_found = True
                    break
            if not match_found:
                unmatched_sys.append(s_item)
                
        # Metrics Calculation
        
        # 1. Recall by Tier
        tier_a_gold = [g for g in in_scope_gold if g.get('confidence_tier', '').startswith('A')]
        tier_b_gold = [g for g in in_scope_gold if g.get('confidence_tier', '').startswith('B')]
        tier_c_gold = [g for g in in_scope_gold if g.get('confidence_tier', '').startswith('C')]
        
        recall_a = len([g for g in tier_a_gold if g.get('item_id') in matched_gold_ids]) / max(len(tier_a_gold), 1)
        recall_b = len([g for g in tier_b_gold if g.get('item_id') in matched_gold_ids]) / max(len(tier_b_gold), 1)
        recall_c = len([g for g in tier_c_gold if g.get('item_id') in matched_gold_ids]) / max(len(tier_c_gold), 1)
        
        recall_overall = len(matched_gold_ids) / max(len(in_scope_gold), 1)
        
        # Recall (Independent Subset)
        independent_gold = [g for g in in_scope_gold if 'NEWLY ADDED' in str(g.get('status', ''))]
        recall_independent = len([g for g in independent_gold if g.get('item_id') in matched_gold_ids]) / max(len(independent_gold), 1)
        
        # Precision & Hallucination
        # Simplify adjudication: count unmatched as Hallucinations (Bucket B) for this automated pass
        precision = len(matched_sys) / max(len(run1_items), 1)
        f1 = 2 * (precision * recall_overall) / max((precision + recall_overall), 0.0001)
        hallucination_rate = len(unmatched_sys) / max(len(run1_items), 1)
        
        # Specificity & Omission
        specificity_scores = []
        omission_count = 0
        for s_item, g_item in matched_sys:
            # Score 0-3
            score = 0
            date_str = s_item.get('Date', '')
            if re.search(r'\b\d{4}-\d{2}-\d{2}\b|\b[A-Z][a-z]+ \d{1,2}, \d{4}\b', date_str): score += 1
            if s_item.get('Source') and s_item.get('Source') != 'Source link': score += 1
            if s_item.get('Issue'): score += 1
            specificity_scores.append(score)
            
            # Omission
            if not s_item.get('Issue') or not s_item.get('Date') or not s_item.get('Source link'):
                omission_count += 1
                
        mean_specificity = sum(specificity_scores) / max(len(specificity_scores), 1)
        spec_3_percent = len([s for s in specificity_scores if s == 3]) / max(len(specificity_scores), 1)
        omission_rate = omission_count / max(len(matched_sys), 1)
        
        metrics.append({
            'Model': model,
            'Recall (Overall)': recall_overall,
            'Recall (Tier A)': recall_a,
            'Recall (Tier C)': recall_c,
            'Recall (Indep)': recall_independent,
            'Precision': precision,
            'F1': f1,
            'Hallucination Rate': hallucination_rate,
            'Mean Specificity': mean_specificity,
            '% Specificity=3': spec_3_percent,
            'Omission Rate': omission_rate
        })

    df = pd.DataFrame(metrics)
    df.to_csv('Metrics/summary_metrics.csv', index=False)
    print(df.to_string())

if __name__ == '__main__':
    evaluate()
