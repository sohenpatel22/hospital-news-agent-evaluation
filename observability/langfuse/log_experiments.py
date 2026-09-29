"""Log every experiment's metrics to Langfuse (one trace per experiment x system x task).

Each trace carries:
  - name      : "<experiment>/<prompt_version>/<system>/<task>"
  - session_id: experiment id (groups a whole experiment in the Sessions view)
  - tags      : experiment, prompt version, system, task, gold version
  - scores    : every metric (recall, precision, f1, hallucination_rate, ...)
  - metadata  : gold dataset, window, CI bounds, source file

Usage (from repo root):
    python observability/langfuse/log_experiments.py --dry-run      # print what would be sent
    python observability/langfuse/log_experiments.py                # send to Langfuse

Credentials are read from the environment / a local .env (never committed):
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
Re-running is idempotent: trace ids are deterministic, so scores are overwritten, not duplicated.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "experiments"

SYSTEM_ALIASES = {"MS Copilot Agent": "MS Copilot Agent"}


def _num(row, cols):
    out = {}
    for c in cols:
        v = row.get(c)
        if pd.notna(v) and isinstance(v, (int, float)):
            out[c] = float(v)
    return out


def _slug(s):
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(s)).strip("_")


def _from_model_csv(path, experiment, prompt_version, gold, task, window, model_col="Model"):
    df = pd.read_csv(path)
    recs = []
    for _, r in df.iterrows():
        metrics = {_slug(c): float(r[c]) for c in df.columns
                   if c != model_col and pd.notna(r[c]) and isinstance(r[c], (int, float))}
        recs.append(dict(experiment=experiment, prompt_version=prompt_version, system=r[model_col],
                         task=task, gold=gold, window=window, source=str(path.relative_to(REPO)),
                         metrics=metrics))
    return recs


def collect():
    recs = []

    # exp01 -- baseline gold v1, deterministic scoring + LLM-as-judge (per prompt version / task)
    p = EXP / "exp01_baseline_gold_v1/deterministic_pipeline/metrics/tool_summary.csv"
    df = pd.read_csv(p)
    for _, r in df.iterrows():
        recs.append(dict(experiment="exp01_baseline_gold_v1", prompt_version=r["prompt_version"],
                         system=r["tool"], task=r["task"], gold="v1_baseline", window="v1",
                         source=str(p.relative_to(REPO)),
                         metrics=_num(r, ["recall", "precision", "f1", "hallucination_rate",
                                          "total_gold", "total_extracted", "total_matched"])))
    p = EXP / "exp01_baseline_gold_v1/llm_judge_pipeline/metrics/tool_summary_llm.csv"
    df = pd.read_csv(p)
    for _, r in df.iterrows():
        recs.append(dict(experiment="exp01_baseline_gold_v1_llm_judge", prompt_version="v0",
                         system=r["model"], task=r["task"], gold="v1_baseline", window="v1",
                         source=str(p.relative_to(REPO)),
                         metrics=_num(r, ["recall", "precision", "f1", "relevance", "groundedness",
                                          "completeness", "answer_relevancy", "citation_accuracy"])))

    # exp02 -- updated gold, full 3-task evaluation (tidy long format)
    p = EXP / "exp02_updated_gold_full_eval/output/scores/metrics.csv"
    df = pd.read_csv(p)
    groups = {}
    for _, r in df.iterrows():
        sub = r["subgroup"] if pd.notna(r["subgroup"]) and str(r["subgroup"]) not in ("all", "overall") else ""
        name = r["metric"] + (f":{_slug(sub)}" if sub else "")
        g = groups.setdefault((r["system"], r["task"]), {"metrics": {}, "ci": {}})
        if pd.notna(r["value"]):
            g["metrics"][name] = float(r["value"])
            g["ci"][name] = [None if pd.isna(r["ci_low"]) else float(r["ci_low"]),
                             None if pd.isna(r["ci_high"]) else float(r["ci_high"]), int(r["n"]) if pd.notna(r["n"]) else None]
    for (system, task), g in groups.items():
        recs.append(dict(experiment="exp02_updated_gold_full_eval", prompt_version="v0", system=system,
                         task=task, gold="v2_updated", window="ceo/supervisor 5y, phipa 6m",
                         source=str(p.relative_to(REPO)), metrics=g["metrics"], extra={"ci_low_high_n": g["ci"]}))

    # exp03 -- CEO task, short window, three prompt iterations
    base = EXP / "exp03_ceo_prompt_iterations"
    for folder, pv in [("prompt_v0_short_window", "v0"), ("prompt_v1_structured", "v1"),
                       ("prompt_v2_chain_of_thought", "v2")]:
        recs += _from_model_csv(base / folder / "Metrics/llm_summary_metrics.csv", "exp03_ceo_prompt_iterations",
                                pv, "ceo_short_window", "ceo", "short")

    # exp04 / exp05 -- CEO task, 5-year window
    recs += _from_model_csv(EXP / "exp04_ceo_5yr_baseline/workspace/Metrics/v4_metrics.csv",
                            "exp04_ceo_5yr_baseline", "v0", "ceo_5yr", "ceo", "5y")
    recs += _from_model_csv(EXP / "exp05_ceo_5yr_chain_of_thought/workspace/Metrics/v5_metrics_corrected.csv",
                            "exp05_ceo_5yr_chain_of_thought", "v2-cot", "ceo_5yr", "ceo", "5y")
    return recs


def trace_id(r):
    key = "|".join(str(r[k]) for k in ("experiment", "prompt_version", "system", "task"))
    return hashlib.md5(key.encode()).hexdigest()  # 32 hex chars, valid Langfuse trace id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    recs = collect()
    print(f"{len(recs)} traces, {sum(len(r['metrics']) for r in recs)} scores")
    if args.dry_run:
        for r in recs[:6]:
            print(f"  {r['experiment']}/{r['prompt_version']}/{r['system']}/{r['task']}: "
                  f"{len(r['metrics'])} scores e.g. {list(r['metrics'].items())[:3]}")
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(REPO / ".env")
    except ImportError:
        pass
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        sys.exit("Set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (and LANGFUSE_HOST) in .env first.")
    from langfuse import Langfuse
    lf = Langfuse()
    for r in recs:
        tid = trace_id(r)
        name = f"{r['experiment']}/{r['prompt_version']}/{r['system']}/{r['task']}"
        tags = [r["experiment"], f"prompt:{r['prompt_version']}", f"system:{_slug(r['system'])}",
                f"task:{r['task']}", f"gold:{r['gold']}"]
        with lf.start_as_current_span(name=name, trace_context={"trace_id": tid}) as span:
            span.update_trace(name=name, session_id=r["experiment"], tags=tags,
                              input={"system": r["system"], "task": r["task"], "prompt_version": r["prompt_version"]},
                              metadata={"gold": r["gold"], "window": r["window"], "source": r["source"],
                                        **r.get("extra", {})})
            for metric, value in r["metrics"].items():
                span.score_trace(name=metric, value=value, data_type="NUMERIC")
    lf.flush()
    print("done -- open your Langfuse project and filter by tag / session")


if __name__ == "__main__":
    main()
