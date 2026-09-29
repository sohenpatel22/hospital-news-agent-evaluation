import pandas as pd

file_path = "../gold/CEO_Gold_Dataset.xlsx"
df = pd.read_excel(file_path, header=1) # First row is headers

# Filter for date window '2026-01-16' to '2026-07-16'
# But date might be string or datetime
def is_in_window(date_str):
    if pd.isna(date_str):
        return False
    date_str = str(date_str).strip()
    if date_str == 'TBD' or date_str.lower() == 'unknown':
        return False
    try:
        dt = pd.to_datetime(date_str)
        return pd.Timestamp('2026-01-16') <= dt <= pd.Timestamp('2026-07-16')
    except:
        return False

# Also might need to account for items manually identified in V0
print("All items in window:")
for _, row in df.iterrows():
    if is_in_window(row['date (YYYY-MM-DD)']):
        print(f"{row['item_id']}: {row['name_or_issue']} | {row['date (YYYY-MM-DD)']}")
