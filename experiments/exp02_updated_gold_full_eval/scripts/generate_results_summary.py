"""
Stage 7 — results write-up support. Generates /output/RESULTS_SUMMARY.md
from metrics.json plus the raw records (for gold-gap / error listings not
already aggregated into metrics.json).
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match import load_gold, split_gold_name_or_issue  # noqa: E402
from score import SYSTEMS as SYSTEM_ORDER, TASKS, build_records  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_DIR = os.path.join(ROOT, "output", "scores")
OUT_PATH = os.path.join(ROOT, "output", "RESULTS_SUMMARY.md")

with open(os.path.join(SCORES_DIR, "metrics.json"), encoding="utf-8") as f:
    M = json.load(f)


def fmt(v, pct=True):
    if v is None:
        return "--"
    return f"{v*100:.0f}%" if pct else f"{v:.2f}"


def fmt_ci(point, lo, hi):
    if point is None:
        return "--"
    if lo is None or hi is None:
        return f"{point*100:.0f}%"
    return f"{point*100:.0f}% [{lo*100:.0f}, {hi*100:.0f}]"


def main():
    gold_items = load_gold()
    gold_by_id = {g["gold_item_id"]: g for g in gold_items}
    records = build_records(gold_by_id, restrict_copilot_run1=True)

    lines = []
    lines.append("# Results Summary")
    lines.append("")
    lines.append(
        "Generated from `/output/scores/metrics.json`. All cross-system figures use "
        "MS Copilot Agent's Run 1 only, matching every other system's single-run basis "
        "(see EVALUATION_PLAN.md 1.6). Recall/precision/hallucination CIs are bootstrap "
        "95% (1000 resamples, [low, high] in percentage points). **CIs overlapping "
        "between two systems means this dataset cannot distinguish them on that metric "
        "-- read comparisons accordingly.**"
    )
    lines.append("")
    lines.append(
        "**Methodology note (2026-08-31):** a Stage 2 matching bug was found and patched "
        "after Stage 5 judge validation surfaced it: when a person had more than one gold "
        "row at the same hospital/task (multiple career events -- e.g. a Board Chair's "
        "incoming AND outgoing rows), the original matcher auto-accepted whichever row it "
        "found first on an exact name match, without checking which event the item "
        "actually described. `repair_multi_event_matches.py` re-scored every matched item "
        "against its own date/direction and repointed 161 matches across 26 files where a "
        "better-fitting gold row existed for the same person. This raised recall for every "
        "system (previously-unmatched gold rows for a person's other events are now "
        "correctly matched) and substantially improved date/role field accuracy (many "
        "'wrong date' errors were a matching artifact, not a model error). All numbers "
        "below are post-patch. **Caveat:** the repair's fit score used the item's own "
        "date AND direction as the two disambiguating signals, so post-patch Direction "
        "field accuracy (Figure 6) is now partly circular for items where direction was "
        "the deciding factor in a repointed match -- it is no longer a fully independent "
        "check of the model's stated direction for those items. Role accuracy is "
        "unaffected (role was never part of the repair's fit score). Date accuracy is "
        "only partly affected -- the repair often had an exact-date tie available and "
        "used direction only as a secondary signal, but some repointed dates were chosen "
        "precisely because they matched, so treat the date-accuracy improvement as an "
        "upper bound on the true effect of fixing the bug, not a clean before/after of "
        "unrelated model behaviour."
    )
    lines.append("")

    # ------------------------------------------------------------- Section 1
    lines.append("## 1. Tidy results table: system x task x metric")
    lines.append("")
    lines.append(
        "| System | Task | Recall (95% CI) | Precision (95% CI) | Hallucination rate (95% CI) | Specificity (mean 0-3) | Omission rate |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for s in SYSTEM_ORDER:
        for t in TASKS:
            rec = M["systems"][s]["recall"][t]["overall"]
            prec = M["systems"][s]["precision"][t]
            hall = M["systems"][s]["hallucination_rate"][t]
            spec = M["systems"][s]["specificity"][t]
            om = M["systems"][s]["omission_rate"][t]
            lines.append(
                f"| {s} | {t} | {fmt_ci(rec['point'], rec['ci_low'], rec['ci_high'])} "
                f"(n={rec['n_gold']}) | {fmt_ci(prec['point'], prec['ci_low'], prec['ci_high'])} "
                f"(n={prec['n']}) | {fmt_ci(hall['point'], hall['ci_low'], hall['ci_high'])} "
                f"(n={hall['n']}) | {fmt(spec['mean'], pct=False) if spec['mean'] is not None else '--'} "
                f"(n={spec['n']}) | {fmt(om['rate'])} (n={om['n']}) |"
            )
    lines.append("")
    lines.append(
        "CEO recall by confidence tier and the independent-provenance-subset recall are "
        "in Figures 1 and 3 respectively (`/output/figures/`), not repeated here to keep "
        "this table readable; see `metrics.csv` for the full tidy long-format export."
    )
    lines.append("")

    # No-CI-separation note: check pairwise overlaps for CEO recall specifically
    lines.append("### Where CIs overlap (CEO recall) — no defensible ranking claim")
    lines.append("")
    ceo_recalls = {}
    for s in SYSTEM_ORDER:
        d = M["systems"][s]["recall"]["ceo"]["overall"]
        if d["point"] is not None:
            ceo_recalls[s] = (d["point"], d["ci_low"], d["ci_high"])
    overlap_pairs = []
    non_overlap_pairs = []
    syslist = list(ceo_recalls.keys())
    for i in range(len(syslist)):
        for j in range(i + 1, len(syslist)):
            a, b = syslist[i], syslist[j]
            _, lo_a, hi_a = ceo_recalls[a]
            _, lo_b, hi_b = ceo_recalls[b]
            overlaps = not (hi_a < lo_b or hi_b < lo_a)
            (overlap_pairs if overlaps else non_overlap_pairs).append((a, b))
    lines.append(
        f"Of {len(syslist) * (len(syslist)-1)//2} system pairs on CEO-task recall, "
        f"**{len(overlap_pairs)} have overlapping 95% CIs** (cannot be distinguished) and "
        f"**{len(non_overlap_pairs)} do not overlap**."
    )
    lines.append("")
    if non_overlap_pairs:
        lines.append("Pairs whose CIs do NOT overlap (a defensible directional claim, at this sample size):")
        for a, b in non_overlap_pairs:
            pa, la, ha = ceo_recalls[a]
            pb, lb, hb = ceo_recalls[b]
            higher, lower = (a, b) if pa > pb else (b, a)
            lines.append(f"- {higher} ({fmt_ci(*ceo_recalls[higher])}) recall is higher than {lower} ({fmt_ci(*ceo_recalls[lower])})")
    else:
        lines.append("No pair of systems has non-overlapping CEO recall CIs at this sample size -- "
                      "**no system can be defensibly called \"better\" than another on CEO recall from this dataset alone.**")
    lines.append("")

    # ------------------------------------------------------------- Section 2
    lines.append("## 2. Largest gold gaps (bucket A) per system")
    lines.append("")
    lines.append(
        "**As of this evaluation round, bucket A (unresolved gold gap) is EMPTY (0 "
        "items) system-wide.** Every item that was provisionally flagged bucket A during "
        "Stage 3/4 adjudication was resolved by the end of this round -- either "
        "web-verified and added to gold as a new row (Dr. Christine Schriver / Dr. Florin "
        "Padeanu's 2022 Chief of Staff transition at Arnprior; Dr. Eyal Golan's 2022 "
        "Professional Staff Association presidency at Mackenzie; Dr. Kevin Wasko and Dr. "
        "Maral Nadjafi's NYGH Chief appointments; Simone Atungo's board-appointment date), "
        "or reclassified after verification (Brenda Donnelly -> bucket B hallucination; "
        "two ChatGPT PHIPA items -> bucket B, mischaracterized policy documents). This is "
        "reported here as the finding for this section, in place of a top-5 list that "
        "would otherwise be empty:"
    )
    lines.append("")
    lines.append("| Gold row added | Hospital | Date | Found via | Confidence tier |")
    lines.append("|---|---|---|---|---|")
    added_rows = ["C244", "C245", "C246", "C247", "C248"]
    for gid in added_rows:
        g = gold_by_id.get(gid)
        if not g:
            continue
        lines.append(f"| {g['name_or_issue']} | {g['hospital']} | {g['date']} | Systems under test, web-verified 2026-08-31 | {g['confidence_tier']} |")
    lines.append(
        "| Simone Atungo (C76, date added) | North York General Hospital | 2026-06-26 | "
        "Systems under test, web-verified 2026-08-31 | A - dated announcement (was Tier B, undated) |"
    )
    lines.append("")
    lines.append(
        "**Note for the preprint:** this means the systems under test, collectively, "
        "surfaced real facts missing from (or under-specified in) the gold set during "
        "this evaluation round. This is expected and healthy for an iteratively-built "
        "gold set, but it also means recall numbers reported before this round's gold "
        "additions were understated for these specific items, and it reinforces why "
        "Figure 3 (independent-subset recall) matters: some of every system's 'overall' "
        "recall credit now traces back to gold rows the systems themselves helped surface."
    )
    lines.append("")

    # ------------------------------------------------------------- Section 3
    lines.append("## 3. Ten most common specific errors across all systems")
    lines.append("")
    lines.append(
        "Ranked by measured instance count (not extrapolated). Categories 1-3 are large "
        "aggregate counts from the field-accuracy/omission pipeline; categories 4-10 are "
        "specific, named error patterns identified during matching/adjudication review, "
        "counted exactly (not sampled) except where noted."
    )
    lines.append("")

    wrong_role_total = sum(M["systems"][s]["error_taxonomy"][t]["wrong_role"] for s in SYSTEM_ORDER for t in TASKS)
    wrong_date_total = sum(M["systems"][s]["error_taxonomy"][t]["wrong_date"] for s in SYSTEM_ORDER for t in TASKS)
    omitted_total = sum(M["systems"][s]["omission_rate"][t]["omitted"] for s in SYSTEM_ORDER for t in TASKS)
    matched_total = sum(M["systems"][s]["omission_rate"][t]["n"] for s in SYSTEM_ORDER for t in TASKS)

    all_records_full = build_records(gold_by_id, restrict_copilot_run1=False)
    e_records = [r for r in all_records_full if r["bucket"] == "E"]
    e_by_name = Counter(r["item"]["person_or_issue"] for r in e_records)
    oos_records = [r for r in all_records_full if r["bucket"] == "matched_out_of_scope"]
    oos_by_gold = Counter(r["gold_item_id"] for r in oos_records)
    foundation_conflation = sum(n for gid, n in oos_by_gold.items() if gold_by_id[gid]["hospital"] and "Foundation" in gold_by_id[gid]["name_or_issue"])
    investigator_conflation = sum(n for gid, n in oos_by_gold.items() if "Investigator" in gold_by_id[gid]["name_or_issue"])

    error_list = [
        (f"Wrong role/title on an otherwise-correctly-matched item", wrong_role_total,
         "e.g. 'Chair' reported where gold specifies 'Board Chair' / 'Second Vice Chair'; combined titles truncated to one component."),
        (f"Wrong date on an otherwise-correctly-matched item", wrong_date_total,
         "Includes cases matched to the right event with the wrong specific date, after tolerances (1.3) are applied."),
        (f"No citation URL provided on a matched item", omitted_total,
         f"Out of {matched_total} matched items; near-universal for ChatGPT/Gemini/MS Copilot Agent (they name a source but rarely link it) -- this is why citation validity could not be scored this round (1.4 addendum)."),
        (f"Non-voting 'community member' reported as/alongside a voting board seat", e_by_name.get("Divya Khan", 0),
         "Same real person/event (NYGH 2022 AGM) repeated across systems and runs; correctly excluded (bucket E) each time, but a recurring pattern worth naming."),
        (f"Committee-only appointment reported without noting it lacks a board seat", e_by_name.get("Maggie Harbert", 0),
         "Quality Committee membership described in board-appointment language; correctly excluded (bucket E)."),
        (f"Foundation entity conflated with / reported alongside hospital entity", foundation_conflation,
         "Nicole McCahon, Terry Pursell, Seanna Millar -- real people, real Foundation-CEO roles, correctly excluded from precision as out-of-scope matches, but a recurring confusion pattern for the models."),
        (f"Investigator (s.8) role conflated with Supervisor (s.9) role", investigator_conflation,
         "Janice Skot is a Ministry-appointed investigator, not a supervisor -- Claude reported her as a supervisor-task match; correctly excluded from precision."),
        (f"PHIPA-adjacent policy/administrative document mischaracterized as an adjudicated PHIPA decision", 2,
         "ChatGPT presented a MyChart Terms revision and a Directory-of-Records publication as 'PHIPA events'; reclassified to bucket B (penalized) per author instruction."),
        (f"Complete fabrication with no corroborating source anywhere", 1,
         "Brenda Donnelly (MS Copilot Agent, ARH, Run 4) -- author-verified against ARH's own records and general search; no trace found. The only item in this evaluation classified bucket B on fabrication grounds rather than mischaracterization."),
    ]

    import re as _re
    vague_date_count = 0
    for r in records:
        if r["bucket"] == "TP":
            dn = r["item"].get("date_normalised")
            if not dn or not _re.match(r"^\d{4}-\d{2}-\d{2}$", dn):
                vague_date_count += 1
    error_list.append(
        (
            "Month/year-only date given where a day-level date was determinable",
            vague_date_count,
            "Counted against specificity (1.4a), not field accuracy directly (date-tolerance rules in 1.3 still accept month/year precision as correct when gold itself is only that precise) -- but it is the single largest driver of specificity scores below 3 (Figure 5).",
        )
    )
    error_list.sort(key=lambda x: -x[1])
    lines.append("| # | Error pattern | Count | Note |")
    lines.append("|---|---|---|---|")
    for i, (name, count, note) in enumerate(error_list, start=1):
        lines.append(f"| {i} | {name} | {count} | {note} |")
    lines.append("")

    # ------------------------------------------------------------- Section 4
    lines.append("## 4. Limitations")
    lines.append("")
    lines.append(
        "- **n = 3 hospitals per task.** Every confidence interval in this report is "
        "correspondingly wide (see the CI columns in section 1) -- treat point-estimate "
        "differences as directional, not conclusive, and lean on the error taxonomy "
        "(section 3) for the qualitative argument rather than ranking systems by a single "
        "point estimate."
    )
    lines.append(
        "- **Repeat runs on one system only.** MS Copilot Agent has 5 runs per "
        "hospital/task; every other system has 1. All cross-system metrics in this report "
        "(including this file) use Copilot's Run 1 only, matching every other system's "
        "single-run basis. Runs 2-5 feed only the single-system consistency analysis "
        "(Figure 7) and must never be read as giving Copilot more 'chances' in any "
        "cross-system number here."
    )
    ceo_total = sum(1 for g in gold_items if g["task"] == "ceo")
    import pandas as pd
    df_ceo = pd.read_excel(os.path.join(ROOT, "data", "gold.xlsx"), sheet_name="CEOs", header=2)
    df_ceo.dropna(how="all", inplace=True)
    ceo_newly_added = int(df_ceo["status"].astype(str).str.startswith("NEWLY ADDED").sum())
    lines.append(
        f"- **Gold-set provenance circularity, and how it was controlled.** A large share "
        f"of the gold set ({ceo_newly_added} of {ceo_total} current CEO rows) has "
        "status `NEWLY ADDED - please verify`, meaning it was added to gold after initial "
        "collection -- in some cases because a system under test surfaced the fact, which "
        "was then human-verified against a primary source. To control for this, every "
        "recall number is also reported on the `independent` provenance subset (Figure 3), "
        "and every system's independent-subset recall is lower than its overall recall, "
        "consistent with real (if partial) circularity. This round added 5 more gold rows "
        "for exactly this reason (section 2) -- disclose that gold-set growth is ongoing "
        "and partly system-prompted, not a one-time snapshot."
    )
    lines.append(
        "- **LLM-judge error, and the measured kappa.** Stage 5 drew a stratified 70-item "
        "sample of matching/adjudication decisions and re-adjudicated all 70 by hand "
        "(`/output/adjudicated/judge_validation_sample_adjudicated.csv`), finding 4 "
        "disagreements (~5.7%) -- all from the same root cause, the multi-event matching "
        "bug described in the methodology note above, which has since been patched "
        "(the disagreement count here predates the patch and is not re-verified against "
        "the corrected matches). "
        "**Cohen's kappa has NOT been computed** (deferred per instruction pending a "
        "genuinely independent second reviewer) -- the 70-row file's `human_decision` "
        "column was filled in by the same system that produced `judge_decision`, so a "
        "kappa computed from it today would measure self-review consistency, not "
        "independent human agreement, and must not be reported as inter-rater reliability "
        "in the preprint without an actual second, independent reviewer filling in a fresh "
        "copy of that column first. Buckets A, C, and D currently have zero items in this "
        "dataset and cannot be kappa-scored at all this round."
    )
    lines.append(
        "- **Evaluation-window boundary effects.** Items dated at the exact edge of a "
        "window (e.g. Simone Atungo's board appointment, 2026-06-26/07-03, days before "
        "the CEO/Supervisor window closes 2026-07-16) are sensitive to both the model's "
        "knowledge cutoff and to which of several reported dates for the same event is "
        "used -- see the date-tolerance rules (EVALUATION_PLAN.md 1.3). No item in this "
        "round's adjudication was excluded solely for falling just outside a window "
        "(bucket D = 0 throughout), but that is partly because dated items cluster well "
        "inside the windows in this dataset, not evidence that boundary effects don't "
        "matter in general."
    )
    lines.append(
        "- **PHIPA's window (6 months: 2026-01-16 to 2026-07-16) is far shorter than "
        "CEO/Supervisor's (5 years: 2021-07-16 to 2026-07-16).** PHIPA recall and "
        "precision are NOT comparable to CEO/Supervisor numbers on the same axis for this "
        "reason alone -- a system with perfect PHIPA recall found at most 3-6 real events "
        "in 6 months, a fundamentally smaller and differently-shaped task than finding "
        "leadership changes over 5 years. Every table and figure in this report keeps "
        "tasks in separate rows/facets rather than pooling them for exactly this reason."
    )
    lines.append("")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
