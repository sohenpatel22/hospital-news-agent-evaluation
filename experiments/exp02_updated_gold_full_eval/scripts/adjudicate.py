"""
Stage 3 — adjudication of unmatched system items.

Every extracted item with no gold match (matched_gold_item_id is null in
/output/matched/) is classified into exactly one bucket:
  A gold gap        | verifiably correct, absent from gold        | no penalty
  B hallucination    | person/event fabricated or doesn't exist    | hallucination rate
  C wrong attribution| real person, wrong hospital/role/entity     | precision + taxonomy
  D out of window     | real+correct but outside eval window       | excluded both ways
  E out of scope      | real, but excluded by the scope rule        | excluded both ways

Two of these buckets are MECHANICAL and decided by this script alone:
  - D (out of window): pure date-range check against the item's own
    date_normalised. No judgment call.
  - E (out of scope): keyword/phrase match against the scope rule's IN/OUT
    role categories, applied to the item's own role/person_or_issue/
    verbatim_snippet text. This is a text-matching judgment call, not a
    factual-verification one, so it's made directly (no web lookup needed).
  - C (wrong attribution): items Stage 2 already identified as
    "right person, wrong hospital" (organisational_errors.json) are C by
    construction. (Currently 0 — Stage 2 review found none survived as
    genuine right-person/wrong-hospital cases; the fuzzy-name candidates
    that looked like it turned out to be different people.)

The remaining items (in window, in scope, not a known org error) require an
A-vs-B call: is this a real fact missing from gold, or a hallucination?
Per EVALUATION_PLAN.md 1.5: "Do NOT let the judge browse the web — it will
hallucinate confirmation." This script (and the Claude pass that fills in
its `bucket_reasoning` step) therefore does NOT attempt to verify claims
against outside sources. It records a PROVISIONAL bucket (A or B) based only
on internal textual signals (citation present/absent, specificity, internal
consistency) plus a confidence score and a description of what evidence
would confirm it — then unconditionally routes every one of these to
needs_human_check.csv. The provisional bucket is a starting point for the
human reviewer, not a final call.

Usage:
  python adjudicate.py --classify   run the window/scope/org-error pass,
                                     write /output/adjudicated/_pending_ab.json
                                     for the A-vs-B items that still need
                                     Claude's provisional read (filled in a
                                     separate pass, see fill_ab_judgment.py),
                                     and write bucket assignments for every
                                     D/E/C item straight away.
  python adjudicate.py --finalize   after _pending_ab.json has bucket_a_or_b /
                                     confidence / evidence_needed filled in
                                     for every entry, merge everything into
                                     /output/adjudicated/<file>.json (one per
                                     extracted-file stem), print the bucket
                                     distribution table, and write
                                     /output/adjudicated/needs_human_check.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /eval
EXTRACTED_DIR = os.path.join(ROOT, "output", "extracted")
MATCHED_DIR = os.path.join(ROOT, "output", "matched")
ADJUDICATED_DIR = os.path.join(ROOT, "output", "adjudicated")
PENDING_AB_PATH = os.path.join(ADJUDICATED_DIR, "_pending_ab.json")
ORG_ERRORS_PATH = os.path.join(MATCHED_DIR, "organisational_errors.json")

WINDOWS = {
    "ceo": (date(2021, 7, 16), date(2026, 7, 16)),
    "supervisor": (date(2021, 7, 16), date(2026, 7, 16)),
    "phipa": (date(2026, 1, 16), date(2026, 7, 16)),
}

# Scope rule (EVALUATION_PLAN.md 1.5 / STAGE 3 instructions)
OUT_OF_SCOPE_PATTERNS = [
    (r"foundation\s+(president\s*/?\s*)?ceo\b", "Foundation CEO / President-CEO — explicitly OUT of scope"),
    (r"foundation\s+president\s+and\s+ceo", "Foundation CEO / President-CEO — explicitly OUT of scope"),
    (r"\bcommunity\s+member\b", "Non-voting community member — explicitly OUT of scope"),
    (r"\bnon[- ]voting\b", "Non-voting member — explicitly OUT of scope"),
    (r"\btrainee\b|\bresident\b(?!.*director)|\bstudent\b|\bintern\b", "Trainee/administrative staff — explicitly OUT of scope"),
    (r"\bexecutive\s+assistant\b|\badministrative\s+(assistant|staff|coordinator)\b", "Administrative staff — explicitly OUT of scope"),
    (r"\bcommittee\s+member\b(?!.*board)", "Committee-only member without a stated board seat — explicitly OUT of scope"),
]

IN_SCOPE_PATTERNS = [
    r"\bboard\s+(of\s+)?(chair|directors?|governors?|trustees?|vice[\s-]?chairs?)\b",
    r"\bfoundation\s+chair\b",
    r"\bfoundation\s+officer\b",
    r"\bvp\b|\bvice\s+president\b",
    r"\bchief\b",  # Chief of Staff, Chief Nursing Executive, CFO, CHRO, etc.
    r"\bpresident\s*/?\s*ceo\b",
    r"\bceo\b",
    r"\bcfo\b|\bcoo\b|\bchro\b|\bcmo\b",
]


def load_extracted():
    """Return dict: source_extracted_file -> list of items (with item_index)."""
    out = {}
    for fname in sorted(os.listdir(EXTRACTED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        with open(os.path.join(EXTRACTED_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        out[fname] = {it["item_index"]: it for it in data["items"]}
    return out


def load_matched():
    """Return dict: source_extracted_file -> list of match rows."""
    out = {}
    for fname in sorted(os.listdir(MATCHED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_") or fname in (
            "unmatched_gold.json",
            "organisational_errors.json",
        ):
            continue
        with open(os.path.join(MATCHED_DIR, fname), encoding="utf-8") as f:
            out[fname] = json.load(f)
    return out


def parse_date_bounds(date_normalised):
    """Return (earliest_possible_date, latest_possible_date) for a
    date_normalised value of unknown precision, or None if absent/unparseable."""
    if not date_normalised:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_normalised)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return (d, d)
    m = re.match(r"^(\d{4})-(\d{2})$", date_normalised)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        first = date(y, mo, 1)
        last_day = 28
        for d in (31, 30, 29, 28):
            try:
                last = date(y, mo, d)
                last_day = d
                break
            except ValueError:
                continue
        return (first, date(y, mo, last_day))
    m = re.match(r"^(\d{4})$", date_normalised)
    if m:
        y = int(m.group(1))
        return (date(y, 1, 1), date(y, 12, 31))
    return None


def window_check(item, task):
    """Returns (status, reason) where status is 'in', 'out', or 'unknown'."""
    bounds = parse_date_bounds(item.get("date_normalised"))
    win_start, win_end = WINDOWS[task]
    if bounds is None:
        return "unknown", "No parseable date_normalised; window compliance cannot be mechanically verified."
    earliest, latest = bounds
    # If the item's possible date range does not overlap the window at all -> out.
    if latest < win_start or earliest > win_end:
        return "out", (
            f"date_normalised={item.get('date_normalised')} falls entirely outside the "
            f"evaluation window [{win_start.isoformat()}, {win_end.isoformat()}] for task={task}."
        )
    return "in", f"date_normalised={item.get('date_normalised')} falls within [{win_start.isoformat()}, {win_end.isoformat()}]."


def scope_check(item):
    """Returns (status, reason) where status is 'in', 'out', or 'unclear'.

    Deliberately keys ONLY off the structured `role` field, not
    person_or_issue/verbatim_snippet: the snippet is free prose that can
    describe multiple people in one sentence (e.g. "X was welcomed as
    Executive Assistant and it was Y's final board meeting" — Y is not an
    Executive Assistant just because that word appears in Y's snippet). If
    role is missing, scope is 'unclear' and goes to human review rather than
    guessing from prose that may not even be about this item's role."""
    role = (item.get("role") or "").strip().lower()
    if not role:
        return "unclear", "role is null; cannot mechanically apply the scope rule without a structured role field (verbatim_snippet is not used here — it may describe a different person in the same sentence)."

    # IN checked first: a role like "community member, Board of Governors" is
    # an actual elected board seat (IN) even though it also contains the
    # string "community member" — an explicit board/foundation/VP/chief
    # mention should win over an ambiguous descriptor word.
    for pattern in IN_SCOPE_PATTERNS:
        if re.search(pattern, role):
            return "in", f"role matches an IN-scope category (pattern: {pattern})."

    for pattern, reason in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, role):
            return "out", reason

    return "unclear", f"role='{item.get('role')}' does not clearly match any IN or OUT scope category listed in the plan."


def build_org_error_lookup():
    if not os.path.exists(ORG_ERRORS_PATH):
        return {}
    with open(ORG_ERRORS_PATH, encoding="utf-8") as f:
        errors = json.load(f)
    lookup = {}
    for e in errors:
        lookup[e["item_uid"]] = e
    return lookup


def item_uid(item, source_file):
    task = item["task"]
    return f"{task}__{item['system']}__{item['hospital']}__run{item['run_number']}__idx{item['item_index']}"


def classify():
    os.makedirs(ADJUDICATED_DIR, exist_ok=True)
    extracted = load_extracted()
    matched = load_matched()
    org_errors = build_org_error_lookup()

    resolved = []  # {source_file, item_index, bucket, reason, confidence}
    pending_ab = []  # items needing Claude's A-vs-B provisional read

    for fname, rows in matched.items():
        items_by_idx = extracted.get(fname, {})
        for row in rows:
            idx = row["item_index"]
            if row["matched_gold_item_id"] is not None:
                continue  # matched -> not adjudicated, handled by Stage 4 scoring
            item = items_by_idx.get(idx)
            if item is None:
                continue
            uid = item_uid(item, fname)
            task = item["task"]

            if uid in org_errors:
                resolved.append(
                    {
                        "source_file": fname,
                        "item_index": idx,
                        "bucket": "C",
                        "reason": "Right person, wrong hospital (Stage 2 organisational_errors.json): "
                        + (org_errors[uid].get("reason") or ""),
                        "confidence": 0.9,
                    }
                )
                continue

            win_status, win_reason = window_check(item, task)
            if win_status == "out":
                resolved.append(
                    {"source_file": fname, "item_index": idx, "bucket": "D", "reason": win_reason, "confidence": 1.0}
                )
                continue

            scope_status, scope_reason = scope_check(item)
            if scope_status == "out":
                resolved.append(
                    {"source_file": fname, "item_index": idx, "bucket": "E", "reason": scope_reason, "confidence": 0.8}
                )
                continue

            # In window (or window unknown) and in-scope (or unclear scope):
            # needs an A-vs-B human-verified call.
            note = win_reason if win_status == "unknown" else ""
            if scope_status == "unclear":
                note = (note + " " if note else "") + scope_reason
            pending_ab.append(
                {
                    "item_uid": uid,
                    "source_file": fname,
                    "item_index": idx,
                    "item": item,
                    "window_status": win_status,
                    "scope_status": scope_status,
                    "note": note,
                    # to be filled by Claude's judgment pass:
                    "provisional_bucket": None,  # "A" or "B"
                    "confidence": None,  # 0-1
                    "evidence_needed": None,  # what would confirm A vs B
                    "reasoning": None,  # one-line rationale for the provisional call
                }
            )

    with open(os.path.join(ADJUDICATED_DIR, "_resolved_mechanical.json"), "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2)
    with open(PENDING_AB_PATH, "w", encoding="utf-8") as f:
        json.dump(pending_ab, f, indent=2)

    print(f"Unmatched items processed: {sum(len(v) for v in matched.values()) - sum(1 for fname, rows in matched.items() for row in rows if row['matched_gold_item_id'] is not None)}")
    from collections import Counter

    bucket_counts = Counter(r["bucket"] for r in resolved)
    print(f"Resolved mechanically: {len(resolved)} -> {dict(bucket_counts)}")
    print(f"Pending A-vs-B judgment (needs Claude's provisional read, then human check): {len(pending_ab)}")
    print(f"\nWritten: {os.path.join(ADJUDICATED_DIR, '_resolved_mechanical.json')}")
    print(f"Written: {PENDING_AB_PATH}")
    print("\nNext: fill provisional_bucket/confidence/evidence_needed/reasoning for every")
    print("entry in _pending_ab.json (Claude does this directly, no web browsing), then")
    print("run adjudicate.py --finalize")


def finalize():
    if not os.path.exists(PENDING_AB_PATH):
        print("Run --classify first.")
        sys.exit(1)
    with open(os.path.join(ADJUDICATED_DIR, "_resolved_mechanical.json"), encoding="utf-8") as f:
        resolved = json.load(f)
    with open(PENDING_AB_PATH, encoding="utf-8") as f:
        pending_ab = json.load(f)

    unfilled = [p for p in pending_ab if p["provisional_bucket"] is None]
    if unfilled:
        print(f"WARNING: {len(unfilled)} pending A-vs-B entries have no provisional_bucket yet.")

    all_rows = []
    for r in resolved:
        all_rows.append(
            {
                "source_file": r["source_file"],
                "item_index": r["item_index"],
                "bucket": r["bucket"],
                "reason": r["reason"],
                "confidence": r["confidence"],
                "needs_human_check": False,
                "evidence_needed": None,
            }
        )
    for p in pending_ab:
        all_rows.append(
            {
                "source_file": p["source_file"],
                "item_index": p["item_index"],
                "bucket": p["provisional_bucket"],
                "reason": p["reasoning"],
                "confidence": p["confidence"],
                "needs_human_check": True,
                "evidence_needed": p["evidence_needed"],
            }
        )

    by_file = {}
    for row in all_rows:
        by_file.setdefault(row["source_file"], []).append(row)

    for fname, rows in by_file.items():
        out_path = os.path.join(ADJUDICATED_DIR, fname)
        payload = [
            {
                "item_index": r["item_index"],
                "bucket": r["bucket"],
                "reason": r["reason"],
                "confidence": r["confidence"],
                "needs_human_check": r["needs_human_check"],
            }
            for r in rows
        ]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    # needs_human_check.csv
    extracted = load_extracted()
    csv_path = os.path.join(ADJUDICATED_DIR, "needs_human_check.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "source_file",
                "item_index",
                "system",
                "task",
                "hospital",
                "run_number",
                "person_or_issue",
                "role",
                "date_normalised",
                "citation_url",
                "provisional_bucket",
                "confidence",
                "evidence_needed",
                "reasoning",
                "human_decision",  # BLANK for manual fill: A / B / C / D / E
                "human_notes",
            ]
        )
        for p in pending_ab:
            item = extracted[p["source_file"]][p["item_index"]]
            writer.writerow(
                [
                    p["source_file"],
                    p["item_index"],
                    item["system"],
                    item["task"],
                    item["hospital"],
                    item["run_number"],
                    item["person_or_issue"],
                    item.get("role") or "",
                    item.get("date_normalised") or "",
                    item.get("citation_url") or "",
                    p["provisional_bucket"],
                    p["confidence"],
                    p["evidence_needed"],
                    p["reasoning"],
                    "",
                    "",
                ]
            )

    print(f"Adjudicated output written to {ADJUDICATED_DIR} ({len(by_file)} files)")
    print(f"needs_human_check.csv written: {csv_path} ({len(pending_ab)} rows)")

    print("\n=== bucket distribution per system per task ===")
    from collections import Counter

    agg = Counter()
    for row in all_rows:
        item = extracted[row["source_file"]][row["item_index"]]
        agg[(item["system"], item["task"], row["bucket"])] += 1

    systems_tasks = sorted(set((k[0], k[1]) for k in agg))
    header = f"{'system':<18} {'task':<12} {'A':<5} {'B':<5} {'C':<5} {'D':<5} {'E':<5}"
    print(header)
    print("-" * len(header))
    for system, task in systems_tasks:
        row = [agg.get((system, task, b), 0) for b in "ABCDE"]
        print(f"{system:<18} {task:<12} " + " ".join(f"{v:<5}" for v in row))
    print("-" * len(header))
    totals = [sum(agg.get((s, t, b), 0) for s, t in systems_tasks) for b in "ABCDE"]
    print(f"{'TOTAL':<18} {'':<12} " + " ".join(f"{v:<5}" for v in totals))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if not args.classify and not args.finalize:
        parser.print_help()
        sys.exit(1)
    if args.classify:
        classify()
    if args.finalize:
        finalize()
