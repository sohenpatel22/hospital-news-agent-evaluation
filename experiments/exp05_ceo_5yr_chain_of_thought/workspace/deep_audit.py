import sys, io, os, re, pandas as pd
from docx import Document
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# CRITICAL AUDIT CHECKS:
# 1. Ambiguous core names ('mary', 'richard', 'anne', 'paviter') - will cause false matches
# 2. Precision denominator bug: header rows from tables are included
# 3. Table header rows counted as 'extracted' items
# 4. First-match-wins: once a gold item is matched it can't be double-counted but
#    multiple extracted items could claim the same gold item

GOLD_PATH = "../gold/CEO_Gold_Dataset.xlsx"
LLM_DIR = "../raw_responses"

df = pd.read_excel(GOLD_PATH, header=1)

# Check ambiguous core names
print("=== AMBIGUOUS / SHORT CORE NAMES (potential false positive matches) ===")
for _, row in df.iterrows():
    issue = str(row['name_or_issue'])
    core = issue.split('-')[0].split('(')[0].strip().lower()
    if len(core.split()) <= 1 or len(core) < 6:
        print(f"  DANGER: {row['item_id']} core={repr(core)} | full={issue[:60]}")

print()
print("=== HEADER ROW COUNTING BUG ===")
# Check if table header rows ('Hospital -> Issue -> ...') are being counted as extracted items
models = ['ChatGPT', 'Claude', 'Gemini', 'MS Copilot Agent', 'Perplexity']
for model in models:
    model_dir = os.path.join(LLM_DIR, model)
    header_rows = 0
    data_rows = 0
    for root, dirs, files in os.walk(model_dir):
        for f in files:
            if f.endswith('.docx') and not f.startswith('~'):
                doc = Document(os.path.join(root, f))
                for table in doc.tables:
                    for i, row in enumerate(table.rows):
                        txt = ' -> '.join([c.text.strip() for c in row.cells])
                        if i == 0 or 'Hospital' in txt[:20]:
                            header_rows += 1
                        else:
                            data_rows += 1
    print(f"  {model}: header_rows_in_tables={header_rows}, actual_data_rows={data_rows}")
