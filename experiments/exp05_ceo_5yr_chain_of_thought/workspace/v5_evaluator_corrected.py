import sys, io, os, re, pandas as pd, numpy as np
from docx import Document
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# COMPLETE FIXED EVALUATOR with all bugs corrected:
# Bug 1: Header rows from tables were included in total_extracted (inflating hallucination rate)
# Bug 2: Ambiguous core names ('mary', 'richard', 'anne', 'paviter') could match falsely
#         - Fixed by requiring core_name to be >= 2 words OR >= 8 chars
# Bug 3: Completeness always = 1.0 because table rows joined by ' → '
#         always have 7 non-empty segments. Fixed by checking actual field values.

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

def is_reliable_core(core_name):
    """Require at least 2 words or 8+ chars to avoid ambiguous matches like 'mary', 'richard'."""
    words = core_name.strip().split()
    return len(words) >= 2 or len(core_name) >= 8

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
            core_name = issue.split('-')[0].split('(')[0].strip().lower()
            gold_items.append({
                'id': item_id,
                'hospital': hospital,
                'issue': issue,
                'core_name': core_name,
                'reliable': is_reliable_core(core_name),
                'date': str(date_val).strip(),
                'tier': tier
            })
    return gold_items

def extract_items_from_model(model):
    """Returns list of parsed items (dicts), excluding table header rows."""
    model_dir = os.path.join(LLM_DIR, model)
    extracted = []
    
    if not os.path.exists(model_dir):
        return extracted
    
    for root, dirs, files in os.walk(model_dir):
        for f in files:
            if f.endswith('.docx') and not f.startswith('~'):
                doc = Document(os.path.join(root, f))
                
                # Paragraph-level: capture arrow/pipe lines
                for para in doc.paragraphs:
                    txt = para.text.strip()
                    if not txt: continue
                    if chr(0x2192) in txt or '->' in txt:
                        parts = [p.strip() for p in re.split(r'→|->', txt)]
                        # Skip if this looks like a header
                        if parts[0].lower() in ['hospital', 'issue']:
                            continue
                        extracted.append({'raw': txt, 'parts': parts, 'source': 'para'})
                    elif '|' in txt:
                        parts = [p.strip() for p in txt.split('|')]
                        if parts[0].lower() in ['hospital', 'issue']:
                            continue
                        extracted.append({'raw': txt, 'parts': parts, 'source': 'para'})
                
                # Table-level: read structured table rows, SKIP header rows
                for table in doc.tables:
                    for i, row in enumerate(table.rows):
                        cells = [c.text.strip() for c in row.cells]
                        # Skip header rows (first row, or rows where first cell is 'Hospital')
                        if cells[0].lower() in ['hospital', 'issue', '']:
                            continue
                        txt = ' → '.join(cells)
                        extracted.append({'raw': txt, 'parts': cells, 'source': 'table'})
    
    return extracted

def evaluate():
    gold = parse_gold()
    total_gold = len(gold)
    tier_counts = {'Tier 1': 0, 'Tier 2': 0, 'Tier 3': 0}
    for g in gold:
        tier_counts[g['tier']] += 1

    results = []
    match_details = {}
    
    for model in models:
        items = extract_items_from_model(model)
        total_extracted = len(items)
        
        # Format consistency: has >= 5 parts (hospital, issue, blurb, date, source)
        consistent = sum(1 for x in items if len(x['parts']) >= 5)
        consistency = consistent / total_extracted if total_extracted > 0 else 0
        
        # Completeness: check actual field values are not empty/TBD/N/A
        completeness_scores = []
        for item in items:
            non_empty = sum(1 for p in item['parts'] 
                           if p.lower() not in ['n/a', 'tbd', 'none', 'unknown', '-', '', 'nan'])
            completeness_scores.append(non_empty / max(len(item['parts']), 1))
        mean_completeness = np.mean(completeness_scores) if completeness_scores else 0
        
        # Match against gold - require reliable core names only
        matched_gold_ids = set()
        field_accuracies = []
        specificities = []
        model_matches = []
        
        for item in items:
            raw_lower = item['raw'].lower()
            parts = item['parts']
            item_hosp = parts[0].lower() if parts else ''
            item_issue = parts[1].lower() if len(parts) > 1 else raw_lower
            item_date  = parts[3].lower() if len(parts) > 3 else ''
            
            best_match = None
            for g in gold:
                if not g['reliable']:
                    continue  # Skip ambiguous gold items for matching
                if g['id'] in matched_gold_ids:
                    continue  # Already matched, don't double-count
                core = g['core_name']
                # Match: core name appears in the extracted row AND hospital matches
                core_found = core in item_issue or core in raw_lower
                hosp_found = g['hospital'] in item_hosp or g['hospital'] in raw_lower
                if core_found and hosp_found:
                    best_match = g
                    break
            
            if best_match:
                matched_gold_ids.add(best_match['id'])
                model_matches.append({'gold_id': best_match['id'], 'extracted': item['raw'][:100]})
                
                # Field-level accuracy: date year present + role keyword present
                date_year = str(best_match['date'])[:4]
                date_acc = 1 if date_year in item_date or date_year in item['raw'] else 0
                
                role_words = [w for w in best_match['issue'].lower().split()
                             if len(w) > 4 and w not in ['incoming', 'outgoing', 'president']]
                role_acc = 1
                for w in role_words[:2]:
                    if w not in item_issue and w not in raw_lower:
                        role_acc = 0
                        break
                
                field_accuracies.append((date_acc + role_acc) / 2.0)
                specificities.append(role_acc)
        
        match_details[model] = model_matches
        
        tp = len(matched_gold_ids)
        t1_tp = len([g for g in gold if g['id'] in matched_gold_ids and g['tier'] == 'Tier 1'])
        t2_tp = len([g for g in gold if g['id'] in matched_gold_ids and g['tier'] == 'Tier 2'])
        t3_tp = len([g for g in gold if g['id'] in matched_gold_ids and g['tier'] == 'Tier 3'])
        
        recall    = tp / total_gold if total_gold > 0 else 0
        precision = tp / total_extracted if total_extracted > 0 else 0
        f1        = 2*(precision*recall)/(precision+recall) if (precision+recall) > 0 else 0
        hall_rate = (total_extracted - tp) / total_extracted if total_extracted > 0 else 0
        omit_rate = 1.0 - recall
        
        results.append({
            'Model': model,
            'Total Extracted': total_extracted,
            'Recall': recall,
            'Precision': precision,
            'F1 Score': f1,
            'Hallucination Rate': hall_rate,
            'Omission Rate': omit_rate,
            'Tier 1 Recall': t1_tp / tier_counts['Tier 1'] if tier_counts['Tier 1'] > 0 else 0,
            'Tier 2 Recall': t2_tp / tier_counts['Tier 2'] if tier_counts['Tier 2'] > 0 else 0,
            'Tier 3 Recall': t3_tp / tier_counts['Tier 3'] if tier_counts['Tier 3'] > 0 else 0,
            'Field-level Accuracy': np.mean(field_accuracies) if field_accuracies else 0,
            'Specificity': np.mean(specificities) if specificities else 0,
            'Completeness': mean_completeness,
            'Consistency': consistency
        })
        
        print(f"\n=== {model}: {tp} TPs out of {total_extracted} extracted ===")
        for m in model_matches:
            print(f"  MATCH {m['gold_id']}: {m['extracted'][:100]}")
    
    df = pd.DataFrame(results)
    print("\n\n=== FINAL CORRECTED METRICS ===")
    print(df[['Model','Total Extracted','Recall','Precision','F1 Score','Hallucination Rate']].to_string())
    
    os.makedirs('Metrics', exist_ok=True)
    df.to_csv('Metrics/v5_metrics_corrected.csv', index=False)
    print("\nSaved to v5_metrics_corrected.csv")

if __name__ == '__main__':
    evaluate()
