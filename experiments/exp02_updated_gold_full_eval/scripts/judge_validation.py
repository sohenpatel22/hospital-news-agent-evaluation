"""
Stage 5 — judge validation.

--sample   Draw a stratified random sample of ~70 decisions (60-80 range)
           spanning systems, tasks, and decision types (match / each
           adjudication bucket A-E), and write
           /output/scores/judge_validation_sample.csv with a BLANK
           human_decision column for manual fill-in.

--score    After human_decision has been filled in for every row, compute
           Cohen's kappa overall and per decision type, write the confusion
           matrix, and report which decision types the judge is least
           reliable on.
"""

import argparse
import csv
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match import load_gold, split_gold_name_or_issue  # noqa: E402
from score import SYSTEMS, TASKS, build_records  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_DIR = os.path.join(ROOT, "output", "scores")
SAMPLE_PATH = os.path.join(SCORES_DIR, "judge_validation_sample.csv")

random.seed(42)
TARGET_TOTAL = 70


def decision_type_of(record):
    if record["bucket"] == "TP":
        return "match_in_scope"
    if record["bucket"] == "matched_out_of_scope":
        return "match_out_of_scope"
    return f"bucket_{record['bucket']}"  # bucket_A .. bucket_E


def judge_decision_str(record):
    if record["bucket"] == "TP":
        return f"MATCH -> {record['gold_item_id']}"
    if record["bucket"] == "matched_out_of_scope":
        return f"MATCH (out-of-scope gold row) -> {record['gold_item_id']}"
    return f"NO-MATCH -> bucket {record['bucket']}"


def judge_reason_str(record, matched_reason_lookup):
    if record["bucket"] in ("TP", "matched_out_of_scope"):
        key = (record["source_file"], record["item"]["item_index"])
        return matched_reason_lookup.get(key, "")
    return record.get("adjudication_reason", "")


def sample():
    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    records = build_records(gold_by_id, restrict_copilot_run1=False)

    # need match_reason / adjudication reason text -- re-derive by loading
    # the matched/adjudicated files directly since build_records doesn't
    # carry reason text through.
    import json

    MATCHED_DIR = os.path.join(ROOT, "output", "matched")
    ADJUDICATED_DIR = os.path.join(ROOT, "output", "adjudicated")
    matched_reason_lookup = {}
    for fname in os.listdir(MATCHED_DIR):
        if not fname.endswith(".json") or fname.startswith("_") or fname in ("unmatched_gold.json", "organisational_errors.json"):
            continue
        for row in json.load(open(os.path.join(MATCHED_DIR, fname), encoding="utf-8")):
            matched_reason_lookup[(fname, row["item_index"])] = row.get("match_reason", "")
    adjudicated_reason_lookup = {}
    for fname in os.listdir(ADJUDICATED_DIR):
        if not fname.endswith(".json") or fname.startswith("_") or fname == "needs_human_check.csv":
            continue
        for row in json.load(open(os.path.join(ADJUDICATED_DIR, fname), encoding="utf-8")):
            adjudicated_reason_lookup[(fname, row["item_index"])] = row.get("reason", "")

    for r in records:
        key = (r["source_file"], r["item"]["item_index"])
        r["adjudication_reason"] = adjudicated_reason_lookup.get(key, "")

    by_type = defaultdict(list)
    for r in records:
        by_type[decision_type_of(r)].append(r)

    print("Available population by decision type:")
    for t, pop in sorted(by_type.items()):
        print(f"  {t}: {len(pop)}")

    sampled = []

    # Take everything for rare types (fewer than 15 available)
    RARE_CAP = 15
    fixed_allocation = {}
    for t, pop in by_type.items():
        if len(pop) <= RARE_CAP:
            fixed_allocation[t] = len(pop)
            sampled.extend(pop)

    remaining_budget = TARGET_TOTAL - len(sampled)
    large_types = {t: pop for t, pop in by_type.items() if t not in fixed_allocation}

    # Stratify the remaining budget across (system, task) cells within the
    # large types (match_in_scope, match_out_of_scope if not already fixed),
    # proportional to availability, minimum 1 per non-empty cell where budget allows.
    cells = defaultdict(list)
    for t, pop in large_types.items():
        for r in pop:
            cells[(t, r["system"], r["task"])].append(r)

    cell_keys = list(cells.keys())
    rng = random.Random(42)
    rng.shuffle(cell_keys)

    # round-robin allocate 1 at a time to spread coverage
    idx = 0
    picked_per_cell = {k: 0 for k in cell_keys}
    while remaining_budget > 0 and cell_keys:
        k = cell_keys[idx % len(cell_keys)]
        pool = cells[k]
        if picked_per_cell[k] < len(pool):
            picked_per_cell[k] += 1
            remaining_budget -= 1
        idx += 1
        if idx > 100000:
            break
        if all(picked_per_cell[k] >= len(cells[k]) for k in cell_keys):
            break

    for k, n in picked_per_cell.items():
        pool = cells[k][:]
        rng.shuffle(pool)
        sampled.extend(pool[:n])

    rng.shuffle(sampled)

    os.makedirs(SCORES_DIR, exist_ok=True)
    with open(SAMPLE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "sample_id",
                "decision_type",
                "system",
                "task",
                "hospital",
                "run_number",
                "source_file",
                "item_index",
                "person_or_issue",
                "role",
                "date_normalised",
                "citation_url",
                "verbatim_snippet",
                "judge_decision",
                "judge_reason",
                "human_decision",  # BLANK for manual fill: same vocabulary as judge_decision
                "human_agrees",  # BLANK: Y/N -- did the human agree with the judge's decision
                "human_notes",
            ]
        )
        for i, r in enumerate(sampled, start=1):
            item = r["item"]
            writer.writerow(
                [
                    i,
                    decision_type_of(r),
                    r["system"],
                    r["task"],
                    r["hospital"],
                    r["run_number"],
                    r["source_file"],
                    item["item_index"],
                    item["person_or_issue"],
                    item.get("role") or "",
                    item.get("date_normalised") or "",
                    item.get("citation_url") or "",
                    item.get("verbatim_snippet") or "",
                    judge_decision_str(r),
                    judge_reason_str(r, matched_reason_lookup),
                    "",
                    "",
                    "",
                ]
            )

    print(f"\nSampled {len(sampled)} decisions -> {SAMPLE_PATH}")
    type_counts = Counter(decision_type_of(r) for r in sampled)
    for t, n in sorted(type_counts.items()):
        print(f"  {t}: {n}")
    missing_types = [t for t in ("bucket_A", "bucket_C", "bucket_D") if t not in by_type or len(by_type[t]) == 0]
    if missing_types:
        print(f"\nNOTE: {missing_types} have ZERO items in the current dataset -- cannot be sampled or "
              f"kappa-scored. This is a real coverage gap in the judge-validation sample, not an error; "
              f"disclose it in the preprint (kappa for these bucket types is simply not measurable this round).")


def score():
    if not os.path.exists(SAMPLE_PATH):
        print("Run --sample first.")
        sys.exit(1)
    rows = list(csv.DictReader(open(SAMPLE_PATH, encoding="utf-8")))
    unfilled = [r for r in rows if not r["human_decision"].strip()]
    if unfilled:
        print(f"{len(unfilled)} / {len(rows)} rows still have a blank human_decision. Fill in every row before scoring.")
        return

    def normalize(s):
        return s.strip().upper()

    labels = sorted(set(normalize(r["judge_decision"]) for r in rows) | set(normalize(r["human_decision"]) for r in rows))
    confusion = defaultdict(lambda: defaultdict(int))
    for r in rows:
        confusion[normalize(r["human_decision"])][normalize(r["judge_decision"])] += 1

    n = len(rows)
    agree = sum(1 for r in rows if normalize(r["judge_decision"]) == normalize(r["human_decision"]))
    po = agree / n

    # expected agreement (Cohen's kappa, treating this as a labeled multi-class problem)
    judge_counts = Counter(normalize(r["judge_decision"]) for r in rows)
    human_counts = Counter(normalize(r["human_decision"]) for r in rows)
    pe = sum((judge_counts.get(lbl, 0) / n) * (human_counts.get(lbl, 0) / n) for lbl in labels)
    kappa = (po - pe) / (1 - pe) if pe != 1 else None

    print(f"Overall: n={n} agreement={po:.3f} Cohen's kappa={kappa}")

    print("\nPer decision-type reliability:")
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["decision_type"]].append(r)
    type_reliability = {}
    for t, trows in sorted(by_type.items()):
        tn = len(trows)
        tagree = sum(1 for r in trows if normalize(r["judge_decision"]) == normalize(r["human_decision"]))
        type_reliability[t] = tagree / tn if tn else None
        print(f"  {t}: n={tn} agreement={type_reliability[t]:.3f}" if tn else f"  {t}: n=0")

    least_reliable = sorted(type_reliability.items(), key=lambda x: (x[1] is None, x[1]))
    print("\nLeast reliable decision types (lowest agreement first):")
    for t, acc in least_reliable[:5]:
        print(f"  {t}: {acc}")

    with open(os.path.join(SCORES_DIR, "judge_validation_confusion_matrix.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["human_decision \\ judge_decision"] + labels)
        for hl in labels:
            writer.writerow([hl] + [confusion[hl].get(jl, 0) for jl in labels])

    import json

    with open(os.path.join(SCORES_DIR, "judge_validation_results.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "n": n,
                "overall_agreement": po,
                "cohens_kappa": kappa,
                "by_decision_type": {t: {"n": len(trows), "agreement": type_reliability[t]} for t, trows in by_type.items()},
                "least_reliable_types": [{"type": t, "agreement": acc} for t, acc in least_reliable],
            },
            f,
            indent=2,
        )
    print(f"\nWrote judge_validation_confusion_matrix.csv and judge_validation_results.json to {SCORES_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args()
    if not args.sample and not args.score:
        parser.print_help()
        sys.exit(1)
    if args.sample:
        sample()
    if args.score:
        score()
