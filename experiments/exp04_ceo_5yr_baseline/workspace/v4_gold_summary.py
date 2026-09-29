import pandas as pd
import json

file_path = "../gold/CEO_Gold_Dataset.xlsx"
xls = pd.ExcelFile(file_path)

out = []
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet, header=1)
    out.append(f"Sheet: {sheet}")
    out.append(f"Columns: {list(df.columns)}")
    out.append(f"Number of items: {len(df)}")
    out.append(f"First 2 items:\n{df.head(2).to_dict(orient='records')}")
    out.append("-" * 40)

with open('v4_gold_summary.txt', 'w') as f:
    f.write("\n".join(out))
