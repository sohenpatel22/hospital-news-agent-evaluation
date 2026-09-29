"""
Stage 4 — scoring.

Computes exactly the metrics in EVALUATION_PLAN.md section 1.6 (as amended
2026-08-31: citation validity replaced by specificity, 1.4a).

RUN SCOPING (critical, see PART 3 item 3 / 1.6 note, both amended 2026-08-31):
  - Every cross-system metric (recall, precision, hallucination rate, field
    accuracy, specificity, omission, completeness, error taxonomy) uses
    MS Copilot Agent's Run 1 ONLY, matching every other system's single-run
    basis. Runs 2-5 are never touched by these metrics.
  - Consistency uses MS Copilot Agent Runs 1-5 ONLY and is single-system;
    it is computed completely separately from every other metric.

Usage:
  python score.py
Writes /output/scores/metrics.json and /output/scores/metrics.csv (long/tidy).
"""

import csv
import json
import os
import random
import re
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match import load_gold, name_variants, split_gold_name_or_issue  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /eval
EXTRACTED_DIR = os.path.join(ROOT, "output", "extracted")
MATCHED_DIR = os.path.join(ROOT, "output", "matched")
ADJUDICATED_DIR = os.path.join(ROOT, "output", "adjudicated")
SCORES_DIR = os.path.join(ROOT, "output", "scores")
FIGURES_DIR = os.path.join(ROOT, "output", "figures")

SYSTEMS = ["ChatGPT", "Claude", "Gemini", "MS Copilot Agent", "Perplexity"]
TASKS = ["ceo", "phipa", "supervisor"]
CEO_TIERS = ["A - dated announcement", "B - directory confirmed, undated", "C - inferred / approximate date"]

random.seed(42)
N_BOOTSTRAP = 1000

_RAW_TITLE_TOLERANCE_GROUPS = [
    {"Chief Nursing Executive", "Chief Nurse Executive"},
    {"VP Medical Affairs, Research and Education", "VP Medical & Academic Affairs"},
    {"EVP Clinical Programs & Chief Planning & Redevelopment Officer", "VP Planning, Redevelopment & Clinical Support"},
    {"VP People and Culture & CHRO", "VP Chief Human Resources Officer"},
]


def norm_role(s):
    if not s:
        return None
    s = s.lower().strip()
    s = re.sub(r"[.,]", "", s)
    # "President/CEO", "President and CEO", "President & CEO" are the same
    # title with different separator punctuation -- not a documented
    # tolerance pair, just separator noise. Canonicalise all three to "/".
    s = re.sub(r"\s*(/|&|\band\b)\s*", "/", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


TITLE_TOLERANCE_GROUPS = [{norm_role(x) for x in group} for group in _RAW_TITLE_TOLERANCE_GROUPS]


def roles_match(system_role, gold_role_detail):
    """gold_role_detail is the text after 'Name - ' in gold's name_or_issue,
    e.g. 'Chief of Staff' or 'Board Chair (incoming)'. Strip parenthetical
    direction markers before comparing.

    Returns None only when the GOLD field is unusable (per 1.6 requirement
    4: "only over matched entities where the gold field is populated").
    A populated gold role with a blank/None system role is a miss (False),
    not an exclusion -- excluding it would inflate accuracy by hiding
    every case where a system simply omitted the role."""
    if not gold_role_detail:
        return None  # gold field not populated -- excluded per spec
    g = re.sub(r"\([^)]*\)", "", gold_role_detail).strip()
    ng = norm_role(g)
    if not ng:
        return None
    if not system_role:
        return False  # gold populated, system left it blank -- a miss
    ns = norm_role(system_role)
    if ns == ng:
        return True
    for group in TITLE_TOLERANCE_GROUPS:
        if ns in group and ng in group:
            return True
    return False


def parse_gold_direction(role_detail):
    if not role_detail:
        return None
    t = role_detail.lower()
    if "incoming" in t:
        return "incoming"
    if "outgoing" in t:
        return "outgoing"
    return None


def dates_match(item_date_norm, gold_date_str, gold_confidence_tier, notes, task):
    """Returns True/False/None (None = N/A, excluded from denominator per
    1.2: gold date blank or Tier B)."""
    if gold_confidence_tier == "B - directory confirmed, undated" or not gold_date_str or gold_date_str == "nan":
        return None
    if not item_date_norm:
        return False

    def to_ymd(s):
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)), "day")
        m = re.match(r"^(\d{4})-(\d{2})$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), None, "month")
        m = re.match(r"^(\d{4})$", s)
        if m:
            return (int(m.group(1)), None, None, "year")
        return None

    g = to_ymd(str(gold_date_str)[:10])
    i = to_ymd(item_date_norm)
    if g is None or i is None:
        return False

    if g[3] == "year":
        return i[0] == g[0]
    if g[3] == "month":
        return i[0] == g[0] and (i[1] is None or i[1] == g[1])
    # gold has full day precision
    if i[0] != g[0]:
        return False
    if i[1] is not None and i[1] != g[1]:
        return False
    if i[2] is not None and g[2] is not None and i[2] != g[2]:
        pass  # fall through to documented-tolerance check below
    elif i[1] == g[1] and (i[2] is None or i[2] == g[2]):
        return True

    # documented per-person date tolerances (1.3)
    notes_l = (notes or "").lower()
    tol_pairs = [
        ((2024, 6, 17), (2024, 6, 18)),  # Mitch Frazer
        ((2024, 8, 18), (2024, 8, 19)),  # Jennifer Dockery
        ((2023, 6, 22), (2023, 7, 18)),  # Arnprior 2023 cohort
    ]
    if "frazer" in notes_l or "dockery" in notes_l or "2023-06-22" in str(gold_date_str) or "2023-07-18" in str(gold_date_str) or any(name in notes_l for name in ("holock", "kenny", "koba", "stitt-cavanagh", "mcgaraughty")):
        for a, b in tol_pairs:
            ai = (i[0], i[1], i[2])
            if ai == a or ai == b:
                return True
    return i[0] == g[0] and i[1] == g[1] and i[2] == g[2]


def is_generic_citation_text(text):
    if not text:
        return True
    t = text.strip().lower()
    if t in ("source link", "link", "source", ""):
        return True
    return False


def specificity_score(item):
    score = 0
    if item.get("date_normalised") and re.match(r"^\d{4}-\d{2}-\d{2}$", item["date_normalised"]):
        score += 1
    if not is_generic_citation_text(item.get("citation_text")):
        score += 1
    if item.get("role"):
        score += 1
    return score


def load_extracted():
    out = {}
    for fname in sorted(os.listdir(EXTRACTED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        with open(os.path.join(EXTRACTED_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        out[fname] = data
    return out


def load_matched():
    out = {}
    for fname in sorted(os.listdir(MATCHED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_") or fname in (
            "unmatched_gold.json", "organisational_errors.json",
        ):
            continue
        with open(os.path.join(MATCHED_DIR, fname), encoding="utf-8") as f:
            out[fname] = {row["item_index"]: row for row in json.load(f)}
    return out


def load_adjudicated():
    out = {}
    for fname in sorted(os.listdir(ADJUDICATED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_") or fname == "needs_human_check.csv":
            continue
        with open(os.path.join(ADJUDICATED_DIR, fname), encoding="utf-8") as f:
            out[fname] = {row["item_index"]: row for row in json.load(f)}
    return out


def build_records(gold_by_id, restrict_copilot_run1=True):
    """One record per extracted item, enriched with match + adjudication +
    gold info. If restrict_copilot_run1, only MS Copilot Agent run_number==1
    items are included (every other system is already run_number==1 only on
    disk). Pass False to get ALL Copilot runs (for the consistency metric)."""
    extracted = load_extracted()
    matched = load_matched()
    adjudicated = load_adjudicated()

    records = []
    for fname, data in extracted.items():
        system = data["system"]
        if restrict_copilot_run1 and system == "MS Copilot Agent" and data["run_number"] != 1:
            continue
        m = matched.get(fname, {})
        a = adjudicated.get(fname, {})
        for item in data["items"]:
            idx = item["item_index"]
            mrow = m.get(idx)
            arow = a.get(idx)
            gold_item_id = mrow["matched_gold_item_id"] if mrow else None
            gold_row = gold_by_id.get(gold_item_id) if gold_item_id else None
            bucket = None
            needs_human_check = False
            if gold_row is not None:
                bucket = "TP" if gold_row["in_scope"] == "TRUE" else "matched_out_of_scope"
            elif arow is not None:
                bucket = arow["bucket"]
                needs_human_check = arow.get("needs_human_check", False)
            records.append(
                {
                    "system": system,
                    "task": data["task"],
                    "hospital": data["hospital"],
                    "run_number": data["run_number"],
                    "source_file": fname,
                    "item": item,
                    "gold_item_id": gold_item_id,
                    "gold_row": gold_row,
                    "bucket": bucket,
                    "needs_human_check": needs_human_check,
                }
            )
    return records


def bootstrap_ci(values_fn, n, seed_offset=0):
    """values_fn(rng_indices) -> metric value for a resample defined by a
    list of indices. n is the population size to resample with replacement.
    Returns (low, high) 95% CI, or (None, None) if n == 0."""
    if n == 0:
        return (None, None)
    rng = random.Random(42 + seed_offset)
    stats = []
    for _ in range(N_BOOTSTRAP):
        idxs = [rng.randrange(n) for _ in range(n)]
        v = values_fn(idxs)
        if v is not None:
            stats.append(v)
    if not stats:
        return (None, None)
    stats.sort()
    lo = stats[int(0.025 * len(stats))]
    hi = stats[min(int(0.975 * len(stats)), len(stats) - 1)]
    return (lo, hi)


def recall_with_ci(matched_gold_ids, in_scope_gold_ids):
    denom = len(in_scope_gold_ids)
    if denom == 0:
        return (None, None, None, 0)
    point = len(matched_gold_ids & in_scope_gold_ids) / denom
    gold_list = list(in_scope_gold_ids)

    def metric(idxs):
        resampled = [gold_list[i] for i in idxs]
        d = len(resampled)
        if d == 0:
            return None
        hit = sum(1 for g in resampled if g in matched_gold_ids)
        return hit / d

    lo, hi = bootstrap_ci(metric, denom, seed_offset=hash(tuple(sorted(in_scope_gold_ids))) % 10000)
    return (point, lo, hi, denom)


def precision_with_ci(records_for_system_task):
    tp = sum(1 for r in records_for_system_task if r["bucket"] == "TP")
    a = sum(1 for r in records_for_system_task if r["bucket"] == "A")
    b = sum(1 for r in records_for_system_task if r["bucket"] == "B")
    c = sum(1 for r in records_for_system_task if r["bucket"] == "C")
    denom_records = [r for r in records_for_system_task if r["bucket"] in ("TP", "A", "B", "C")]
    denom = len(denom_records)
    if denom == 0:
        return (None, None, None, 0, tp, a, b, c)
    point = (tp + a) / denom

    def metric(idxs):
        resampled = [denom_records[i] for i in idxs]
        d = len(resampled)
        if d == 0:
            return None
        num = sum(1 for r in resampled if r["bucket"] in ("TP", "A"))
        return num / d

    lo, hi = bootstrap_ci(metric, denom, seed_offset=1)
    return (point, lo, hi, denom, tp, a, b, c)


def hallucination_with_ci(records_for_system_task):
    denom = len(records_for_system_task)
    if denom == 0:
        return (None, None, None, 0, 0)
    b_count = sum(1 for r in records_for_system_task if r["bucket"] == "B")
    point = b_count / denom

    def metric(idxs):
        resampled = [records_for_system_task[i] for i in idxs]
        d = len(resampled)
        if d == 0:
            return None
        num = sum(1 for r in resampled if r["bucket"] == "B")
        return num / d

    lo, hi = bootstrap_ci(metric, denom, seed_offset=2)
    return (point, lo, hi, denom, b_count)


def main():
    os.makedirs(SCORES_DIR, exist_ok=True)

    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    gold_by_task = defaultdict(list)
    for g in gold_items:
        gold_by_task[g["task"]].append(g)

    # status column -> provenance (1.8 / 1.10): NEWLY ADDED -> independent
    status_by_gold_id = {}
    xls = pd.ExcelFile(os.path.join(ROOT, "data", "gold.xlsx"))
    df_ceo = pd.read_excel(xls, sheet_name="CEOs", header=2)
    df_ceo.dropna(how="all", inplace=True)
    for _, row in df_ceo.iterrows():
        if pd.isna(row.get("item_id")):
            continue
        status_by_gold_id[str(row["item_id"])] = str(row.get("status", ""))

    records = build_records(gold_by_id, restrict_copilot_run1=True)

    tidy_rows = []  # for metrics.csv: metric, system, task, subgroup, value, ci_low, ci_high, n
    out = {"generated_at": "2026-08-31", "run_scoping": "cross-system metrics use MS Copilot Agent Run 1 only; consistency uses Runs 1-5 separately", "systems": {}}

    # ---------- RECALL ----------
    for task in TASKS:
        in_scope_ids_all = {g["gold_item_id"] for g in gold_by_task[task] if g["in_scope"] == "TRUE"}
        independent_ids = {g["gold_item_id"] for g in gold_by_task[task] if g["in_scope"] == "TRUE" and status_by_gold_id.get(g["gold_item_id"], "").startswith("NEWLY ADDED")}

        for system in SYSTEMS:
            sys_records = [r for r in records if r["system"] == system and r["task"] == task]
            matched_ids = {r["gold_item_id"] for r in sys_records if r["bucket"] == "TP"}

            if task == "ceo":
                for tier in CEO_TIERS:
                    tier_ids = {g["gold_item_id"] for g in gold_by_task[task] if g["in_scope"] == "TRUE" and g["confidence_tier"] == tier}
                    point, lo, hi, n = recall_with_ci(matched_ids, tier_ids)
                    out["systems"].setdefault(system, {}).setdefault("recall", {}).setdefault(task, {})[tier] = {"point": point, "ci_low": lo, "ci_high": hi, "n_gold": n}
                    tidy_rows.append(["recall_by_tier", system, task, tier, point, lo, hi, n])

            point, lo, hi, n = recall_with_ci(matched_ids, in_scope_ids_all)
            out["systems"].setdefault(system, {}).setdefault("recall", {}).setdefault(task, {})["overall"] = {"point": point, "ci_low": lo, "ci_high": hi, "n_gold": n}
            tidy_rows.append(["recall_overall", system, task, "overall", point, lo, hi, n])

            point_i, lo_i, hi_i, n_i = recall_with_ci(matched_ids, independent_ids)
            out["systems"].setdefault(system, {}).setdefault("recall", {}).setdefault(task, {})["independent"] = {"point": point_i, "ci_low": lo_i, "ci_high": hi_i, "n_gold": n_i}
            tidy_rows.append(["recall_independent", system, task, "independent", point_i, lo_i, hi_i, n_i])

            if task == "ceo" or task == "phipa" or task == "supervisor":
                pass  # tier note handled above; PHIPA/supervisor simply never populate the tier dict

    # ---------- PRECISION & HALLUCINATION ----------
    for task in TASKS:
        for system in SYSTEMS:
            sys_records = [r for r in records if r["system"] == system and r["task"] == task]
            point, lo, hi, n, tp, a, b, c = precision_with_ci(sys_records)
            out["systems"].setdefault(system, {}).setdefault("precision", {})[task] = {
                "point": point, "ci_low": lo, "ci_high": hi, "n": n, "tp": tp, "bucket_A": a, "bucket_B": b, "bucket_C": c,
            }
            tidy_rows.append(["precision", system, task, "overall", point, lo, hi, n])

            hpoint, hlo, hhi, hn, hb = hallucination_with_ci(sys_records)
            out["systems"].setdefault(system, {}).setdefault("hallucination_rate", {})[task] = {
                "point": hpoint, "ci_low": hlo, "ci_high": hhi, "n": hn, "bucket_B": hb,
            }
            tidy_rows.append(["hallucination_rate", system, task, "overall", hpoint, hlo, hhi, hn])

    # ---------- FIELD ACCURACY, SPECIFICITY, OMISSION (matched TP only) ----------
    for task in TASKS:
        for system in SYSTEMS:
            tp_records = [r for r in records if r["system"] == system and r["task"] == task and r["bucket"] == "TP"]
            role_correct, role_n = 0, 0
            date_correct, date_n = 0, 0
            dir_correct, dir_n = 0, 0
            spec_scores = []
            omission_count = 0

            for r in tp_records:
                item = r["item"]
                gold_row = r["gold_row"]
                core_name, role_detail = split_gold_name_or_issue(gold_row["name_or_issue"])

                rm = roles_match(item.get("role"), role_detail)
                if rm is not None:
                    role_n += 1
                    role_correct += int(rm)

                dm = dates_match(item.get("date_normalised"), gold_row.get("date"), gold_row.get("confidence_tier"), gold_row.get("notes"), task)
                if dm is not None:
                    date_n += 1
                    date_correct += int(dm)

                gdir = parse_gold_direction(role_detail)
                if gdir is not None:
                    dir_n += 1
                    dir_correct += int(item.get("direction") == gdir)

                spec_scores.append(specificity_score(item))

                required_blank = (
                    not item.get("person_or_issue")
                    or not item.get("role")
                    or not item.get("date_normalised")
                    or not item.get("citation_url")
                )
                if required_blank:
                    omission_count += 1

            fa = out["systems"].setdefault(system, {}).setdefault("field_accuracy", {}).setdefault(task, {})
            fa["role"] = {"correct": role_correct, "n": role_n, "accuracy": (role_correct / role_n) if role_n else None}
            fa["date"] = {"correct": date_correct, "n": date_n, "accuracy": (date_correct / date_n) if date_n else None}
            fa["direction"] = {"correct": dir_correct, "n": dir_n, "accuracy": (dir_correct / dir_n) if dir_n else None}
            tidy_rows.append(["field_accuracy_role", system, task, "role", fa["role"]["accuracy"], None, None, role_n])
            tidy_rows.append(["field_accuracy_date", system, task, "date", fa["date"]["accuracy"], None, None, date_n])
            tidy_rows.append(["field_accuracy_direction", system, task, "direction", fa["direction"]["accuracy"], None, None, dir_n])

            n_spec = len(spec_scores)
            mean_spec = (sum(spec_scores) / n_spec) if n_spec else None
            pct3 = (sum(1 for s in spec_scores if s == 3) / n_spec) if n_spec else None
            out["systems"][system].setdefault("specificity", {})[task] = {"mean": mean_spec, "pct_scoring_3": pct3, "n": n_spec}
            tidy_rows.append(["specificity_mean", system, task, "overall", mean_spec, None, None, n_spec])
            tidy_rows.append(["specificity_pct3", system, task, "overall", pct3, None, None, n_spec])

            omission_rate = (omission_count / len(tp_records)) if tp_records else None
            out["systems"][system].setdefault("omission_rate", {})[task] = {"rate": omission_rate, "n": len(tp_records), "omitted": omission_count}
            tidy_rows.append(["omission_rate", system, task, "overall", omission_rate, None, None, len(tp_records)])

    # ---------- COMPLETENESS (flags, not a rate) ----------
    hospitals_by_task = defaultdict(set)
    for g in gold_items:
        hospitals_by_task[g["task"]].add(g["hospital"])

    for task in TASKS:
        for system in SYSTEMS:
            sys_records = [r for r in records if r["system"] == system and r["task"] == task]
            hospitals_covered = {r["hospital"] for r in sys_records}
            directions_seen = {r["item"].get("direction") for r in sys_records}
            all_hospitals = hospitals_covered >= hospitals_by_task[task]
            both_directions = "incoming" in directions_seen and "outgoing" in directions_seen
            out["systems"].setdefault(system, {}).setdefault("completeness", {})[task] = {
                "all_hospitals_covered": all_hospitals,
                "hospitals_covered": sorted(hospitals_covered),
                "hospitals_expected": sorted(hospitals_by_task[task]),
                "both_directions_seen": both_directions,
            }

    # ---------- ERROR TAXONOMY ----------
    for task in TASKS:
        for system in SYSTEMS:
            sys_records = [r for r in records if r["system"] == system and r["task"] == task]
            counts = {
                "fabricated_person_or_event": 0,
                "wrong_role": 0,
                "wrong_date": 0,
                "organisational_confusion": 0,
                "stale": 0,
            }
            for r in sys_records:
                if r["bucket"] == "B":
                    counts["fabricated_person_or_event"] += 1
                elif r["bucket"] == "C":
                    counts["organisational_confusion"] += 1
                elif r["bucket"] == "TP":
                    gold_row = r["gold_row"]
                    core_name, role_detail = split_gold_name_or_issue(gold_row["name_or_issue"])
                    rm = roles_match(r["item"].get("role"), role_detail)
                    if rm is False:
                        counts["wrong_role"] += 1
                    dm = dates_match(r["item"].get("date_normalised"), gold_row.get("date"), gold_row.get("confidence_tier"), gold_row.get("notes"), task)
                    if dm is False:
                        counts["wrong_date"] += 1
            out["systems"].setdefault(system, {}).setdefault("error_taxonomy", {})[task] = counts
            for cat, n in counts.items():
                tidy_rows.append(["error_taxonomy_" + cat, system, task, cat, n, None, None, len(sys_records)])
    out["error_taxonomy_note"] = "6th category 'unsupported citation' not computed this round (citation validity excluded, see 1.4 addendum). 'stale' is counted as 0 throughout -- no automated heuristic was implemented for it; treat as not-yet-measured, not as zero occurrences, and flag for manual review."

    # ---------- CONSISTENCY (Copilot only, Runs 1-5) ----------
    all_records_copilot = build_records(gold_by_id, restrict_copilot_run1=False)
    copilot_records = [r for r in all_records_copilot if r["system"] == "MS Copilot Agent"]

    def entity_key(r):
        if r["gold_item_id"]:
            return "G:" + r["gold_item_id"]
        item = r["item"]
        nv = sorted(name_variants(item.get("person_or_issue") or ""))
        key_name = nv[0] if nv else (item.get("person_or_issue") or "")
        return f"U:{key_name}@{r['hospital']}@{item.get('direction')}"

    consistency = {}
    for task in TASKS:
        run_sets = {}
        for run in range(1, 6):
            run_sets[run] = {
                entity_key(r) for r in copilot_records if r["task"] == task and r["run_number"] == run
            }
        pairs = []
        runs_list = sorted(run_sets.keys())
        for i in range(len(runs_list)):
            for j in range(i + 1, len(runs_list)):
                a, b = run_sets[runs_list[i]], run_sets[runs_list[j]]
                union = a | b
                jac = (len(a & b) / len(union)) if union else None
                pairs.append({"run_a": runs_list[i], "run_b": runs_list[j], "jaccard": jac})
        valid_jacs = [p["jaccard"] for p in pairs if p["jaccard"] is not None]
        mean_jaccard = sum(valid_jacs) / len(valid_jacs) if valid_jacs else None

        all_entities = set()
        for s in run_sets.values():
            all_entities |= s
        stable_count = sum(1 for e in all_entities if all(e in run_sets[r] for r in runs_list))
        stability = (stable_count / len(all_entities)) if all_entities else None

        consistency[task] = {
            "pairwise_jaccard": pairs,
            "mean_pairwise_jaccard": mean_jaccard,
            "n_pairs": len(pairs),
            "per_item_stability": stability,
            "n_distinct_entities_any_run": len(all_entities),
            "n_stable_in_all_5_runs": stable_count,
        }
        tidy_rows.append(["consistency_mean_jaccard", "MS Copilot Agent", task, "SINGLE_SYSTEM_ONLY", mean_jaccard, None, None, len(pairs)])
        tidy_rows.append(["consistency_stability", "MS Copilot Agent", task, "SINGLE_SYSTEM_ONLY", stability, None, None, len(all_entities)])

    out["consistency"] = {
        "label": "SINGLE-SYSTEM RELIABILITY (MS Copilot Agent only) -- NOT a cross-system comparison",
        "by_task": consistency,
    }

    # ---------- CHECKPOINT: independent recall < overall recall for Copilot ----------
    checkpoint_notes = []
    for task in TASKS:
        ov = out["systems"].get("MS Copilot Agent", {}).get("recall", {}).get(task, {}).get("overall", {}).get("point")
        ind = out["systems"].get("MS Copilot Agent", {}).get("recall", {}).get(task, {}).get("independent", {}).get("point")
        if ov is not None and ind is not None:
            ok = ind <= ov
            checkpoint_notes.append(f"{task}: overall={ov:.3f} independent={ind:.3f} independent<=overall: {ok}")
    out["checkpoint_independent_lower_than_overall"] = checkpoint_notes

    with open(os.path.join(SCORES_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    with open(os.path.join(SCORES_DIR, "metrics.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "system", "task", "subgroup", "value", "ci_low", "ci_high", "n"])
        for row in tidy_rows:
            writer.writerow(row)

    print("Wrote", os.path.join(SCORES_DIR, "metrics.json"))
    print("Wrote", os.path.join(SCORES_DIR, "metrics.csv"))
    print()
    print("=== CHECKPOINT: recall(independent) should be <= recall(overall) for Copilot ===")
    for line in checkpoint_notes:
        print(" ", line)


if __name__ == "__main__":
    main()
