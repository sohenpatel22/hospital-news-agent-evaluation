import os
import pandas as pd
import json

print("=== PART 1 & 3: Inspecting gold.xlsx ===")
file_path = r'eval/data/gold.xlsx'

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
else:
    xls = pd.ExcelFile(file_path)
    print(f"Sheets found: {xls.sheet_names}")
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, header=2)
        print(f"\n--- Sheet: {sheet} ---")
        # Ensure we drop completely empty rows that might be counted
        df.dropna(how='all', inplace=True)
        print(f"Row count (after dropping all-empty rows): {len(df)}")
        print(f"Column names: {list(df.columns)}")
        
        in_scope_col = [col for col in df.columns if 'in_scope' in str(col).lower()]
        if in_scope_col:
            col = in_scope_col[0]
            counts = df[col].astype(str).str.upper().value_counts(dropna=False).to_dict()
            print(f"in_scope counts: {counts}")
        else:
            print("in_scope column not found!")
            
        conf_col = [col for col in df.columns if 'confidence' in str(col).lower() or 'tier' in str(col).lower()]
        if conf_col:
            col = conf_col[0]
            print(f"confidence_tier counts: {df[col].value_counts(dropna=False).to_dict()}")
        elif 'ceo' in sheet.lower():
            print("confidence_tier column not found in ceo sheet!")
            
        date_cols = [col for col in df.columns if 'date' in str(col).lower()]
        if date_cols:
            for d_col in date_cols:
                blank_count = df[d_col].isna().sum()
                print(f"Blank dates in '{d_col}': {blank_count}")
        else:
            print("No column with 'date' in name found!")

print("\n=== PART 2: Walking eval/data/raw ===")
raw_dir = r'eval/data/raw'
for root, dirs, files in os.walk(raw_dir):
    level = root.replace(raw_dir, '').count(os.sep)
    indent = ' ' * 4 * (level)
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 4 * (level + 1)
    for f in files:
        f_path = os.path.join(root, f)
        size = os.path.getsize(f_path)
        print(f"{subindent}{f} ({size} bytes)")
