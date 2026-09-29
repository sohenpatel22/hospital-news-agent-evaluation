import os

models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']

# New Gold items
gold_map = {
    'C13': 'Carmine Stumpo',
    'C34': 'Jeremy Stevenson',
    'C35': 'Raeline McGrath',
    'C36': 'Pierre Noel',
    'C76': 'Kristina Fanjoy',
    'C103': 'Manish Shah',
    'C124': 'Serda Evren'
}

with open('v2_all_texts.txt', 'r', encoding='utf-8') as f:
    text = f.read()

model_matches = {m: [] for m in models}

for model in models:
    model_start = text.find(f"--- MODEL: {model}")
    if model_start == -1: continue
    
    next_model_start = len(text)
    for m in models:
        if m == model: continue
        idx = text.find(f"--- MODEL: {m}", model_start + 10)
        if idx != -1 and idx < next_model_start:
            next_model_start = idx
            
    model_text = text[model_start:next_model_start].lower()
    
    for gid, name in gold_map.items():
        search_name = name.lower().split(' (')[0]
        if search_name in model_text:
            model_matches[model].append(gid)

print("Automated matches:")
print(model_matches)
