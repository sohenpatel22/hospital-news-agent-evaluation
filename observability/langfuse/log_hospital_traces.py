"""Log exp02 results at hospital level to Langfuse.

One trace per  system x task x hospital x run  (Copilot has runs 1-5, everyone else run 1):
    name     : exp02/<task>/<hospital>/<system>/run<n>
    session  : exp02_updated_gold_full_eval   (same session as the aggregate traces)
    tags     : hospital:<slug>, task:<t>, system:<s>, run:<n>, level:hospital
    scores   : recall, precision, hallucination_rate, n_gold, n_extracted, n_tp, n_bucket_a/b/c
    children : one span per extracted item -> input (person, role, direction, date, citation) and
               output (bucket TP/A/B/C/D/E, matched gold item, gold row text)
    metadata : gold rows the system missed for that hospital (recall gaps)

Metric definitions are identical to experiments/exp02_updated_gold_full_eval/scripts/score.py
(records are built with its own build_records). Cross-system comparisons should filter to run:1.

Usage (repo root):  python observability/langfuse/log_hospital_traces.py [--dry-run]
"""
import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXP02 = REPO / "experiments" / "exp02_updated_gold_full_eval"
sys.path.insert(0, str(EXP02 / "scripts"))
from match import load_gold  # noqa: E402
import score  # noqa: E402

SESSION = "exp02_updated_gold_full_eval"


def slug(s):
    return "".join(c.lower() if c.isalnum() else "_" for c in str(s)).strip("_")


def canonical_hospital(name, gold_hospitals):
    """Map an output-side hospital name onto the gold-side name (first-word match)."""
    if name in gold_hospitals:
        return name
    first = name.split()[0].lower()
    for g in gold_hospitals:
        if g.split()[0].lower() == first:
            return g
    return name


def build():
    gold = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold}
    gold_hosp = {g["hospital"] for g in gold}
    records = score.build_records(gold_by_id, restrict_copilot_run1=False)

    groups = defaultdict(list)
    for r in records:
        h = canonical_hospital(r["hospital"], gold_hosp)
        groups[(r["system"], r["task"], h, r["run_number"])].append(r)

    traces = []
    for (system, task, hosp, run), recs in sorted(groups.items()):
        in_scope = {g["gold_item_id"]: g for g in gold
                    if g["task"] == task and g["hospital"] == hosp and g["in_scope"] == "TRUE"}
        tp_ids = {r["gold_item_id"] for r in recs if r["bucket"] == "TP"}
        count = lambda b: sum(1 for r in recs if r["bucket"] == b)  # noqa: E731
        tp, a, b_, c = count("TP"), count("A"), count("B"), count("C")
        denom = tp + a + b_ + c
        metrics = {"n_gold": len(in_scope), "n_extracted": len(recs), "n_tp": tp,
                   "n_bucket_a": a, "n_bucket_b": b_, "n_bucket_c": c}
        if in_scope:
            metrics["recall"] = len(tp_ids & set(in_scope)) / len(in_scope)
        if denom:
            metrics["precision"] = (tp + a) / denom
        if recs and any(r["bucket"] for r in recs):
            metrics["hallucination_rate"] = b_ / len(recs)
        missed = [f"{gid}: {g['name_or_issue']} ({g['date']})" for gid, g in in_scope.items() if gid not in tp_ids]
        items = []
        for r in recs:
            it, gr = r["item"], r["gold_row"]
            items.append({
                "input": {k: it.get(k) for k in ("person_or_issue", "role", "direction", "date_raw",
                                                 "date_normalised", "citation_url", "citation_text")},
                "output": {"bucket": r["bucket"], "gold_item_id": r["gold_item_id"],
                           "gold_row": gr["name_or_issue"] if gr else None,
                           "needs_human_check": r["needs_human_check"]},
                "metadata": {"item_index": it.get("item_index"), "snippet": (it.get("verbatim_snippet") or "")[:500]},
            })
        traces.append({"system": system, "task": task, "hospital": hosp, "run": run,
                       "metrics": metrics, "missed": missed, "items": items,
                       "source_file": recs[0]["source_file"]})
    return traces


def tid(t):
    return hashlib.md5(f"hosp|{t['system']}|{t['task']}|{t['hospital']}|{t['run']}".encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    traces = build()
    n_items = sum(len(t["items"]) for t in traces)
    print(f"{len(traces)} hospital traces, {n_items} item spans, "
          f"{sum(len(t['metrics']) for t in traces)} scores")
    if args.dry_run:
        for t in traces[:5]:
            print(f"  {t['task']}/{t['hospital']}/{t['system']}/run{t['run']}: {t['metrics']}")
        return

    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
    from langfuse import Langfuse, propagate_attributes
    lf = Langfuse()
    if not lf.auth_check():
        sys.exit("Langfuse authentication failed - check .env")
    for t in traces:
        trace_id = tid(t)
        name = f"exp02/{t['task']}/{t['hospital']}/{t['system']}/run{t['run']}"
        tags = ["level:hospital", f"hospital:{slug(t['hospital'])}", f"task:{t['task']}",
                f"system:{slug(t['system'])}", f"run:{t['run']}", "exp02_updated_gold_full_eval"]
        with propagate_attributes(trace_name=name, session_id=SESSION, tags=tags):
            with lf.start_as_current_observation(
                    name=name, as_type="span", trace_context={"trace_id": trace_id},
                    input={"system": t["system"], "task": t["task"], "hospital": t["hospital"], "run": t["run"]},
                    output=t["metrics"],
                    metadata={"missed_gold_rows": t["missed"], "source_file": t["source_file"]}):
                for i, it in enumerate(t["items"]):
                    with lf.start_as_current_observation(
                            name=f"item {it['metadata']['item_index']}: {it['input']['person_or_issue']}"[:120],
                            as_type="span", input=it["input"], output=it["output"], metadata=it["metadata"],
                            level="ERROR" if it["output"]["bucket"] in ("B", "C") else "DEFAULT",
                            status_message=f"bucket {it['output']['bucket']}"):
                        pass
        for metric, value in t["metrics"].items():
            lf.create_score(trace_id=trace_id, name=metric, value=float(value), data_type="NUMERIC",
                            score_id=hashlib.md5(f"{trace_id}|{metric}".encode()).hexdigest())
    lf.flush()
    print("done")


if __name__ == "__main__":
    main()
