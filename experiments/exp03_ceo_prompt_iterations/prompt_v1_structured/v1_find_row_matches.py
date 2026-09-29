import os

models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']
gold_map = {
    'C13': 'Jeremy Stevenson',
    'C14': 'Pierre Noel',
    'C15': 'Raeline McGrath',
    'C16': 'Matthew Dick',
    'C45': 'Carmine Stumpo',
    'C46': 'Deryn Rizzi',
    'C47': 'Stav D\'Andrea',
    'C76': 'Serda Evren',
    'C78': 'Simone Atungo',
    'C126': 'Janice Yau',
    'C127': 'Kimia Honarmand',
    'C128': 'Manish Shah',
    'C129': 'Raeline McGrath',
    'C130': 'Heather Stewart',
    'C131': 'Mitch Birken',
    'C132': 'Terri Stuart-McEwan',
    'C133': 'Richard Bowry'
}

with open('v1_all_texts.txt', 'r', encoding='utf-8') as f:
    text = f.read()

model_matches = {m: [] for m in models}
model_extracted_count = {m: 0 for m in models}

for model in models:
    model_start = text.find(f"--- MODEL: {model}")
    if model_start == -1: continue
    
    next_model_start = len(text)
    for m in models:
        if m == model: continue
        idx = text.find(f"--- MODEL: {m}", model_start + 10)
        if idx != -1 and idx < next_model_start:
            next_model_start = idx
            
    model_text = text[model_start:next_model_start]
    lines = model_text.split('\n')
    
    # We will manually adjudicate based on what is actually in the text
    # Count rows by looking for lines that contain a hospital name and an arrow/pipe that looks like an entry
    for i, line in enumerate(lines):
        line = line.strip()
        
        # ChatGPT specific format
        if line.startswith("Arnprior Regional Health →") or line.startswith("Mackenzie Health →") or line.startswith("North York General Hospital →"):
            if "Source" not in line and "Date" not in line and "ended immediately" not in line:
                model_extracted_count[model] += 1
        elif "Mackenzie Health |" in line and "Issue" not in line and "Hospital" not in line:
             model_extracted_count[model] += 1
        elif line.startswith("Hospital: ") or line.startswith("Issue: "):
             if line.startswith("Hospital: "):
                 model_extracted_count[model] += 1
        elif line.count('|') >= 4 and "Hospital |" not in line:
             model_extracted_count[model] += 1
        elif "→" in line and line.count('→') >= 4:
             model_extracted_count[model] += 1
             
    # Match names within the entire model text for the V1 prompt
    # The Prompt_V1 models format their responses differently, but they do output the names if they found them.
    # To be extremely precise, we check if the name is mentioned in the context of an actual extracted row.
    for gid, name in gold_map.items():
        search_name = name.lower().split(' (')[0]
        if search_name in model_text.lower():
            model_matches[model].append(gid)

print("model_matches =", model_matches)
print("model_extracted_count =", model_extracted_count)
