"""
score_evaluation.py

Scores extracted LLM/Agent responses against a gold-standard dataset.

INPUTS (edit the CONFIG section below, or pass as command-line args):
  --gold        path to gold CSV for the task (gold_task1_phipa.csv / gold_task2_ceo.csv / gold_task3_supervisors.csv)
  --responses   path to your filled-in extracted_responses.csv (all tools/versions/runs for that task)
  --out         path to write the results CSV

OUTPUTS:
  1. item_level_results.csv   - every extracted item, whether it matched gold, and why
  2. hospital_summary.csv     - recall/precision/F1/hallucination per (tool, prompt_version, run, hospital)
  3. tool_summary.csv         - aggregated per (tool, prompt_version) across all hospitals/runs
  4. consistency_results.csv  - Jaccard similarity across the 5 repeat runs (prompt_version == 'v0' only)
  5. link_check_results.csv   - HTTP validity + credibility tier per link (only for items with a real link)

USAGE:
    python3 score_evaluation.py --gold gold_task1_phipa.csv --responses extracted_responses.csv --out results/

WHAT THIS SCRIPT DOES *NOT* DO (by design — see conversation notes):
  - It does not use an LLM to judge correctness. All matching is deterministic
    (fuzzy string + date proximity), so it is reproducible and auditable.
  - It flags likely hallucinations for YOU to spot-check manually — a flag is
    not proof. Some flags will turn out to be real gold-set gaps you missed.
  - Link "support" (does the page actually confirm the claim) is NOT automated
    here — that needs a bounded LLM read or a human check. This script only
    checks that the URL resolves (HTTP status), which is a much weaker signal.
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from itertools import combinations
from urllib.parse import urlparse

import pandas as pd
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# CONFIG — tune these if your matching seems too strict/loose
# ---------------------------------------------------------------------------

NAME_MATCH_THRESHOLD = 0.55       # fuzzy-match ratio (0-1) above which two
                                   # name_or_issue strings are considered "the
                                   # same real-world item". Lower = more lenient.
DATE_TOLERANCE_DAYS = 3            # extracted date within this many days of the
                                   # gold date still counts as a date match
                                   # (handles "announced" vs "effective" fuzz,
                                   # and minor reporting imprecision)
LINK_CHECK_TIMEOUT = 8             # seconds per URL before marking as unreachable
LINK_CHECK_MAX = 300                # safety cap on how many URLs to HTTP-check in one run

# Source credibility tiers — extend this as you find more domains.
# Lower number = more credible, per the team's own PHIPA/Supervisor ranking:
# Order in Council > Supervisor/official report > national news > local news > hospital site
CREDIBILITY_TIERS = {
    1: ["ontario.ca", "ipc.on.ca", "decisions.ipc.on.ca", "canlii.org"],
    2: ["cbc.ca", "ctvnews.ca", "globalnews.ca", "theglobeandmail.com", "torontostar.com"],
    3: ["newswire.ca", "northernontariobusiness.com", "renfrewtoday.ca", "am800cklw.com"],
    4: [],  # local/regional news not otherwise listed - filled in per-run as needed
    5: [],  # hospital's own domain - detected dynamically per hospital, see credibility_tier()
}

# Hospital domains (used to detect tier 5 "hospital's own site" dynamically)
HOSPITAL_DOMAINS = [
    "mackenziehealth.ca", "arnpriorregionalhealth.ca", "senhosp.ca",
    "redlakehospital.ca", "nygh.on.ca", "wrh.on.ca", "ottawahospital.on.ca",
    "hamiltonhealthsciences.ca", "williamoslerhs.ca", "lhsc.on.ca",
]

# ---------------------------------------------------------------------------
# HOSPITAL NAME NORMALIZATION
# ---------------------------------------------------------------------------

def build_alias_map(gold_df):
    """Build a dict mapping any known alias -> canonical hospital name,
    using the hospital_aliases column in the gold CSV (semicolon-separated)."""
    alias_map = {}
    for _, row in gold_df.iterrows():
        canonical = row["hospital"].strip()
        alias_map[normalize_text(canonical)] = canonical
        aliases = row.get("hospital_aliases", "")
        if pd.notna(aliases) and aliases:
            for a in str(aliases).split(";"):
                a = a.strip()
                if a:
                    alias_map[normalize_text(a)] = canonical
    return alias_map


def normalize_text(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_hospital(name, alias_map):
    key = normalize_text(name)
    return alias_map.get(key, name.strip() if isinstance(name, str) else name)


# ---------------------------------------------------------------------------
# DATE PARSING
# ---------------------------------------------------------------------------

def try_parse_date(s):
    """Best-effort date parser for the messy free-text dates LLMs produce.
    Returns a datetime.date or None."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    if s.upper() in ("NONE", "N/A", "NOT STATED", ""):
        return None
    fmts = [
        "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # last resort: pull a YYYY-MM-DD or "Month DD, YYYY" substring out of noisy text
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.strptime(m.group(0), "%Y-%m-%d").date()
        except ValueError:
            pass
    m = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        s,
        re.IGNORECASE,
    )
    if m:
        try:
            return datetime.strptime(m.group(0).replace(",", ""), "%B %d %Y").date()
        except ValueError:
            pass
    return None


def dates_close(d1, d2, tolerance_days=DATE_TOLERANCE_DAYS):
    if d1 is None or d2 is None:
        return False
    return abs((d1 - d2).days) <= tolerance_days


# ---------------------------------------------------------------------------
# FUZZY TEXT MATCHING
# ---------------------------------------------------------------------------

def text_similarity(a, b):
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


# ---------------------------------------------------------------------------
# CORE MATCHING: extracted items <-> gold items, per hospital
# ---------------------------------------------------------------------------

def match_hospital_group(gold_items, extracted_items):
    """
    gold_items / extracted_items: lists of dicts with keys
      item_id (gold only), name_or_issue, date (raw string), date_parsed
    Returns: matched_pairs (list of (gold_item, extracted_item, score)),
             unmatched_gold (list), unmatched_extracted (list)
    """
    gold_pool = list(gold_items)
    extracted_pool = list(extracted_items)
    matched_pairs = []

    # Greedy best-match: repeatedly find the single best remaining pair above
    # threshold, remove both, repeat. This avoids double-matching one gold
    # item to two extracted items (or vice versa).
    while gold_pool and extracted_pool:
        best_score = -1
        best_pair = None
        for g in gold_pool:
            for e in extracted_pool:
                score = text_similarity(g["name_or_issue"], e["name_or_issue"])
                # small bonus if dates also line up - helps disambiguate
                # near-identical names (e.g. two "Board Director" rows)
                if dates_close(g.get("date_parsed"), e.get("date_parsed")):
                    score += 0.15
                score = min(score, 1.0)  # cap for readability - bonus can push raw ratio over 1.0
                if score > best_score:
                    best_score = score
                    best_pair = (g, e)
        if best_score >= NAME_MATCH_THRESHOLD and best_pair:
            g, e = best_pair
            matched_pairs.append((g, e, best_score))
            gold_pool.remove(g)
            extracted_pool.remove(e)
        else:
            break  # no more matches above threshold

    return matched_pairs, gold_pool, extracted_pool  # unmatched_gold, unmatched_extracted


# ---------------------------------------------------------------------------
# LINK CHECKING
# ---------------------------------------------------------------------------

def check_link(url):
    """Returns (is_valid, status_note). Best-effort; treats any 2xx/3xx as valid."""
    if not url or str(url).strip().upper() in ("NONE", "N/A", ""):
        return None, "no_link_provided"
    try:
        req = urllib.request.Request(url, method='HEAD')
        try:
            resp = urllib.request.urlopen(req, timeout=LINK_CHECK_TIMEOUT)
            return resp.status < 400, f"http_{resp.status}"
        except urllib.error.HTTPError as e:
            if e.code >= 400:
                # retry with GET
                req = urllib.request.Request(url, method='GET')
                resp = urllib.request.urlopen(req, timeout=LINK_CHECK_TIMEOUT)
                return resp.status < 400, f"http_{resp.status}"
            return False, f"http_{e.code}"
    except Exception as e:
        return False, f"error_{type(e).__name__}"


def credibility_tier(url):
    if not url or str(url).strip().upper() in ("NONE", "N/A", ""):
        return None
    domain = urlparse(str(url)).netloc.lower().replace("www.", "")
    for tier, domains in CREDIBILITY_TIERS.items():
        if any(d in domain for d in domains):
            return tier
    if any(d in domain for d in HOSPITAL_DOMAINS):
        return 5
    return 4  # unrecognized domain - treat as "other/local" until you extend the list


# ---------------------------------------------------------------------------
# CONSISTENCY (Jaccard similarity across the 5 repeat runs of prompt_version == v0)
# ---------------------------------------------------------------------------

def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 1.0  # both empty = perfectly consistent (agreed on "nothing")
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def compute_consistency(matched_item_sets_by_run):
    """matched_item_sets_by_run: dict run_number -> set of gold item_ids matched.
    Returns mean pairwise Jaccard similarity across all run pairs."""
    runs = list(matched_item_sets_by_run.values())
    if len(runs) < 2:
        return None
    scores = [jaccard(a, b) for a, b in combinations(runs, 2)]
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# MAIN SCORING PIPELINE
# ---------------------------------------------------------------------------

def run_scoring(gold_path, responses_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    gold_df = pd.read_csv(gold_path, dtype=str).fillna("")
    resp_df = pd.read_csv(responses_path, dtype=str).fillna("")

    alias_map = build_alias_map(gold_df)

    # normalize hospital names on both sides
    gold_df["hospital_norm"] = gold_df["hospital"].apply(lambda h: normalize_hospital(h, alias_map))
    resp_df["hospital_norm"] = resp_df["hospital"].apply(lambda h: normalize_hospital(h, alias_map))

    # only in-scope gold items count toward recall/precision denominators
    gold_in_scope = gold_df[gold_df["in_scope"].str.strip().str.lower() == "true"].copy()
    gold_in_scope["date_parsed"] = gold_in_scope["date"].apply(try_parse_date)

    resp_df["date_parsed"] = resp_df["date"].apply(try_parse_date)

    item_level_rows = []
    hospital_summary_rows = []

    # group extracted responses by (tool, prompt_version, run_number, hospital)
    group_cols = ["tool", "task", "prompt_version", "run_number", "hospital_norm"]
    for keys, group in resp_df.groupby(group_cols):
        tool, task, prompt_version, run_number, hospital_norm = keys

        gold_items = gold_in_scope[gold_in_scope["hospital_norm"] == hospital_norm].to_dict("records")
        extracted_items = group.to_dict("records")

        # drop explicit "NONE FOUND" placeholder rows from matching (they're
        # informational, not a real claim) but keep a record of them
        real_extracted = [e for e in extracted_items if normalize_text(e["name_or_issue"]) != "none found"]

        matched_pairs, unmatched_gold, unmatched_extracted = match_hospital_group(gold_items, real_extracted)

        matched_gold_ids = set(g["item_id"] for g, e, s in matched_pairs)

        for g, e, score in matched_pairs:
            date_match = dates_close(g.get("date_parsed"), e.get("date_parsed"))
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
        date_acc = (sum(1 for g, e, s in matched_pairs if dates_close(g.get("date_parsed"), e.get("date_parsed")))
                    / n_matched) if n_matched > 0 else None

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

    # ---- tool-level aggregation (sum counts, then recompute rates - avoids
    # averaging-of-ratios distortion when hospitals have very different gold sizes) ----
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
        agg["f1"] = (2 * agg["recall"] * agg["precision"] / (agg["recall"] + agg["precision"])).round(3)
        agg["hallucination_rate"] = (agg["total_flagged"] / agg["total_extracted"]).round(3)
        agg.to_csv(os.path.join(out_dir, "tool_summary.csv"), index=False)

    # ---- consistency: only meaningful where prompt_version == v0 and run_number 1-5 exist ----
    consistency_rows = []
    v0_df = resp_df[resp_df["prompt_version"].str.lower() == "v0"]
    for (tool, task, hospital_norm), group in v0_df.groupby(["tool", "task", "hospital_norm"]):
        gold_items = gold_in_scope[gold_in_scope["hospital_norm"] == hospital_norm].to_dict("records")
        sets_by_run = {}
        for run_number, run_group in group.groupby("run_number"):
            extracted_items = [r for r in run_group.to_dict("records")
                                if normalize_text(r["name_or_issue"]) != "none found"]
            matched_pairs, _, _ = match_hospital_group(gold_items, extracted_items)
            sets_by_run[run_number] = set(g["item_id"] for g, e, s in matched_pairs)
        consistency_score = compute_consistency(sets_by_run)
        consistency_rows.append({
            "tool": tool, "task": task, "hospital": hospital_norm,
            "n_runs": len(sets_by_run),
            "mean_pairwise_jaccard": round(consistency_score, 3) if consistency_score is not None else None,
        })
    pd.DataFrame(consistency_rows).to_csv(os.path.join(out_dir, "consistency_results.csv"), index=False)

    # ---- link checking (bounded, only for unique links that appear) ----
    all_links = set()
    for col in ["link"]:
        all_links.update(v for v in resp_df[col].tolist() if v and v.strip().upper() not in ("NONE", "N/A", ""))
    all_links = list(all_links)[:LINK_CHECK_MAX]
    link_rows = []
    for url in all_links:
        valid, note = check_link(url)
        tier = credibility_tier(url)
        link_rows.append({"link": url, "valid": valid, "note": note, "credibility_tier": tier})
    pd.DataFrame(link_rows).to_csv(os.path.join(out_dir, "link_check_results.csv"), index=False)

    print(f"Done. Wrote results to {out_dir}/")
    print(f"  - item_level_results.csv   ({len(item_level_df)} rows)")
    print(f"  - hospital_summary.csv     ({len(hospital_summary_df)} rows)")
    print(f"  - tool_summary.csv")
    print(f"  - consistency_results.csv ({len(consistency_rows)} rows)")
    print(f"  - link_check_results.csv  ({len(link_rows)} links checked, capped at {LINK_CHECK_MAX})")
    print()
    print("NEXT STEP: open item_level_results.csv and manually review every row")
    print("tagged FLAGGED_POSSIBLE_HALLUCINATION_REVIEW_MANUALLY - confirm each")
    print("is a real hallucination and not a gold-set gap before citing hallucination_rate.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score extracted LLM/Agent responses against gold dataset")
    parser.add_argument("--gold", required=True, help="Path to gold CSV for this task")
    parser.add_argument("--responses", required=True, help="Path to filled-in extracted_responses.csv")
    parser.add_argument("--out", default="results", help="Output directory")
    args = parser.parse_args()
    run_scoring(args.gold, args.responses, args.out)
