"""
Stage 2 — entity matching mechanics.

Modes:
  --candidates   Load gold (all 3 sheets) + all extracted items, generate
                 match candidates per item:
                   - Tier "exact": identical after deterministic
                     normalisation (honorifics/case/punctuation/suffix
                     strip, parenthetical-nickname expansion, hardcoded
                     documented spelling variants). Auto-accepted — this is
                     rule-based, not a fuzzy guess, so it does not violate
                     "never auto-accept a fuzzy match".
                   - Tier "fuzzy_high" (rapidfuzz score >= 85) and
                     "fuzzy_low" (70-84): NOT auto-accepted. Written to
                     /output/matched/_candidates_for_confirmation.json for
                     an LLM (Claude, acting as the confirming judge) to
                     accept/reject with a one-line reason.
                 Candidates are generated across ALL hospitals for the
                 item's task (not just the item's own hospital) so that
                 "right person, wrong hospital" cases are detected as
                 organisational errors rather than silently dropped.
                 Person-name matching only; hospital agreement is recorded
                 per candidate but does not gate candidate generation.

  --resolve      After /output/matched/_candidates_for_confirmation.json
                 has been filled in with a "decision" (accept/reject) and
                 "reason" per candidate (done by Claude directly, see
                 confirm_candidates.py or manual edit), merge everything
                 into final per-item match results:
                   /output/matched/<same stem as extracted file>.json
                     -> list of {item_index, matched_gold_item_id,
                                 match_confidence, match_reason}
                   /output/matched/unmatched_gold.json
                     -> gold rows (per task) that no system item matched
                   /output/matched/organisational_errors.json
                     -> right-person-wrong-hospital candidates (name matched
                        but hospital did not), for Stage 3 bucket C
                 Then print the summary table.
"""

import argparse
import json
import os
import re
import sys

import pandas as pd
from rapidfuzz import fuzz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /eval
GOLD_PATH = os.path.join(ROOT, "data", "gold.xlsx")
EXTRACTED_DIR = os.path.join(ROOT, "output", "extracted")
MATCHED_DIR = os.path.join(ROOT, "output", "matched")
CANDIDATES_PATH = os.path.join(MATCHED_DIR, "_candidates_for_confirmation.json")
GOLD_INDEX_PATH = os.path.join(MATCHED_DIR, "_gold_index.json")
EXTRACTED_INDEX_PATH = os.path.join(MATCHED_DIR, "_extracted_index.json")

SHEET_TO_TASK = {
    "CEOs": "ceo",
    "PHIPA": "phipa",
    "Leadership changes (Supervisor)": "supervisor",
}

HONORIFICS = {"dr", "mr", "mrs", "ms", "miss", "prof", "professor", "hon", "honourable", "the"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}

# Documented spelling variants from EVALUATION_PLAN.md section 1.1 / 1.3.
# Each tuple is treated as mutually interchangeable; all forms normalise to
# the first (canonical) form.
SPELLING_VARIANT_GROUPS = [
    ("pete kenney", "pete kenny"),
    ("mark macgowan", "mark macgown"),
    ("mary agnes wilson", "mary agnes wilson"),  # hyphen removed by normalisation anyway
    ("nicole cahon", "nicole mccahon"),
    ("atlaf stationwala", "altaf stationwala"),
]


def build_spelling_variant_map():
    m = {}
    for group in SPELLING_VARIANT_GROUPS:
        canonical = group[0]
        for variant in group:
            m[variant] = canonical
    return m


SPELLING_VARIANT_MAP = build_spelling_variant_map()


NICKNAME_QUOTE_RE = re.compile(r"[\"‘’“”']([^\"‘’“”']+)[\"‘’“”']")


def strip_parenthetical_nickname(name):
    """'Richard (Rick) Holock' or 'Richard "Rick" Holock' (straight or
    curly quotes) -> ['Richard Holock', 'Rick Holock']. If neither
    pattern is present, returns [name]."""
    m = re.search(r"\(([^)]+)\)", name)
    if not m:
        m = NICKNAME_QUOTE_RE.search(name)
    if not m:
        return [name]
    nickname = m.group(1).strip()
    without_marker = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    without_marker = NICKNAME_QUOTE_RE.sub(" ", without_marker).strip()
    without_marker = re.sub(r"\s+", " ", without_marker)
    # without_marker is presumably "First Last"; substitute nickname for first token
    tokens = without_marker.split(" ")
    if len(tokens) >= 2:
        nickname_form = " ".join([nickname] + tokens[1:])
    else:
        nickname_form = nickname
    return [without_marker, nickname_form]


def normalise_name(raw):
    """Deterministic normalisation for exact-match comparison:
    lowercase, strip honorifics/suffixes, strip punctuation, collapse
    whitespace, apply documented spelling-variant map, sort-independent
    hyphen handling (hyphens treated as spaces)."""
    s = raw.lower()
    s = s.replace("-", " ")
    s = re.sub(r"[.,]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = [t for t in s.split(" ") if t not in HONORIFICS and t not in SUFFIXES]
    s = " ".join(tokens)
    s = SPELLING_VARIANT_MAP.get(s, s)
    return s


def name_variants(raw):
    """All normalised-name forms worth comparing for a single raw name
    string (handles parenthetical nicknames and comma-separated
    professional-credential suffixes, e.g. 'Simone Atungo, MES, ICD.D,
    AccBD' -> also generates the 'Simone Atungo' variant. Without this,
    gold rows with credentials appended never matched system items, which
    only ever name the bare person -- found 2026-08-31 via a missed Simone
    Atungo match)."""
    variants = set()
    for form in strip_parenthetical_nickname(raw):
        variants.add(normalise_name(form))
        if "," in form:
            variants.add(normalise_name(form.split(",")[0]))
    return variants


def split_gold_name_or_issue(raw):
    """Gold's name_or_issue is formatted 'Name - Role (detail)' (or
    'Issue - description' for PHIPA). Split on the first ' - ' (spaces
    required, so internal hyphens like 'Mary-Agnes' or 'Stitt-Cavanagh'
    are left alone). Returns (core_name_or_issue, role_or_detail_text)."""
    parts = re.split(r"\s+-\s+", raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw.strip(), None


def parse_aliases(alias_str, canonical):
    aliases = {canonical.strip().lower()}
    if isinstance(alias_str, str) and alias_str.strip():
        for part in re.split(r"[;,]", alias_str):
            part = part.strip().lower()
            if part:
                aliases.add(part)
    return aliases


def load_gold():
    xls = pd.ExcelFile(GOLD_PATH)
    gold_items = []  # flat list across all 3 sheets
    for sheet, task in SHEET_TO_TASK.items():
        df = pd.read_excel(xls, sheet_name=sheet, header=2)
        df.dropna(how="all", inplace=True)
        for _, row in df.iterrows():
            item_id = row.get("item_id")
            if pd.isna(item_id):
                continue
            hospital = str(row.get("hospital", "")).strip()
            alias_set = parse_aliases(row.get("hospital_aliases"), hospital)
            name_or_issue = str(row.get("name_or_issue", "")).strip()
            core_name, role_detail = split_gold_name_or_issue(name_or_issue)
            gold_items.append(
                {
                    "gold_item_id": str(item_id),
                    "task": task,
                    "hospital": hospital,
                    "hospital_aliases": sorted(alias_set),
                    "name_or_issue": name_or_issue,
                    "core_name_or_issue": core_name,
                    "role_detail": role_detail,
                    "name_variants": sorted(name_variants(core_name)),
                    "date": None
                    if pd.isna(row.get("date (YYYY-MM-DD)"))
                    else str(row.get("date (YYYY-MM-DD)")),
                    "in_scope": str(row.get("in_scope", "")).strip().upper(),
                    "confidence_tier": None
                    if "confidence_tier" not in row or pd.isna(row.get("confidence_tier"))
                    else str(row.get("confidence_tier")),
                    "notes": None if pd.isna(row.get("notes")) else str(row.get("notes")),
                }
            )
    return gold_items


def canonical_hospital_for(hospital_text, gold_items, task):
    """Return canonical gold hospital name if hospital_text matches any
    alias set for this task, else None."""
    h = hospital_text.strip().lower()
    seen = {}
    for g in gold_items:
        if g["task"] != task:
            continue
        seen[g["hospital"]] = set(g["hospital_aliases"])
    for canonical, aliases in seen.items():
        if h in aliases or h == canonical.lower():
            return canonical
    return None


def load_extracted_items():
    items = []
    for fname in sorted(os.listdir(EXTRACTED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        with open(os.path.join(EXTRACTED_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        for it in data.get("items", []):
            items.append(
                {
                    "source_extracted_file": fname,
                    **it,
                }
            )
    return items


def item_uid(item):
    return (
        f"{item['task']}__{item['system']}__{item['hospital']}__"
        f"run{item['run_number']}__idx{item['item_index']}"
    )


def generate_candidates():
    os.makedirs(MATCHED_DIR, exist_ok=True)
    gold_items = load_gold()
    extracted_items = load_extracted_items()

    with open(GOLD_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(gold_items, f, indent=2)

    gold_by_task = {}
    for g in gold_items:
        gold_by_task.setdefault(g["task"], []).append(g)

    auto_accepted = []  # exact-normalised matches, no LLM needed
    needs_confirmation = []  # fuzzy candidates needing LLM accept/reject
    no_candidate = []  # nothing above threshold at all

    for item in extracted_items:
        task = item["task"]
        raw_name = item.get("person_or_issue", "") or ""
        item_variants = name_variants(raw_name)
        item_hospital_canonical = canonical_hospital_for(item["hospital"], gold_items, task)

        best_by_gold = []  # (gold_item, score, tier, matched_variant_pair)
        for g in gold_by_task.get(task, []):
            best_score = 0
            best_pair = None
            for iv in item_variants:
                if not iv:
                    continue
                for gv in g["name_variants"]:
                    if not gv:
                        continue
                    if iv == gv:
                        score = 100
                    else:
                        score = fuzz.token_sort_ratio(iv, gv)
                    if score > best_score:
                        best_score = score
                        best_pair = (iv, gv)
            if best_score >= 70:
                best_by_gold.append((g, best_score, best_pair))

        best_by_gold.sort(key=lambda x: -x[1])
        top = best_by_gold[:5]

        if not top:
            no_candidate.append(
                {
                    "item_uid": item_uid(item),
                    "item": item,
                    "item_hospital_canonical": item_hospital_canonical,
                }
            )
            continue

        exact_same_hospital = [
            t for t in top if t[1] == 100 and t[0]["hospital"] == item_hospital_canonical
        ]
        if exact_same_hospital:
            g, score, pair = exact_same_hospital[0]
            auto_accepted.append(
                {
                    "item_uid": item_uid(item),
                    "item": item,
                    "matched_gold_item_id": g["gold_item_id"],
                    "gold_name": g["name_or_issue"],
                    "gold_hospital": g["hospital"],
                    "score": score,
                    "match_confidence": "high",
                    "match_reason": (
                        f"exact after normalisation (matched form '{pair[0]}' == '{pair[1]}'); "
                        f"hospital agrees ({item_hospital_canonical})"
                    ),
                }
            )
            continue

        candidates_out = []
        for g, score, pair in top:
            tier = "exact_diff_hospital" if score == 100 else ("fuzzy_high" if score >= 85 else "fuzzy_low")
            candidates_out.append(
                {
                    "gold_item_id": g["gold_item_id"],
                    "gold_name": g["name_or_issue"],
                    "gold_hospital": g["hospital"],
                    "gold_date": g["date"],
                    "gold_in_scope": g["in_scope"],
                    "gold_confidence_tier": g["confidence_tier"],
                    "gold_notes": g["notes"],
                    "score": score,
                    "tier": tier,
                    "matched_form_item": pair[0],
                    "matched_form_gold": pair[1],
                    "hospital_agrees": g["hospital"] == item_hospital_canonical,
                    "decision": None,  # to be filled: "accept" | "reject"
                    "decision_reason": None,  # one-line reason, to be filled
                }
            )

        needs_confirmation.append(
            {
                "item_uid": item_uid(item),
                "item": item,
                "item_hospital_canonical": item_hospital_canonical,
                "candidates": candidates_out,
            }
        )

    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "auto_accepted": auto_accepted,
                "needs_confirmation": needs_confirmation,
                "no_candidate": no_candidate,
            },
            f,
            indent=2,
        )

    print(f"Extracted items: {len(extracted_items)}")
    print(f"Gold items: {len(gold_items)}")
    print(f"Auto-accepted (exact normalised match, same hospital): {len(auto_accepted)}")
    print(f"Needs LLM confirmation (fuzzy/cross-hospital candidates): {len(needs_confirmation)}")
    print(f"No candidate at all (score < 70 vs every gold row in task): {len(no_candidate)}")
    print(f"\nWritten to {CANDIDATES_PATH}")
    print("Next: have Claude (as confirming judge) fill in 'decision'/'decision_reason' for")
    print("every candidate in needs_confirmation, then run match.py --resolve")


def resolve():
    if not os.path.exists(CANDIDATES_PATH):
        print("Run --candidates first.")
        sys.exit(1)
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    gold_items = json.load(open(GOLD_INDEX_PATH, encoding="utf-8"))
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}

    unresolved = [
        c
        for entry in data["needs_confirmation"]
        for c in entry["candidates"]
        if c["decision"] is None
    ]
    if unresolved:
        print(f"WARNING: {len(unresolved)} candidates still have decision=null. "
              f"Resolve them before trusting this output.")

    results = []  # per-item match result
    organisational_errors = []
    matched_gold_ids = set()

    for entry in data["auto_accepted"]:
        results.append(
            {
                "item_uid": entry["item_uid"],
                "item": entry["item"],
                "matched_gold_item_id": entry["matched_gold_item_id"],
                "match_confidence": entry["match_confidence"],
                "match_reason": entry["match_reason"],
            }
        )
        matched_gold_ids.add(entry["matched_gold_item_id"])

    for entry in data["needs_confirmation"]:
        item = entry["item"]
        accepted = [c for c in entry["candidates"] if c["decision"] == "accept"]
        accepted_same_hospital = [c for c in accepted if c["hospital_agrees"]]
        accepted_diff_hospital = [c for c in accepted if not c["hospital_agrees"]]

        if accepted_same_hospital:
            best = accepted_same_hospital[0]
            confidence = "medium" if best["tier"] != "fuzzy_low" else "low"
            results.append(
                {
                    "item_uid": entry["item_uid"],
                    "item": item,
                    "matched_gold_item_id": best["gold_item_id"],
                    "match_confidence": confidence,
                    "match_reason": best["decision_reason"] or f"LLM-confirmed {best['tier']} match",
                }
            )
            matched_gold_ids.add(best["gold_item_id"])
        elif accepted_diff_hospital:
            best = accepted_diff_hospital[0]
            results.append(
                {
                    "item_uid": entry["item_uid"],
                    "item": item,
                    "matched_gold_item_id": None,
                    "match_confidence": "n/a",
                    "match_reason": (
                        f"right person, wrong hospital vs gold_item_id={best['gold_item_id']} "
                        f"({best['gold_hospital']}) -> organisational error, not a match"
                    ),
                }
            )
            organisational_errors.append(
                {
                    "item_uid": entry["item_uid"],
                    "item": item,
                    "gold_item_id": best["gold_item_id"],
                    "gold_name": best["gold_name"],
                    "gold_hospital": best["gold_hospital"],
                    "item_hospital": item["hospital"],
                    "reason": best["decision_reason"],
                }
            )
        else:
            results.append(
                {
                    "item_uid": entry["item_uid"],
                    "item": item,
                    "matched_gold_item_id": None,
                    "match_confidence": "n/a",
                    "match_reason": "no candidate accepted by LLM confirmation",
                }
            )

    for entry in data["no_candidate"]:
        results.append(
            {
                "item_uid": entry["item_uid"],
                "item": entry["item"],
                "matched_gold_item_id": None,
                "match_confidence": "n/a",
                "match_reason": "no candidate with name-similarity score >= 70 in this task",
            }
        )

    # Write per-source-file matched output
    by_file = {}
    for r in results:
        by_file.setdefault(r["item"]["source_extracted_file"], []).append(r)

    for fname, rows in by_file.items():
        out_name = fname  # same stem as extracted file
        out_path = os.path.join(MATCHED_DIR, out_name)
        payload = [
            {
                "item_index": r["item"]["item_index"],
                "matched_gold_item_id": r["matched_gold_item_id"],
                "match_confidence": r["match_confidence"],
                "match_reason": r["match_reason"],
            }
            for r in rows
        ]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    # unmatched_gold.json: gold rows never matched, per task
    unmatched_gold_by_task = {}
    for g in gold_items:
        if g["gold_item_id"] not in matched_gold_ids:
            unmatched_gold_by_task.setdefault(g["task"], []).append(g)
    with open(os.path.join(MATCHED_DIR, "unmatched_gold.json"), "w", encoding="utf-8") as f:
        json.dump(unmatched_gold_by_task, f, indent=2)

    with open(os.path.join(MATCHED_DIR, "organisational_errors.json"), "w", encoding="utf-8") as f:
        json.dump(organisational_errors, f, indent=2)

    # Summary
    print("=== system x task -> matched / unmatched-system-item / low-confidence ===")
    agg = {}
    for r in results:
        key = (r["item"]["system"], r["item"]["task"])
        a = agg.setdefault(key, {"matched": 0, "unmatched": 0, "low_conf": 0})
        if r["matched_gold_item_id"]:
            a["matched"] += 1
            if r["match_confidence"] == "low":
                a["low_conf"] += 1
        else:
            a["unmatched"] += 1

    header = f"{'system':<18} {'task':<12} {'matched':<9} {'unmatched':<11} {'low_conf':<9}"
    print(header)
    print("-" * len(header))
    for (system, task), a in sorted(agg.items()):
        print(f"{system:<18} {task:<12} {a['matched']:<9} {a['unmatched']:<11} {a['low_conf']:<9}")

    total_matched = sum(a["matched"] for a in agg.values())
    total_unmatched = sum(a["unmatched"] for a in agg.values())
    total_low_conf = sum(a["low_conf"] for a in agg.values())
    print("-" * len(header))
    print(f"{'TOTAL':<18} {'':<12} {total_matched:<9} {total_unmatched:<11} {total_low_conf:<9}")

    print(f"\nUnmatched gold rows by task: {{t: len(v) for t,v in unmatched_gold_by_task.items()}}"
          .replace("{t: len(v) for t,v in unmatched_gold_by_task.items()}",
                   str({t: len(v) for t, v in unmatched_gold_by_task.items()})))
    print(f"Organisational errors (right person, wrong hospital): {len(organisational_errors)}")
    print(f"Matched-output files written to {MATCHED_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", action="store_true")
    parser.add_argument("--resolve", action="store_true")
    args = parser.parse_args()
    if not args.candidates and not args.resolve:
        parser.print_help()
        sys.exit(1)
    if args.candidates:
        generate_candidates()
    if args.resolve:
        resolve()
