# Results Summary

Generated from `/output/scores/metrics.json`. All cross-system figures use MS Copilot Agent's Run 1 only, matching every other system's single-run basis (see EVALUATION_PLAN.md 1.6). Recall/precision/hallucination CIs are bootstrap 95% (1000 resamples, [low, high] in percentage points). **CIs overlapping between two systems means this dataset cannot distinguish them on that metric -- read comparisons accordingly.**

**Methodology note (2026-08-31):** a Stage 2 matching bug was found and patched after Stage 5 judge validation surfaced it: when a person had more than one gold row at the same hospital/task (multiple career events -- e.g. a Board Chair's incoming AND outgoing rows), the original matcher auto-accepted whichever row it found first on an exact name match, without checking which event the item actually described. `repair_multi_event_matches.py` re-scored every matched item against its own date/direction and repointed 161 matches across 26 files where a better-fitting gold row existed for the same person. This raised recall for every system (previously-unmatched gold rows for a person's other events are now correctly matched) and substantially improved date/role field accuracy (many 'wrong date' errors were a matching artifact, not a model error). All numbers below are post-patch. **Caveat:** the repair's fit score used the item's own date AND direction as the two disambiguating signals, so post-patch Direction field accuracy (Figure 6) is now partly circular for items where direction was the deciding factor in a repointed match -- it is no longer a fully independent check of the model's stated direction for those items. Role accuracy is unaffected (role was never part of the repair's fit score). Date accuracy is only partly affected -- the repair often had an exact-date tie available and used direction only as a secondary signal, but some repointed dates were chosen precisely because they matched, so treat the date-accuracy improvement as an upper bound on the true effect of fixing the bug, not a clean before/after of unrelated model behaviour.

## 1. Tidy results table: system x task x metric

| System | Task | Recall (95% CI) | Precision (95% CI) | Hallucination rate (95% CI) | Specificity (mean 0-3) | Omission rate |
|---|---|---|---|---|---|---|
| ChatGPT | ceo | 26% [21, 31] (n=243) | 100% [100, 100] (n=67) | 0% [0, 0] (n=68) | 2.73 (n=67) | 100% (n=67) |
| ChatGPT | phipa | 33% [0, 100] (n=3) | 33% [0, 100] (n=3) | 50% [0, 100] (n=4) | 2.00 (n=1) | 100% (n=1) |
| ChatGPT | supervisor | 100% [100, 100] (n=4) | 100% [100, 100] (n=6) | 0% [0, 0] (n=6) | 3.00 (n=6) | 100% (n=6) |
| Claude | ceo | 18% [13, 23] (n=243) | 100% [100, 100] (n=48) | 0% [0, 0] (n=49) | 2.79 (n=48) | 10% (n=48) |
| Claude | phipa | 0% [0, 0] (n=3) | -- (n=0) | -- (n=0) | -- (n=0) | -- (n=0) |
| Claude | supervisor | 100% [100, 100] (n=4) | 100% [100, 100] (n=5) | 0% [0, 0] (n=6) | 2.80 (n=5) | 0% (n=5) |
| Gemini | ceo | 13% [9, 17] (n=243) | 100% [100, 100] (n=31) | 0% [0, 0] (n=34) | 2.61 (n=31) | 100% (n=31) |
| Gemini | phipa | 33% [0, 100] (n=3) | 100% [100, 100] (n=1) | 0% [0, 0] (n=1) | 2.00 (n=1) | 100% (n=1) |
| Gemini | supervisor | 100% [100, 100] (n=4) | 100% [100, 100] (n=5) | 0% [0, 0] (n=5) | 2.80 (n=5) | 100% (n=5) |
| MS Copilot Agent | ceo | 26% [21, 32] (n=243) | 100% [100, 100] (n=64) | 0% [0, 0] (n=66) | 2.89 (n=64) | 100% (n=64) |
| MS Copilot Agent | phipa | 100% [100, 100] (n=3) | 100% [100, 100] (n=3) | 0% [0, 0] (n=3) | 2.00 (n=3) | 100% (n=3) |
| MS Copilot Agent | supervisor | 100% [100, 100] (n=4) | 100% [100, 100] (n=6) | 0% [0, 0] (n=6) | 3.00 (n=6) | 100% (n=6) |
| Perplexity | ceo | 23% [18, 28] (n=243) | 100% [100, 100] (n=56) | 0% [0, 0] (n=59) | 2.95 (n=56) | 41% (n=56) |
| Perplexity | phipa | 0% [0, 0] (n=3) | -- (n=0) | -- (n=0) | -- (n=0) | -- (n=0) |
| Perplexity | supervisor | 100% [100, 100] (n=4) | 100% [100, 100] (n=4) | 0% [0, 0] (n=4) | 2.50 (n=4) | 50% (n=4) |

CEO recall by confidence tier and the independent-provenance-subset recall are in Figures 1 and 3 respectively (`/output/figures/`), not repeated here to keep this table readable; see `metrics.csv` for the full tidy long-format export.

### Where CIs overlap (CEO recall) — no defensible ranking claim

Of 10 system pairs on CEO-task recall, **7 have overlapping 95% CIs** (cannot be distinguished) and **3 do not overlap**.

Pairs whose CIs do NOT overlap (a defensible directional claim, at this sample size):
- ChatGPT (26% [21, 31]) recall is higher than Gemini (13% [9, 17])
- MS Copilot Agent (26% [21, 32]) recall is higher than Gemini (13% [9, 17])
- Perplexity (23% [18, 28]) recall is higher than Gemini (13% [9, 17])

## 2. Largest gold gaps (bucket A) per system

**As of this evaluation round, bucket A (unresolved gold gap) is EMPTY (0 items) system-wide.** Every item that was provisionally flagged bucket A during Stage 3/4 adjudication was resolved by the end of this round -- either web-verified and added to gold as a new row (Dr. Christine Schriver / Dr. Florin Padeanu's 2022 Chief of Staff transition at Arnprior; Dr. Eyal Golan's 2022 Professional Staff Association presidency at Mackenzie; Dr. Kevin Wasko and Dr. Maral Nadjafi's NYGH Chief appointments; Simone Atungo's board-appointment date), or reclassified after verification (Brenda Donnelly -> bucket B hallucination; two ChatGPT PHIPA items -> bucket B, mischaracterized policy documents). This is reported here as the finding for this section, in place of a top-5 list that would otherwise be empty:

| Gold row added | Hospital | Date | Found via | Confidence tier |
|---|---|---|---|---|
| Dr. Florin Padeanu - Chief of Staff (incoming) | Arnprior Regional Health | 2022-01-01 | Systems under test, web-verified 2026-08-31 | A - dated announcement |
| Dr. Christine Schriver - Chief of Staff (outgoing) | Arnprior Regional Health | 2022-01-01 | Systems under test, web-verified 2026-08-31 | A - dated announcement |
| Dr. Eyal Golan - President, Professional Staff Association (incoming, ex-officio board seat) | Mackenzie Health | 2022-01-19 | Systems under test, web-verified 2026-08-31 | A - dated announcement |
| Dr. Kevin Wasko - Chief of Emergency Medicine and Program Medical Director (incoming) | North York General Hospital | 2023-05-01 | Systems under test, web-verified 2026-08-31 | C - inferred / approximate date |
| Dr. Maral Nadjafi - Chief of Medicine and Program Medical Director (incoming) | North York General Hospital | 2022 | Systems under test, web-verified 2026-08-31 | C - inferred / approximate date |
| Simone Atungo (C76, date added) | North York General Hospital | 2026-06-26 | Systems under test, web-verified 2026-08-31 | A - dated announcement (was Tier B, undated) |

**Note for the preprint:** this means the systems under test, collectively, surfaced real facts missing from (or under-specified in) the gold set during this evaluation round. This is expected and healthy for an iteratively-built gold set, but it also means recall numbers reported before this round's gold additions were understated for these specific items, and it reinforces why Figure 3 (independent-subset recall) matters: some of every system's 'overall' recall credit now traces back to gold rows the systems themselves helped surface.

## 3. Ten most common specific errors across all systems

Ranked by measured instance count (not extrapolated). Categories 1-3 are large aggregate counts from the field-accuracy/omission pipeline; categories 4-10 are specific, named error patterns identified during matching/adjudication review, counted exactly (not sampled) except where noted.

| # | Error pattern | Count | Note |
|---|---|---|---|
| 1 | No citation URL provided on a matched item | 214 | Out of 297 matched items; near-universal for ChatGPT/Gemini/MS Copilot Agent (they name a source but rarely link it) -- this is why citation validity could not be scored this round (1.4 addendum). |
| 2 | Wrong role/title on an otherwise-correctly-matched item | 189 | e.g. 'Chair' reported where gold specifies 'Board Chair' / 'Second Vice Chair'; combined titles truncated to one component. |
| 3 | Wrong date on an otherwise-correctly-matched item | 119 | Includes cases matched to the right event with the wrong specific date, after tolerances (1.3) are applied. |
| 4 | Month/year-only date given where a day-level date was determinable | 42 | Counted against specificity (1.4a), not field accuracy directly (date-tolerance rules in 1.3 still accept month/year precision as correct when gold itself is only that precise) -- but it is the single largest driver of specificity scores below 3 (Figure 5). |
| 5 | Non-voting 'community member' reported as/alongside a voting board seat | 7 | Same real person/event (NYGH 2022 AGM) repeated across systems and runs; correctly excluded (bucket E) each time, but a recurring pattern worth naming. |
| 6 | Foundation entity conflated with / reported alongside hospital entity | 6 | Nicole McCahon, Terry Pursell, Seanna Millar -- real people, real Foundation-CEO roles, correctly excluded from precision as out-of-scope matches, but a recurring confusion pattern for the models. |
| 7 | Committee-only appointment reported without noting it lacks a board seat | 4 | Quality Committee membership described in board-appointment language; correctly excluded (bucket E). |
| 8 | PHIPA-adjacent policy/administrative document mischaracterized as an adjudicated PHIPA decision | 2 | ChatGPT presented a MyChart Terms revision and a Directory-of-Records publication as 'PHIPA events'; reclassified to bucket B (penalized) per author instruction. |
| 9 | Investigator (s.8) role conflated with Supervisor (s.9) role | 1 | Janice Skot is a Ministry-appointed investigator, not a supervisor -- Claude reported her as a supervisor-task match; correctly excluded from precision. |
| 10 | Complete fabrication with no corroborating source anywhere | 1 | Brenda Donnelly (MS Copilot Agent, ARH, Run 4) -- author-verified against ARH's own records and general search; no trace found. The only item in this evaluation classified bucket B on fabrication grounds rather than mischaracterization. |

## 4. Limitations

- **n = 3 hospitals per task.** Every confidence interval in this report is correspondingly wide (see the CI columns in section 1) -- treat point-estimate differences as directional, not conclusive, and lean on the error taxonomy (section 3) for the qualitative argument rather than ranking systems by a single point estimate.
- **Repeat runs on one system only.** MS Copilot Agent has 5 runs per hospital/task; every other system has 1. All cross-system metrics in this report (including this file) use Copilot's Run 1 only, matching every other system's single-run basis. Runs 2-5 feed only the single-system consistency analysis (Figure 7) and must never be read as giving Copilot more 'chances' in any cross-system number here.
- **Gold-set provenance circularity, and how it was controlled.** A large share of the gold set (146 of 248 current CEO rows) has status `NEWLY ADDED - please verify`, meaning it was added to gold after initial collection -- in some cases because a system under test surfaced the fact, which was then human-verified against a primary source. To control for this, every recall number is also reported on the `independent` provenance subset (Figure 3), and every system's independent-subset recall is lower than its overall recall, consistent with real (if partial) circularity. This round added 5 more gold rows for exactly this reason (section 2) -- disclose that gold-set growth is ongoing and partly system-prompted, not a one-time snapshot.
- **LLM-judge error, and the measured kappa.** Stage 5 drew a stratified 70-item sample of matching/adjudication decisions and re-adjudicated all 70 by hand (`/output/adjudicated/judge_validation_sample_adjudicated.csv`), finding 4 disagreements (~5.7%) -- all from the same root cause, the multi-event matching bug described in the methodology note above, which has since been patched (the disagreement count here predates the patch and is not re-verified against the corrected matches). **Cohen's kappa has NOT been computed** (deferred per instruction pending a genuinely independent second reviewer) -- the 70-row file's `human_decision` column was filled in by the same system that produced `judge_decision`, so a kappa computed from it today would measure self-review consistency, not independent human agreement, and must not be reported as inter-rater reliability in the preprint without an actual second, independent reviewer filling in a fresh copy of that column first. Buckets A, C, and D currently have zero items in this dataset and cannot be kappa-scored at all this round.
- **Evaluation-window boundary effects.** Items dated at the exact edge of a window (e.g. Simone Atungo's board appointment, 2026-06-26/07-03, days before the CEO/Supervisor window closes 2026-07-16) are sensitive to both the model's knowledge cutoff and to which of several reported dates for the same event is used -- see the date-tolerance rules (EVALUATION_PLAN.md 1.3). No item in this round's adjudication was excluded solely for falling just outside a window (bucket D = 0 throughout), but that is partly because dated items cluster well inside the windows in this dataset, not evidence that boundary effects don't matter in general.
- **PHIPA's window (6 months: 2026-01-16 to 2026-07-16) is far shorter than CEO/Supervisor's (5 years: 2021-07-16 to 2026-07-16).** PHIPA recall and precision are NOT comparable to CEO/Supervisor numbers on the same axis for this reason alone -- a system with perfect PHIPA recall found at most 3-6 real events in 6 months, a fundamentally smaller and differently-shaped task than finding leadership changes over 5 years. Every table and figure in this report keeps tasks in separate rows/facets rather than pooling them for exactly this reason.
