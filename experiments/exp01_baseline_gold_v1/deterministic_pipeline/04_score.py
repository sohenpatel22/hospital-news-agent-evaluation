import os
import re
import pandas as pd
import sys
sys.path.append(r"../Evaluation Code")
import score_evaluation

# ---------------------------------------------------------------------------
# FIX A: Extract person names from gold/prediction text
# ---------------------------------------------------------------------------

# Broad list of known names from the gold dataset for exact matching
KNOWN_NAMES = [
    # Supervisors
    "Eric Hanna", "Carmine Stumpo", "Altaf Stationwala", "David Musyj",
    # CEO / Board common
    "Mary-Agnes Wilson", "Leah Levesque", "Jeremy Stevenson", "Beth Ciavaglia",
    "Fay Lim-Lambie", "Stephanie Zee", "Joby McKenzie", "Ruby Philip-Katyal",
    "Atul Mehta", "John Fursey", "Richard Holock", "Peter Kenny", "Borys Koba",
    "Oliver Jacob", "Cathy Jordan",
]

def extract_person_name_from_gold(gold_text):
    """Extract the person name from a gold entry like 'Eric Hanna - Supervisor (s.9)'
    Returns lowercase name or None."""
    # Pattern: everything before the first ' - '
    m = re.match(r'^(.+?)\s*-\s*', gold_text)
    if m:
        return m.group(1).strip().lower()
    return gold_text.lower()

def name_in_prediction(name, pred_text):
    """Check if a person's name (from gold) appears in the prediction text.
    Handles both full name and last name matches."""
    if not name or not pred_text:
        return False
    pred_lower = pred_text.lower()
    name_lower = name.lower()
    # Full name match
    if name_lower in pred_lower:
        return True
    # Last name only match (for longer names)
    parts = name_lower.split()
    if len(parts) >= 2:
        last = parts[-1]
        if len(last) > 3 and last in pred_lower:
            return True
    return False

# ---------------------------------------------------------------------------
# FIX B: PHIPA ID extraction
# ---------------------------------------------------------------------------

PHIPA_ID_PATTERN = re.compile(
    r'(PHIPA\s+Decision\s+\d+|PO-\d+|Order\s+(?:in\s+Council\s+)?[\w/\-]+)',
    re.IGNORECASE
)

def extract_phipa_ids(text):
    """Extract all PHIPA decision IDs and order numbers from text."""
    if not text:
        return set()
    matches = PHIPA_ID_PATTERN.findall(text)
    return {m.strip().lower().replace(' ', '') for m in matches}

def ids_overlap(gold_text, pred_text):
    """Return True if any extracted PHIPA/PO IDs match between gold and prediction."""
    gold_ids = extract_phipa_ids(gold_text)
    pred_ids = extract_phipa_ids(pred_text)
    return bool(gold_ids & pred_ids)

# ---------------------------------------------------------------------------
# FIX C: Two-stage matching per task
# ---------------------------------------------------------------------------

def smart_match(gold_items, real_extracted, task):
    """Two-stage matching:
    Stage 1: Task-specific key match (name for supervisors/ceo, ID for phipa)
    Stage 2: Fuzzy fallback (existing score_evaluation.match_hospital_group)
    """
    gold_pool = list(gold_items)
    extracted_pool = list(real_extracted)
    matched_pairs = []

    # Stage 1: Key matching
    if task in ('supervisors', 'ceo'):
        remaining_gold = []
        for g in gold_pool:
            gold_name = extract_person_name_from_gold(g['name_or_issue'])
            found = False
            for e in extracted_pool:
                if name_in_prediction(gold_name, e['name_or_issue']):
                    matched_pairs.append((g, e, 0.9))  # high confidence
                    extracted_pool.remove(e)
                    found = True
                    break
            if not found:
                remaining_gold.append(g)
        gold_pool = remaining_gold

    elif task == 'phipa':
        remaining_gold = []
        for g in gold_pool:
            found = False
            for e in extracted_pool:
                if ids_overlap(g['name_or_issue'], e['name_or_issue']):
                    matched_pairs.append((g, e, 0.95))
                    extracted_pool.remove(e)
                    found = True
                    break
            if not found:
                remaining_gold.append(g)
        gold_pool = remaining_gold

    # Stage 2: Fuzzy fallback for any remaining unmatched items
    fuzzy_pairs, unmatched_gold, unmatched_extracted = score_evaluation.match_hospital_group(
        gold_pool, extracted_pool
    )
    matched_pairs.extend(fuzzy_pairs)

    return matched_pairs, unmatched_gold, unmatched_extracted


def score_events():
    print("--- Phase 5: Scoring Engine (v2 - Smart Matching) ---")
    
    out_dir = "metrics"
    os.makedirs(out_dir, exist_ok=True)
    
    gold_df = pd.read_csv("gold/all_gold.csv", dtype=str).fillna("")
    resp_df = pd.read_csv("structured_outputs/all_predictions.csv", dtype=str).fillna("")
    resp_df.rename(columns={"model": "tool", "hospital_eval": "hospital"}, inplace=True)
    resp_df["prompt_version"] = "v0"
    
    alias_map = score_evaluation.build_alias_map(gold_df)
    gold_df["hospital_norm"] = gold_df["hospital"].apply(lambda h: score_evaluation.normalize_hospital(h, alias_map))
    resp_df["hospital_norm"] = resp_df["hospital"].apply(lambda h: score_evaluation.normalize_hospital(h, alias_map))
    
    gold_in_scope = gold_df[gold_df["in_scope"].str.strip().str.lower() == "true"].copy()
    gold_in_scope["date_parsed"] = gold_in_scope["date"].apply(score_evaluation.try_parse_date)
    resp_df["date_parsed"] = resp_df["date"].apply(score_evaluation.try_parse_date)
    
    item_level_rows = []
    hospital_summary_rows = []
    
    group_cols = ["tool", "task", "prompt_version", "run_number", "hospital_norm"]
    for keys, group in resp_df.groupby(group_cols):
        tool, task, prompt_version, run_number, hospital_norm = keys
        
        gold_items = gold_in_scope[
            (gold_in_scope["hospital_norm"] == hospital_norm) &
            (gold_in_scope["task"] == task)
        ].to_dict("records")
        extracted_items = group.to_dict("records")
        
        real_extracted = [
            e for e in extracted_items
            if score_evaluation.normalize_text(e["name_or_issue"]) not in ("none found", "unparsable")
        ]
        
        # Use smart matching instead of plain fuzzy
        matched_pairs, unmatched_gold, unmatched_extracted = smart_match(gold_items, real_extracted, task)
        
        for g, e, score in matched_pairs:
            date_match = score_evaluation.dates_close(g.get("date_parsed"), e.get("date_parsed"))
            item_level_rows.append({
                "tool": tool, "task": task, "prompt_version": prompt_version, "run_number": run_number,
                "hospital": hospital_norm, "result": "MATCH",
                "gold_item_id": g["item_id"], "gold_text": g["name_or_issue"], "gold_date": g["date"],
                "extracted_text": e["name_or_issue"], "extracted_date": e["date"],
                "extracted_source": e.get("source", ""), "extracted_link": e.get("link", ""),
                "match_score": round(score, 3), "date_matches": date_match,
            })
        for g in unmatched_gold:
            item_level_rows.append({
                "tool": tool, "task": task, "prompt_version": prompt_version, "run_number": run_number,
                "hospital": hospital_norm, "result": "MISSED_BY_TOOL",
                "gold_item_id": g["item_id"], "gold_text": g["name_or_issue"], "gold_date": g["date"],
                "extracted_text": "", "extracted_date": "", "extracted_source": "", "extracted_link": "",
                "match_score": "", "date_matches": "",
            })
        for e in unmatched_extracted:
            item_level_rows.append({
                "tool": tool, "task": task, "prompt_version": prompt_version, "run_number": run_number,
                "hospital": hospital_norm, "result": "FLAGGED_POSSIBLE_HALLUCINATION_REVIEW_MANUALLY",
                "gold_item_id": "", "gold_text": "", "gold_date": "",
                "extracted_text": e["name_or_issue"], "extracted_date": e["date"],
                "extracted_source": e.get("source", ""), "extracted_link": e.get("link", ""),
                "match_score": "", "date_matches": "",
            })
            
        n_gold = len(gold_items)
        n_matched = len(matched_pairs)
        n_extracted = len(real_extracted)
        recall = n_matched / n_gold if n_gold > 0 else None
        precision = n_matched / n_extracted if n_extracted > 0 else None
        f1 = (2 * recall * precision / (recall + precision)) if recall and precision and (recall + precision) > 0 else None
        date_acc = (
            sum(1 for g, e, s in matched_pairs if score_evaluation.dates_close(g.get("date_parsed"), e.get("date_parsed")))
            / n_matched
        ) if n_matched > 0 else None
        
        hospital_summary_rows.append({
            "tool": tool, "task": task, "prompt_version": prompt_version, "run_number": run_number,
            "hospital": hospital_norm,
            "gold_items": n_gold, "extracted_items": n_extracted, "matched": n_matched,
            "unmatched_gold_missed": len(unmatched_gold),
            "flagged_possible_hallucination": len(unmatched_extracted),
            "recall": round(recall, 3) if recall is not None else None,
            "precision": round(precision, 3) if precision is not None else None,
            "f1": round(f1, 3) if f1 is not None else None,
            "date_field_accuracy": round(date_acc, 3) if date_acc is not None else None,
        })
    
    item_level_df = pd.DataFrame(item_level_rows)
    hospital_summary_df = pd.DataFrame(hospital_summary_rows)
    
    item_level_df.to_csv(os.path.join(out_dir, "item_level_results.csv"), index=False)
    hospital_summary_df.to_csv(os.path.join(out_dir, "hospital_summary.csv"), index=False)
    
    if not hospital_summary_df.empty:
        agg = hospital_summary_df.groupby(["tool", "task", "prompt_version"]).agg(
            total_gold=("gold_items", "sum"),
            total_extracted=("extracted_items", "sum"),
            total_matched=("matched", "sum"),
            total_missed=("unmatched_gold_missed", "sum"),
            total_flagged=("flagged_possible_hallucination", "sum"),
        ).reset_index()
        agg["recall"] = (agg["total_matched"] / agg["total_gold"]).round(3)
        agg["precision"] = (agg["total_matched"] / agg["total_extracted"]).round(3)
        # avoid divide by zero for F1
        denom = agg["recall"] + agg["precision"]
        agg["f1"] = (2 * agg["recall"] * agg["precision"] / denom.where(denom > 0)).round(3)
        agg["hallucination_rate"] = (agg["total_flagged"] / agg["total_extracted"].where(agg["total_extracted"] > 0)).round(3)
        agg.to_csv(os.path.join(out_dir, "tool_summary.csv"), index=False)
        
        print("\n=== TOOL SUMMARY ===")
        print(agg[["tool","task","recall","precision","f1","hallucination_rate"]].to_string(index=False))
    
    # Consistency
    consistency_rows = []
    v0_df = resp_df[resp_df["prompt_version"].str.lower() == "v0"]
    for (tool, task, hospital_norm), group in v0_df.groupby(["tool", "task", "hospital_norm"]):
        gold_items = gold_in_scope[
            (gold_in_scope["hospital_norm"] == hospital_norm) &
            (gold_in_scope["task"] == task)
        ].to_dict("records")
        sets_by_run = {}
        for run_number, run_group in group.groupby("run_number"):
            extracted_items = [
                r for r in run_group.to_dict("records")
                if score_evaluation.normalize_text(r["name_or_issue"]) not in ("none found", "unparsable")
            ]
            matched_pairs, _, _ = smart_match(gold_items, extracted_items, task)
            sets_by_run[run_number] = set(g["item_id"] for g, e, s in matched_pairs)
        consistency_score = score_evaluation.compute_consistency(sets_by_run)
        consistency_rows.append({
            "tool": tool, "task": task, "hospital": hospital_norm,
            "n_runs": len(sets_by_run),
            "mean_pairwise_jaccard": round(consistency_score, 3) if consistency_score is not None else None,
        })
    pd.DataFrame(consistency_rows).to_csv(os.path.join(out_dir, "consistency_results.csv"), index=False)
    
    # Citation analysis (link checking from previous run)
    print(f"\nDone. Metrics written to {out_dir}/")

if __name__ == "__main__":
    score_events()
