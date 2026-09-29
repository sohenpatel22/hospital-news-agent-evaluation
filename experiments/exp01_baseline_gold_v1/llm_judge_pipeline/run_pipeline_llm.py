"""
run_pipeline_llm.py
===================
Master runner for the LLM evaluation pipeline.
Runs all 6 stages in sequence.

Usage:
  python run_pipeline_llm.py              # full run (uses cache)
  python run_pipeline_llm.py --force      # force re-run all LLM calls
  python run_pipeline_llm.py --skip-llm  # skip LLM stages, run deterministic only
"""

import sys
import time
import pathlib

BASE = pathlib.Path(__file__).parent

def run(script_name, force=False, skip_llm=False):
    import subprocess
    args = [sys.executable, str(BASE / script_name)]
    if force and script_name in ("01_llm_extract.py", "02_llm_judge.py"):
        args.append("--force")
    if skip_llm and script_name in ("01_llm_extract.py", "02_llm_judge.py"):
        print(f"\n  [SKIP] {script_name} (--skip-llm mode)")
        return
    print(f"\n{'='*60}\nRunning {script_name}\n{'='*60}")
    result = subprocess.run(args, cwd=str(BASE))
    if result.returncode != 0:
        print(f"ERROR in {script_name}. Aborting.")
        sys.exit(result.returncode)

def main():
    force = "--force" in sys.argv
    skip_llm = "--skip-llm" in sys.argv
    
    print("Ontario Health — LLM Evaluation Pipeline")
    print(f"Mode: {'force re-run' if force else 'skip-llm' if skip_llm else 'cached'}")
    start = time.time()
    
    # Create subdirs
    for d in ["extracted_events", "judge_scores", "metrics", "visualizations", "final"]:
        (BASE / d).mkdir(exist_ok=True)
    
    run("01_llm_extract.py", force=force, skip_llm=skip_llm)
    run("02_llm_judge.py", force=force, skip_llm=skip_llm)
    run("03_deterministic_score.py")
    run("04_combine_results.py")
    run("05_visualize_llm.py")
    run("06_final_report_llm.py")
    
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Pipeline complete in {elapsed:.1f}s")
    print(f"Final report: {BASE / 'final' / 'Evaluation_Results_LLM.xlsx'}")
    print(f"Visualizations: {BASE / 'visualizations'}/")

if __name__ == "__main__":
    main()
