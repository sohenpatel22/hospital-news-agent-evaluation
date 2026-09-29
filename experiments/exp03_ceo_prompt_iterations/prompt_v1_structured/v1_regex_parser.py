import re
import json
import os

with open('v1_all_texts.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

parsed = {}
current_model = None

for line in lines:
    line = line.strip()
    if line.startswith('--- MODEL:'):
        current_model = line.split('|')[0].replace('--- MODEL:', '').strip()
        if current_model not in parsed:
            parsed[current_model] = []
        continue
        
    if not current_model:
        continue
        
    # Pattern 1: Hospital → Issue → Blurb → Date → Source → Link
    if line.count('→') >= 3:
        parts = [p.strip() for p in line.split('→')]
        # Some models append confidence tag at the end, so parts might be > 6
        if len(parts) >= 5:
            item = {
                "Hospital": parts[0],
                "Issue": parts[1],
                "Paragraph blurb": parts[2] if len(parts) > 5 else "",
                "Date": parts[-3] if len(parts) >= 6 else parts[-2],
                "Source": parts[-2] if len(parts) >= 6 else parts[-1],
                "Source link": parts[-1] if len(parts) >= 6 else ""
            }
            parsed[current_model].append(item)
            
    # Pattern 2: Hospital | Issue | Blurb | Date | Source | Link
    elif line.count('|') >= 4 and "Hospital |" not in line and "Issue |" not in line:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 5:
            item = {
                "Hospital": parts[0],
                "Issue": parts[1],
                "Paragraph blurb": parts[2] if len(parts) > 5 else "",
                "Date": parts[-3] if len(parts) >= 6 else parts[-2],
                "Source": parts[-2] if len(parts) >= 6 else parts[-1],
                "Source link": parts[-1] if len(parts) >= 6 else ""
            }
            parsed[current_model].append(item)

os.makedirs('Parsed_Responses', exist_ok=True)
for model, items in parsed.items():
    with open(f'Parsed_Responses/{model}_llm.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=4)
    print(f"Parsed {len(items)} for {model}")
