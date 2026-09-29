"""
One-time repair for the Stage 2 multi-event matching bug found during Stage 5
judge validation: when a person has MULTIPLE gold rows at the same
hospital/task (multiple career events -- e.g. Bert Clark has an incoming AND
an outgoing Board Chair row), the original matcher's "exact name match, same
hospital -> auto-accept" rule picked whichever gold row it found first,
without checking which event the item actually describes. Confirmed wrong in
4/70 sampled cases (Bert Clark, Jack Mintz, Stephanie Zee, Altaf Stationwala).

This script does NOT rerun match.py's candidate generation from scratch
(that would discard all the manual/LLM-confirmed decisions made across
Stages 2-5). Instead it:

  1. Groups gold rows into "families" -- same task + hospital + overlapping
     name variant -- wherever a family has more than one row (i.e. the
     person appears in gold for more than one event).
  2. For every currently-matched extracted item whose matched_gold_item_id
     belongs to a >1-member family, scores each family member against the
     item's own date_normalised and direction, and re-picks the best-fitting
     member.
  3. Patches /output/matched/*.json in place ONLY where the recomputed best
     match differs from the current one AND has a strictly better fit score
     (never flips on a tie -- a tie means there was nothing in the item text
     to disambiguate on, so the original pick stands).
  4. Regenerates /output/matched/unmatched_gold.json from the patched state.

Run with --apply to write changes; without it, prints a dry-run report only.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match import load_gold, split_gold_name_or_issue  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATCHED_DIR = os.path.join(ROOT, "output", "matched")
EXTRACTED_DIR = os.path.join(ROOT, "output", "extracted")


def parse_gold_direction(role_detail):
    if not role_detail:
        return None
    t = role_detail.lower()
    if "incoming" in t:
        return "incoming"
    if "outgoing" in t:
        return "outgoing"
    return None


def date_diff_days(a, b):
    """a, b are strings of precision YYYY-MM-DD / YYYY-MM / YYYY. Returns
    None if either is missing or unparseable, else an approximate day gap
    computed at whatever shared precision is available (month/year treated
    as their first day for the purpose of a rough distance metric)."""
    def to_tuple(s):
        if not s:
            return None
        s = str(s)[:10]
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.match(r"^(\d{4})-(\d{2})$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), 15)
        m = re.match(r"^(\d{4})$", s)
        if m:
            return (int(m.group(1)), 7, 1)
        return None

    ta, tb = to_tuple(a), to_tuple(b)
    if ta is None or tb is None:
        return None
    import datetime
    try:
        da = datetime.date(*ta)
        db = datetime.date(*tb)
    except ValueError:
        return None
    return abs((da - db).days)


def build_gold_families(gold_items):
    """Return dict: gold_item_id -> list of gold_item_ids sharing the same
    task+hospital+overlapping-name-variant (the "family"), including itself."""
    by_task_hospital = defaultdict(list)
    for g in gold_items:
        by_task_hospital[(g["task"], g["hospital"])].append(g)

    families = {}
    for (_task, _hosp), group in by_task_hospital.items():
        n = len(group)
        used = [False] * n
        for i in range(n):
            if used[i]:
                continue
            cluster = [group[i]]
            used[i] = True
            for j in range(i + 1, n):
                if used[j]:
                    continue
                if set(group[i]["name_variants"]) & set(group[j]["name_variants"]):
                    cluster.append(group[j])
                    used[j] = True
            ids = [g["gold_item_id"] for g in cluster]
            for g in cluster:
                families[g["gold_item_id"]] = ids
    return families


def score_fit(item, gold_row):
    score = 0
    core_name, role_detail = split_gold_name_or_issue(gold_row["name_or_issue"])
    gdir = parse_gold_direction(role_detail)
    idir = item.get("direction")
    if gdir is not None and idir in ("incoming", "outgoing"):
        score += 3 if gdir == idir else -3

    dd = date_diff_days(item.get("date_normalised"), gold_row.get("date"))
    if dd is not None:
        if dd == 0:
            score += 3
        else:
            score -= min(dd / 180.0, 3.0)  # up to -3 for a ~1.5yr+ gap
    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes; default is dry-run")
    args = parser.parse_args()

    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    families = build_gold_families(gold_items)

    extracted = {}
    for fname in os.listdir(EXTRACTED_DIR):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        data = json.load(open(os.path.join(EXTRACTED_DIR, fname), encoding="utf-8"))
        extracted[fname] = {it["item_index"]: it for it in data["items"]}

    changes = []
    files_touched = 0

    for fname in sorted(os.listdir(MATCHED_DIR)):
        if not fname.endswith(".json") or fname.startswith("_") or fname in (
            "unmatched_gold.json", "organisational_errors.json",
        ):
            continue
        path = os.path.join(MATCHED_DIR, fname)
        rows = json.load(open(path, encoding="utf-8"))
        items_by_idx = extracted.get(fname, {})
        file_changed = False

        for row in rows:
            gid = row.get("matched_gold_item_id")
            if not gid or gid not in families:
                continue
            family = families[gid]
            if len(family) <= 1:
                continue
            item = items_by_idx.get(row["item_index"])
            if item is None:
                continue

            scored = [(fam_gid, score_fit(item, gold_by_id[fam_gid])) for fam_gid in family]
            scored.sort(key=lambda x: -x[1])
            best_gid, best_score = scored[0]
            current_score = dict(scored)[gid]

            if best_gid != gid and best_score > current_score:
                changes.append(
                    {
                        "file": fname,
                        "item_index": row["item_index"],
                        "person_or_issue": item.get("person_or_issue"),
                        "item_date": item.get("date_normalised"),
                        "item_direction": item.get("direction"),
                        "old_gold_id": gid,
                        "old_gold_name": gold_by_id[gid]["name_or_issue"],
                        "old_gold_date": gold_by_id[gid]["date"],
                        "new_gold_id": best_gid,
                        "new_gold_name": gold_by_id[best_gid]["name_or_issue"],
                        "new_gold_date": gold_by_id[best_gid]["date"],
                        "old_score": current_score,
                        "new_score": best_score,
                    }
                )
                if args.apply:
                    row["matched_gold_item_id"] = best_gid
                    row["match_confidence"] = "medium"
                    row["match_reason"] = (
                        f"AUTO-REPAIRED 2026-08-31 (multi-event matching bug fix): re-pointed from "
                        f"{gid} ({gold_by_id[gid]['name_or_issue']!r}, {gold_by_id[gid]['date']}) to "
                        f"{best_gid} ({gold_by_id[best_gid]['name_or_issue']!r}, {gold_by_id[best_gid]['date']}) "
                        f"based on the item's own date_normalised={item.get('date_normalised')!r} and "
                        f"direction={item.get('direction')!r} fitting the new gold row's event better "
                        f"(fit score {best_score:.2f} vs {current_score:.2f}). Original match was 'exact "
                        f"name, same hospital' with no event-level disambiguation among this person's "
                        f"{len(family)} gold rows."
                    )
                    file_changed = True

        if file_changed:
            files_touched += 1
            json.dump(rows, open(path, "w", encoding="utf-8"), indent=2)

    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: {len(changes)} match(es) would be repointed across {len(set(c['file'] for c in changes))} file(s)")
    for c in changes:
        print(
            f"  {c['file']} idx{c['item_index']} '{c['person_or_issue']}' "
            f"(item date={c['item_date']}, dir={c['item_direction']}): "
            f"{c['old_gold_id']} ({c['old_gold_date']}, score {c['old_score']:.2f}) -> "
            f"{c['new_gold_id']} ({c['new_gold_date']}, score {c['new_score']:.2f})"
        )

    if args.apply:
        # regenerate unmatched_gold.json from the patched state
        matched_gold_ids = set()
        for fname in os.listdir(MATCHED_DIR):
            if not fname.endswith(".json") or fname.startswith("_") or fname in (
                "unmatched_gold.json", "organisational_errors.json",
            ):
                continue
            for row in json.load(open(os.path.join(MATCHED_DIR, fname), encoding="utf-8")):
                if row.get("matched_gold_item_id"):
                    matched_gold_ids.add(row["matched_gold_item_id"])

        unmatched_by_task = defaultdict(list)
        for g in gold_items:
            if g["gold_item_id"] not in matched_gold_ids:
                unmatched_by_task[g["task"]].append(g)
        json.dump(unmatched_by_task, open(os.path.join(MATCHED_DIR, "unmatched_gold.json"), "w", encoding="utf-8"), indent=2)
        print(f"\nRegenerated unmatched_gold.json: {[(t, len(v)) for t, v in unmatched_by_task.items()]}")
    else:
        print("\nRun again with --apply to write these changes.")


if __name__ == "__main__":
    main()
