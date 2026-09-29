import os
import re
import pandas as pd
from docx import Document
import numpy as np

GOLD_PATH = "../gold/CEO_Gold_Dataset.xlsx"
LLM_DIR = "../raw_responses"

models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']

def get_tier(issue_text):
    text = str(issue_text).lower()
    if any(x in text for x in ['ceo', 'president', 'chief executive']):
        return 'Tier 1'
    elif any(x in text for x in ['vp', 'vice president', 'cfo', 'cne', 'cco', 'chief nursing', 'chief financial']):
        return 'Tier 2'
    else:
        return 'Tier 3'

def parse_gold():
    xls = pd.ExcelFile(GOLD_PATH)
    gold_items = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, header=1)
        for _, row in df.iterrows():
            item_id = row.get('item_id', 'Unknown')
            if pd.isna(item_id): continue
            
            hospital = str(row.get('hospital', '')).strip().lower()
            issue = str(row.get('name_or_issue', '')).strip()
            date_val = row.get('date (YYYY-MM-DD)', '')
            
            tier = get_tier(issue)
            
            # extract core name for matching
            core_name = issue.split('-')[0].split('(')[0].strip().lower()
            
            gold_items.append({
                'id': item_id,
                'hospital': hospital,
                'issue': issue,
                'core_name': core_name,
                'date': str(date_val).strip(),
                'tier': tier
            })
    return gold_items

def is_valid_format(line):
    # format should be A -> B -> C -> D -> E -> F
    parts = [p.strip() for p in re.split(r'→|->', line)]
    return len(parts) >= 5, parts

def evaluate_models():
    gold = parse_gold()
    total_gold = len(gold)
    
    tier_counts = {'Tier 1': 0, 'Tier 2': 0, 'Tier 3': 0}
    for g in gold:
        tier_counts[g['tier']] += 1
        
    results = []

    for model in models:
        model_dir = os.path.join(LLM_DIR, model)
        extracted_lines = []
        
        # Read all docx
        if os.path.exists(model_dir):
            for root, dirs, files in os.walk(model_dir):
                for file in files:
                    if file.endswith('.docx') and not file.startswith('~'):
                        doc = Document(os.path.join(root, file))
                        for para in doc.paragraphs:
                            txt = para.text.strip()
                            # It's an extracted line if it contains arrow or is long enough and not just conversational text
                            if '→' in txt or '->' in txt or '|' in txt:
                                extracted_lines.append(txt)
                        for table in doc.tables:
                            for row in table.rows:
                                txt = " → ".join([c.text.strip() for c in row.cells])
                                extracted_lines.append(txt)
        
        # Parse extracted lines
        parsed_items = []
        consistent_format_count = 0
        total_extracted = len(extracted_lines)
        
        for line in extracted_lines:
            is_cons, parts = is_valid_format(line)
            if is_cons: consistent_format_count += 1
            
            # Heuristic completeness: fields not TBD, N/A, None, or empty
            complete_fields = 0
            for p in parts:
                if p.lower() not in ['n/a', 'tbd', 'none', 'unknown', '-', '']:
                    complete_fields += 1
            
            hosp = parts[0] if len(parts) > 0 else ""
            issue = parts[1] if len(parts) > 1 else line
            date = parts[3] if len(parts) > 3 else ""
            
            parsed_items.append({
                'raw': line,
                'hospital': hosp.lower(),
                'issue': issue.lower(),
                'date': date.lower(),
                'completeness_ratio': complete_fields / max(len(parts), 1)
            })

        # Match against Gold
        matched_gold_ids = set()
        field_accuracies = []
        specificities = []
        
        for item in parsed_items:
            # Find best gold match
            best_match = None
            for g in gold:
                # If hospital roughly matches and core name is in the issue text
                if (g['core_name'] in item['issue'] or g['core_name'] in item['raw'].lower()):
                    if (g['hospital'] in item['hospital'] or g['hospital'] in item['raw'].lower()):
                        best_match = g
                        break
            
            if best_match:
                matched_gold_ids.add(best_match['id'])
                
                # Check field level accuracy (date and role)
                date_acc = 1 if (str(best_match['date'])[:4] in item['date'] or str(best_match['date'])[:4] in item['raw']) else 0
                
                # Specificity: exact role extraction (e.g., 'CEO', 'Treasurer')
                # Simplistic heuristic: if the first big word of the role is present
                role_words = [w for w in best_match['issue'].lower().split() if len(w) > 3 and w not in ['incoming', 'outgoing']]
                role_acc = 1
                for w in role_words[:2]:
                    if w not in item['issue'] and w not in item['raw'].lower():
                        role_acc = 0
                        break
                
                field_accuracies.append((date_acc + role_acc) / 2.0)
                specificities.append(role_acc)
        
        tp = len(matched_gold_ids)
        
        # Tiered Recall
        t1_tp = len([g for g in gold if g['id'] in matched_gold_ids and g['tier'] == 'Tier 1'])
        t2_tp = len([g for g in gold if g['id'] in matched_gold_ids and g['tier'] == 'Tier 2'])
        t3_tp = len([g for g in gold if g['id'] in matched_gold_ids and g['tier'] == 'Tier 3'])
        
        recall = tp / total_gold if total_gold > 0 else 0
        precision = tp / total_extracted if total_extracted > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        hallucination_rate = (total_extracted - tp) / total_extracted if total_extracted > 0 else 0
        omission_rate = 1.0 - recall
        
        mean_field_acc = np.mean(field_accuracies) if field_accuracies else 0
        mean_specificity = np.mean(specificities) if specificities else 0
        mean_completeness = np.mean([x['completeness_ratio'] for x in parsed_items]) if parsed_items else 0
        consistency = consistent_format_count / total_extracted if total_extracted > 0 else 0
        
        results.append({
            'Model': model,
            'Total Extracted': total_extracted,
            'Recall': recall,
            'Precision': precision,
            'F1 Score': f1,
            'Hallucination Rate': hallucination_rate,
            'Omission Rate': omission_rate,
            'Tier 1 Recall': t1_tp / tier_counts['Tier 1'] if tier_counts['Tier 1'] > 0 else 0,
            'Tier 2 Recall': t2_tp / tier_counts['Tier 2'] if tier_counts['Tier 2'] > 0 else 0,
            'Tier 3 Recall': t3_tp / tier_counts['Tier 3'] if tier_counts['Tier 3'] > 0 else 0,
            'Field-level Accuracy': mean_field_acc,
            'Specificity': mean_specificity,
            'Completeness': mean_completeness,
            'Consistency': consistency
        })

    df = pd.DataFrame(results)
    os.makedirs('Metrics', exist_ok=True)
    df.to_csv('Metrics/v4_metrics.csv', index=False)
    print("Metrics written successfully.")
    print(df.to_string())

if __name__ == "__main__":
    evaluate_models()
