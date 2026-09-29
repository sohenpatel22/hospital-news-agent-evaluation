"""
04_combine_results.py
=====================
Merges deterministic scores + LLM judge scores into a single unified table.
Normalizes all metrics to 0-1 scale for comparability.
"""

import json
import pathlib
import re
import pandas as pd

BASE = pathlib.Path(__file__).parent
METRICS_DIR = BASE / "metrics"
JUDGE_DIR = BASE / "judge_scores"
OUT_DIR = METRICS_DIR

def slug(s):
    return re.sub(r'[^\w]', '_', str(s))[:50]

def load_judge_scores() -> pd.DataFrame:
    rows = []
    for task_dir in JUDGE_DIR.iterdir():
        if not task_dir.is_dir(): continue
        for model_dir in task_dir.iterdir():
            if not model_dir.is_dir(): continue
            for f in model_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    rows.append({
                        "task": data.get("task", task_dir.name),
                        "model": data.get("model", model_dir.name),
                        "hospital": data.get("hospital", f.stem),
                        "relevance_raw": data.get("relevance"),
                        "relevance": round(data.get("relevance", 0) / 3, 3),  # normalize to 0-1
                        "relevance_reason": data.get("relevance_reason",""),
                        "groundedness_raw": data.get("groundedness"),
                        "groundedness": round(data.get("groundedness", 0) / 3, 3),
                        "groundedness_reason": data.get("groundedness_reason",""),
                        "completeness": data.get("completeness"),
                        "completeness_reason": data.get("completeness_reason",""),
                        "missed_items": "; ".join(data.get("missed_items", [])),
                        "answer_relevancy": data.get("answer_relevancy"),
                        "answer_relevancy_reason": data.get("answer_relevancy_reason",""),
                    })
                except Exception as e:
                    print(f"  Warning: could not load {f}: {e}")
    return pd.DataFrame(rows)


def run_combine():
    print("--- Stage 4: Combining Results ---")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load deterministic scores
    det_path = METRICS_DIR / "deterministic_scores.csv"
    if not det_path.exists():
        print("ERROR: Run 03_deterministic_score.py first.")
        return
    df_det = pd.read_csv(det_path)
    
    # Load judge scores
    df_judge = load_judge_scores()
    
    if df_judge.empty:
        print("Warning: No judge scores found. Run 02_llm_judge.py first.")
        df_combined = df_det.copy()
    else:
        # Merge on task + model + hospital
        df_combined = df_det.merge(
            df_judge,
            on=["task", "model", "hospital"],
            how="left"
        )
    
    # Load citation summary
    cite_path = METRICS_DIR / "citation_analysis.csv"
    if cite_path.exists():
        df_cite = pd.read_csv(cite_path)
        cite_agg = df_cite.groupby(["task","model","hospital"]).agg(
            links_found=("link","count"),
            links_valid=("valid", lambda x: x.sum()),
            avg_credibility_tier=("credibility_tier","mean")
        ).reset_index()
        cite_agg["citation_accuracy"] = (cite_agg["links_valid"] / cite_agg["links_found"]).round(3)
        df_combined = df_combined.merge(cite_agg, on=["task","model","hospital"], how="left")
    
    df_combined.to_csv(OUT_DIR / "combined_scores.csv", index=False)
    print(f"Saved combined_scores.csv ({len(df_combined)} rows)")
    
    # Aggregated tool summary
    agg_cols = ["recall","precision","f1","relevance","groundedness","completeness","answer_relevancy","citation_accuracy"]
    available = [c for c in agg_cols if c in df_combined.columns]
    
    tool_summary = df_combined.groupby(["model","task"])[available].mean().round(3).reset_index()
    tool_summary.to_csv(OUT_DIR / "tool_summary_llm.csv", index=False)
    
    print("\n=== UNIFIED TOOL SUMMARY (averaged across hospitals) ===")
    print(tool_summary.to_string(index=False))
    
    # Overall summary (across all tasks)
    overall = df_combined.groupby("model")[available].mean().round(3)
    overall.to_csv(OUT_DIR / "overall_summary_llm.csv")
    print("\n=== OVERALL SUMMARY (all tasks combined) ===")
    print(overall.to_string())

if __name__ == "__main__":
    run_combine()
