import pandas as pd
import json

file_path = "../gold/CEO_Gold_Dataset.xlsx"
xls = pd.ExcelFile(file_path)

gold_data = []

# Similar logic as before: header might be on row 1 instead of row 0
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    # Print columns to see the structure
    print(f"Sheet '{sheet}' columns: {df.columns.tolist()}")
    
    # Just dump the first few rows to understand structure
    print(df.head(5).to_dict(orient='records'))
