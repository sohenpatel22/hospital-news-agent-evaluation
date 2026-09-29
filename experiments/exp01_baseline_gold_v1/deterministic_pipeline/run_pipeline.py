import os
import subprocess
import sys
import time

def run_script(script_name):
    print(f"\n{'='*50}\nRunning {script_name}\n{'='*50}")
    result = subprocess.run([sys.executable, script_name], cwd=os.path.dirname(os.path.abspath(__file__)))
    if result.returncode != 0:
        print(f"Error executing {script_name}. Aborting pipeline.")
        sys.exit(result.returncode)

def main():
    print("Starting Antigravity Evaluation Pipeline...")
    start_time = time.time()
    
    scripts = [
        "01_prepare_gold.py",
        "02_extract_docx.py",
        "03_parse_events.py",
        "04_score.py",
        "05_visualize.py",
        "06_final_report.py"
    ]
    
    for script in scripts:
        run_script(script)
        
    duration = time.time() - start_time
    print(f"\nPipeline completed successfully in {duration:.2f} seconds.")
    print("Check the 'final/Evaluation_Results.xlsx' file for the complete report.")

if __name__ == "__main__":
    main()
