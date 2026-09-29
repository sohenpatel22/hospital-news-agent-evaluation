"""
03_deterministic_score.py
=========================
Deterministic metrics — no LLM required, no API cost.

Metrics:
  - exact_match_f1:     Smart name/ID matching precision, recall, F1
  - citation_accuracy:  HTTP validity + domain credibility tier per link
  - abstention_correct: Did model correctly say "none" for CONFIRMED ZERO hospitals?
"""

import os
import re
import json
import pathlib
import urllib.request
import urllib.error
import pandas as pd
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "Evaluation Code"))
import score_evaluation

BASE = pathlib.Path(__file__).parent
EXTRACTED_DIR = BASE / "extracted_events"
GOLD_CSV = BASE.parent / "deterministic_pipeline" / "gold" / "all_gold.csv"
OUT_DIR = BASE / "metrics"

LINK_CHECK_TIMEOUT = 8
LINK_CHECK_MAX = 200  # cap total URLs to avoid long runtimes

CREDIBILITY_TIERS = {
    1: ["ontario.ca", "ipc.on.ca", "decisions.ipc.on.ca", "canlii.org"],
    2: ["cbc.ca", "ctvnews.ca", "globalnews.ca", "theglobeandmail.com", "torontostar.com"],
    3: ["newswire.ca", "northernontariobusiness.com", "renfrewtoday.ca", "am800cklw.com",
        "mackenziehealth.ca", "arnpriorregionalhealth.ca", "nygh.on.ca", "wrh.on.ca",
        "ottawahospital.on.ca", "hamiltonhealthsciences.ca", "williamoslerhs.ca", "lhsc.on.ca"],
}


def slug(s):
    return re.sub(r'[^\w]', '_', str(s))[:50]

def check_link(url):
    if not url or str(url).strip().upper() in ("NONE", "N/A", "", "NULL"):
        return None, "no_link"
    try:
        req = urllib.request.Request(str(url), method='HEAD',
                                     headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=LINK_CHECK_TIMEOUT)
        return resp.status < 400, f"http_{resp.status}"
    except urllib.error.HTTPError as e:
        return e.code < 400, f"http_{e.code}"
    except Exception as e:
        return False, f"error_{type(e).__name__}"

def credibility_tier(url):
    if not url or str(url).strip().upper() in ("NONE", "N/A", "", "NULL"):
        return None
    from urllib.parse import urlparse
    domain = urlparse(str(url)).netloc.lower().replace("www.", "")
    for tier, domains in CREDIBILITY_TIERS.items():
        if any(d in domain for d in domains):
            return tier
    return 4

def load_extracted_flat(task, model, hospital) -> list[dict]:
    """Load all events from all runs, deduped."""
    task_dir = EXTRACTED_DIR / task / slug(model)
    all_events = []
    declared_none = False
    seen = set()
    for f in sorted(task_dir.glob(f"{slug(hospital)}_run*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("model_declared_none"):
                declared_none = True
            for e in data.get("events", []):
                key = str(e.get("name_or_issue", ""))[:80]
                if key not in seen:
                    seen.add(key)
                    e["_run"] = data.get("run_number", 1)
                    all_events.append(e)
        except Exception:
            pass
    return all_events, declared_none

def compute_exact_match_f1(gold_items, extracted_events, task):
    """Reuse the smart matcher from 04_score.py logic."""
    gold_pool = list(gold_items)
    extracted_pool = [{"name_or_issue": e.get("name_or_issue",""), 
                       "date_parsed": score_evaluation.try_parse_date(e.get("date") or e.get("appointment_date",""))}
                      for e in extracted_events]
    gold_prepared = [{"item_id": g.get("item_id",""), 
                      "name_or_issue": g.get("name_or_issue",""),
                      "date_parsed": score_evaluation.try_parse_date(g.get("date",""))}
                     for g in gold_pool]
    
    # Use smart matching (name/ID based)
    matched = 0
    used_extracted = set()
    
    for g in gold_prepared:
        gold_name_raw = re.match(r'^(.+?)\s*-\s*', g["name_or_issue"])
        gold_name = gold_name_raw.group(1).strip().lower() if gold_name_raw else g["name_or_issue"].lower()
        
        # PHIPA ID extraction
        gold_ids = score_evaluation.normalize_text(g["name_or_issue"])
        phipa_id_match = re.search(r'(phipa\s*decision\s*\d+|po-\d+)', gold_ids, re.IGNORECASE)
        gold_phipa_id = phipa_id_match.group(0) if phipa_id_match else None
        
        for i, e in enumerate(extracted_pool):
            if i in used_extracted:
                continue
            pred_text = e["name_or_issue"].lower()
            
            # Name match
            name_match = gold_name in pred_text or (len(gold_name.split()) >= 2 and gold_name.split()[-1] in pred_text)
            # PHIPA ID match
            id_match = gold_phipa_id and gold_phipa_id.replace(' ', '') in pred_text.replace(' ', '')
            # Fuzzy fallback
            fuzzy = score_evaluation.text_similarity(g["name_or_issue"], e["name_or_issue"]) >= 0.55
            
            if name_match or id_match or fuzzy:
                matched += 1
                used_extracted.add(i)
                break
    
    n_gold = len(gold_prepared)
    n_extracted = len(extracted_pool)
    recall = matched / n_gold if n_gold > 0 else None
    precision = matched / n_extracted if n_extracted > 0 else None
    f1 = (2*recall*precision/(recall+precision)) if recall and precision and (recall+precision) > 0 else None
    
    return {
        "gold_count": n_gold,
        "extracted_count": n_extracted,
        "matched": matched,
        "recall": round(recall, 3) if recall is not None else None,
        "precision": round(precision, 3) if precision is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
    }


def run_deterministic():
    print("--- Stage 3: Deterministic Scoring ---")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    gold_df = pd.read_csv(GOLD_CSV)
    gold_df["in_scope"] = gold_df["in_scope"].astype(str).str.strip().str.lower() == "true"
    
    # Confirmed-zero hospitals per task
    zero_hospitals = {
        "phipa": gold_df[(gold_df["task"]=="phipa") & (gold_df["in_scope"]==False) & 
                         (gold_df["notes"].str.contains("CONFIRMED ZERO", na=False))]["hospital"].tolist(),
        "ceo": gold_df[(gold_df["task"]=="ceo") & (gold_df["in_scope"]==False) & 
                       (gold_df["notes"].str.contains("CONFIRMED ZERO", na=False))]["hospital"].tolist(),
        "supervisors": gold_df[(gold_df["task"]=="supervisors") & (gold_df["in_scope"]==False) & 
                               (gold_df["notes"].str.contains("CONFIRMED ZERO", na=False))]["hospital"].tolist(),
    }
    
    MODELS = ["MS Copilot Agent", "ChatGPT", "Claude", "Gemini", "Perplexity"]
    TASKS = ["phipa", "ceo", "supervisors"]
    
    rows = []
    all_links = []
    
    for task in TASKS:
        for model in MODELS:
            task_dir = EXTRACTED_DIR / task / slug(model)
            if not task_dir.exists():
                continue
            
            hospitals = set()
            for f in task_dir.glob("*_run*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    hospitals.add(data.get("hospital",""))
                except Exception:
                    pass
            
            for hospital in sorted(hospitals):
                if not hospital:
                    continue
                
                extracted_events, declared_none = load_extracted_flat(task, model, hospital)
                
                # Gold items
                gold_items = gold_df[
                    (gold_df["task"] == task) &
                    (gold_df["in_scope"] == True) &
                    (gold_df["hospital"].str.lower().str.strip() == hospital.lower().strip())
                ].to_dict("records")
                
                # Exact match F1
                f1_scores = compute_exact_match_f1(gold_items, extracted_events, task)
                
                # Abstention correctness
                is_zero_hospital = hospital in zero_hospitals.get(task, [])
                has_events = len(extracted_events) > 0
                if is_zero_hospital:
                    abstention_correct = declared_none and not has_events
                else:
                    abstention_correct = None  # N/A for hospitals that should have events
                
                # Collect links for citation checking
                for e in extracted_events:
                    link = e.get("link")
                    if link and "http" in str(link):
                        all_links.append({
                            "task": task, "model": model, "hospital": hospital,
                            "link": link, "name_or_issue": e.get("name_or_issue","")
                        })
                
                rows.append({
                    "task": task,
                    "model": model,
                    "hospital": hospital,
                    "is_zero_hospital": is_zero_hospital,
                    "model_declared_none": declared_none,
                    "abstention_correct": abstention_correct,
                    **f1_scores
                })
    
    df_scores = pd.DataFrame(rows)
    df_scores.to_csv(OUT_DIR / "deterministic_scores.csv", index=False)
    print(f"Saved deterministic_scores.csv ({len(df_scores)} rows)")
    
    # Citation accuracy (bounded)
    print(f"\nChecking {min(len(all_links), LINK_CHECK_MAX)} citations (capped at {LINK_CHECK_MAX})...")
    link_rows = []
    checked = set()
    for item in all_links[:LINK_CHECK_MAX]:
        url = item["link"]
        if url in checked:
            continue
        checked.add(url)
        valid, note = check_link(url)
        tier = credibility_tier(url)
        link_rows.append({**item, "valid": valid, "note": note, "credibility_tier": tier})
    
    df_links = pd.DataFrame(link_rows)
    df_links.to_csv(OUT_DIR / "citation_analysis.csv", index=False)
    
    # Summary: citation accuracy per model
    if not df_links.empty:
        cite_summary = df_links.groupby("model").agg(
            total_links=("link","count"),
            valid_links=("valid", lambda x: x.sum()),
            avg_credibility_tier=("credibility_tier", "mean")
        ).round(2)
        cite_summary["citation_accuracy"] = (cite_summary["valid_links"] / cite_summary["total_links"]).round(3)
        cite_summary.to_csv(OUT_DIR / "citation_summary.csv")
        print("\nCitation Accuracy by Model:")
        print(cite_summary[["total_links","valid_links","citation_accuracy","avg_credibility_tier"]].to_string())
    
    print(f"\nDone. Written to {OUT_DIR}/")

if __name__ == "__main__":
    run_deterministic()
