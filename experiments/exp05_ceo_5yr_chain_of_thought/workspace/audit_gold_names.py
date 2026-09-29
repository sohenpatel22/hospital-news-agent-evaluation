import sys, io, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GOLD_PATH = "../gold/CEO_Gold_Dataset.xlsx"
df = pd.read_excel(GOLD_PATH, header=1)

print("=== GOLD CORE NAMES ===")
for _, row in df.iterrows():
    issue = str(row['name_or_issue'])
    core = issue.split('-')[0].split('(')[0].strip().lower()
    print(f"  {row['item_id']}: core={repr(core)} | hosp={row['hospital']}")
