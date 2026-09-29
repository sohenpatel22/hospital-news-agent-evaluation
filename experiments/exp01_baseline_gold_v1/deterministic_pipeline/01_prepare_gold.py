import os
import pandas as pd
import sys

def prepare_gold():
    print("--- Phase 2: Preparing Gold Dataset ---")
    
    input_file = r"../data/Gold Standard Dataset - Compact Version.xlsx"
    out_dir = "gold"
    
    # Read sheets
    df_phipa = pd.read_excel(input_file, sheet_name="PHIPA")
    df_ceo = pd.read_excel(input_file, sheet_name="CEOs")
    df_sup = pd.read_excel(input_file, sheet_name="Supervisor")
    
    print(f"Loaded PHIPA: {len(df_phipa)} rows")
    print(f"Loaded CEO: {len(df_ceo)} rows")
    print(f"Loaded Supervisor: {len(df_sup)} rows")
    
    all_dfs = [df_phipa, df_ceo, df_sup]
    for df in all_dfs:
        # Standardize empty values
        df.replace({float('nan'): None, pd.NaT: None}, inplace=True)
        # Ensure item_id is string
        df['item_id'] = df['item_id'].astype(str)
        # Clean dates if they are datetime objects
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            df['date'].replace({'NaT': None}, inplace=True)

    df_all = pd.concat(all_dfs, ignore_index=True)
    
    # Validations
    print("Running validations...")
    
    # 1. No duplicate item_ids
    dupes = df_all[df_all.duplicated('item_id', keep=False)]
    if not dupes.empty:
        print(f"WARNING: Found duplicate item_ids: {dupes['item_id'].tolist()}")
    else:
        print("PASS: No duplicate item_ids")
        
    # 2. Check for expected hospitals
    expected_hospitals = [
        "Stevenson Memorial Hospital", "Renfrew Victoria Hospital", "Sault Area Hospital",
        "Sante Manitouwadge Health", "Sinai Health System", "London Health Sciences Centre",
        "William Osler Health System", "The Ottawa Hospital", "Anson General Hospital",
        "Geraldton District Hospital", "Baycrest Health Sciences", "Hamilton Health Sciences",
        "Mackenzie Health", "Arnprior Regional Health", "Sensenbrenner Hospital",
        "Red Lake Margaret Cochenour Memorial Hospital", "North York General Hospital",
        "Windsor Regional Hospital"
    ]
    # In the compact dataset, Hamilton Health Sciences Corporation might be Hamilton Health Sciences
    expected_hospitals_normalized = [h.lower().replace("corporation", "").strip() for h in expected_hospitals]
    
    actual_hospitals = df_all['hospital'].dropna().unique()
    actual_normalized = [h.lower().replace("corporation", "").strip() for h in actual_hospitals]
    
    missing = set(expected_hospitals_normalized) - set(actual_normalized)
    if missing:
        print(f"WARNING: Missing expected hospitals: {missing}")
    else:
        print("PASS: All 18 target hospitals present (or aliases)")

    # Write out to gold directory
    df_phipa.to_csv(os.path.join(out_dir, "phipa_gold.csv"), index=False)
    df_ceo.to_csv(os.path.join(out_dir, "ceo_gold.csv"), index=False)
    df_sup.to_csv(os.path.join(out_dir, "supervisor_gold.csv"), index=False)
    df_all.to_csv(os.path.join(out_dir, "all_gold.csv"), index=False)
    
    print(f"Successfully saved processed CSVs to {out_dir}/")
    
if __name__ == "__main__":
    prepare_gold()
