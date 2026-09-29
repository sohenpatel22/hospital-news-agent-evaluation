import os

models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']

# Gold items mapping
gold_map = {
    'C13': 'Jeremy Stevenson',
    'C14': 'Pierre Noel',
    'C15': 'Raeline McGrath (Acting CEO)',
    'C16': 'Matthew Dick',
    'C45': 'Carmine Stumpo',
    'C46': 'Deryn Rizzi',
    'C47': 'Stav D\'Andrea',
    'C76': 'Serda Evren',
    'C78': 'Simone Atungo',
    'C126': 'Janice Yau',
    'C127': 'Kimia Honarmand',
    'C128': 'Manish Shah',
    'C129': 'Raeline McGrath (CNO)',
    'C130': 'Heather Stewart',
    'C131': 'Mitch Birken',
    'C132': 'Terri Stuart-McEwan',
    'C133': 'Richard Bowry'
}

with open('v1_all_texts.txt', 'r', encoding='utf-8') as f:
    text = f.read()

for model in models:
    print(f"--- {model} ---")
    model_start = text.find(f"--- MODEL: {model}")
    if model_start == -1: continue
    
    # find next model start
    next_model_start = len(text)
    for m in models:
        if m == model: continue
        idx = text.find(f"--- MODEL: {m}", model_start + 10)
        if idx != -1 and idx < next_model_start:
            next_model_start = idx
            
    model_text = text[model_start:next_model_start].lower()
    
    for gid, name in gold_map.items():
        search_name = name.lower().split(' (')[0] # remove parentheticals
        if search_name in model_text:
            print(f"  {gid} ({name}): FOUND")
        else:
            print(f"  {gid} ({name}): NOT found")
    print("\n")
