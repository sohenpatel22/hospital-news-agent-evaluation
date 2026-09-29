import os
import pandas as pd

def create_final_report():
    print("--- Phase 7: Final Workbook ---")
    
    out_dir = "final"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "Evaluation_Results.xlsx")
    
    metrics_dir = "metrics"
    files_to_include = {
        "Tool Summary": "tool_summary.csv",
        "Hospital Summary": "hospital_summary.csv",
        "Item Level Results": "item_level_results.csv",
        "Consistency": "consistency_results.csv",
        "Citation Analysis": "citation_analysis.csv"
    }
    
    # Use pandas ExcelWriter
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        for sheet_name, file_name in files_to_include.items():
            csv_path = os.path.join(metrics_dir, file_name)
            if not os.path.exists(csv_path):
                print(f"Warning: {csv_path} not found. Skipping sheet.")
                continue
                
            df = pd.read_csv(csv_path)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Formatting
            worksheet = writer.sheets[sheet_name]
            
            # Freeze top row
            worksheet.freeze_panes = "A2"
            
            # Auto-fit columns roughly
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter # Get the column name
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50) # Cap width at 50
                worksheet.column_dimensions[column].width = adjusted_width

    print(f"Done. Final report saved to {out_file}")

if __name__ == "__main__":
    create_final_report()
