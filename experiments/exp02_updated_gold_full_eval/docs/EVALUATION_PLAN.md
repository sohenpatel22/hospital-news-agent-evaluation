# Hospital News Agent Evaluation — Rubric and Claude Code Prompt Sequence

**Systems under test:** Microsoft 365 Copilot (Hospital News Agent), Perplexity, Claude, ChatGPT, Google Gemini
**Tasks:** CEO/leadership changes · PHIPA decisions · Hospital supervisors
**Hospitals:** Mackenzie Health · North York General · Arnprior Regional Health
**Windows:** CEO + Supervisor = 2021-07-16 → 2026-07-16 · PHIPA = 2026-01-16 → 2026-07-16
**Repeat runs:** Copilot only, Runs 1–5 (Test 2). All other systems: Run 1 only.

---

## PART 1 — SCORING RUBRIC

### 1.1 Entity matching (run before any metric)

An item in a system response matches a gold row when **person/issue AND hospital both match**.

**Name matching — accept as match:**
- Case, punctuation, honorifics: `Dr. Joby McKenzie` = `Joby McKenzie`
- Nicknames and parentheticals: `Richard (Rick) Holock` = `Rick Holock` = `Richard Holock`
- Suffix variants: `Paul Truscott` = `Paul Truscott Jr.`
- Documented spelling variants: `Pete Kenney` = `Pete Kenny`; `Mark MacGowan` = `Mark MacGown`
- Minor transpositions/misspellings where the person is unambiguous: `Mary Agnes-Wilson` = `Mary-Agnes Wilson`; `Nicole Cahon` = `Nicole McCahon`; `Atlaf Stationwala` = `Altaf Stationwala`

**Do NOT match:**
- Different people with similar names
- Right person, wrong hospital → counts as an **organisational error**, not a match
- Hospital vs Foundation confusion → **organisational error** (see 1.5)

Use the `hospital_aliases` column for hospital matching.

### 1.2 Field scoring (only for matched entities)

Score each matched entity on four fields:

| Field | Correct when |
|---|---|
| **Role** | Semantically equivalent to gold. Accept documented title variants (see 1.3). Distinct offices must not be conflated — `Vice Chair` ≠ `Second Vice Chair`; `Chief of Staff` ≠ `Chief Pathologist`; `Board Chair` ≠ `Board Director` |
| **Date** | Exact match, OR falls within a documented tolerance (see 1.3), OR gold date is blank/Tier B (then score `N/A`, exclude from denominator) |
| **Direction** | Incoming vs outgoing correctly stated |
| **Citation** | See 1.4 |

### 1.3 Documented tolerances — count BOTH as correct

These are in the gold `notes` column. Any system returning either value is correct.

**Dates:**
- Mitch Frazer: 2024-06-17 (elected) or 2024-06-18 (took office)
- Jennifer Dockery: 2024-08-18 (payroll) or 2024-08-19 (news release)
- Arnprior 2023 cohort — Holock, Kenny, Koba, Stitt-Cavanagh, McGaraughty: 2023-06-22 (AGM) or 2023-07-18 (announcement)
- Any gold date at month precision (`YYYY-MM`): accept any day within that month
- Any gold date at year precision (`YYYY`): accept any date within that year

**Titles (both hospital-published):**
- `Chief Nursing Executive` = `Chief Nurse Executive`
- `VP Medical Affairs, Research and Education` = `VP Medical & Academic Affairs`
- `EVP Clinical Programs & Chief Planning & Redevelopment Officer` = `VP Planning, Redevelopment & Clinical Support`
- `VP People and Culture & CHRO` = `VP Chief Human Resources Officer`

**Supervisor task — date basis (per Wendy's team ruling):**
Use the **commencement** date where any source states it; fall back to the **order** date only when no commencement date is published. Accept either where both exist in sources (e.g. Altaf Stationwala: 2024-06-26 order / 2024-07-08 commencement).

### 1.4 Citation validity — 4-point scale

Citation is a **core requirement**. A system producing no link is penalised, not excluded.

| Score | Meaning |
|---|---|
| 3 | Link resolves AND names the person AND supports the claimed role/date |
| 2 | Link resolves and is topically relevant but does not name the person or support the claim |
| 1 | Link is broken, is a bare domain/homepage, or is fabricated |
| 0 | No link provided |

Report **mean citation score** and **% of items scoring 3**.

**ADDENDUM (2026-08-31) — citation validity NOT computed for this evaluation round.**
The raw LLM/agent responses were not all copied with their citations intact during
data collection (a data-capture gap, not a system-quality signal) — the author
confirmed this is human error on the collection side, not something the systems
under test should be penalised or credited for. Scoring citation validity against
incomplete citation capture would produce a metric that reflects our collection
process, not the systems. **Citation validity is therefore excluded from Stage 4
scoring for this round.** See 1.4a below for the substitute metric used instead,
and disclose this substitution explicitly in the preprint's limitations section —
do not silently drop citation quality from the paper without explaining why.

### 1.4a Specificity — substitute metric for this evaluation round

Because citation validity (1.4) is not computed this round, **specificity** is
scored instead, over every matched entity. It measures how specific/checkable the
system's own claim was, independent of whether a citation was captured for it.

0–3 score per matched item, one point for each of:
1. **Exact date** — `date_normalised` is full `YYYY-MM-DD` precision (not just
   `YYYY-MM` or `YYYY`).
2. **Named, non-generic source** — `citation_text` is a specific, identifiable
   source (a document title, board-minutes date, named outlet, decision/order
   number) rather than null, a bare hospital name with nothing else, or a
   placeholder string like "Source link".
3. **Role stated** — `role` is non-null.

Report **mean specificity score** and **% of items scoring 3**, per system, same
shape as the citation-validity metric it replaces (so Figure 5 in Stage 6 can be
repurposed directly). This is a proxy for how much a reader could verify or act on
the claim as stated — it is not a substitute for citation validity's actual
link-checking, and the preprint must say so.

### 1.5 Adjudication of unmatched system items — MANDATORY

Every returned item with no gold match is adjudicated into exactly one bucket:

| Bucket | Definition | Counts against |
|---|---|---|
| **A. Gold gap** | Verifiably correct against a real source, but absent from gold | Nothing — flag for gold-set update |
| **B. Hallucination** | Person/event does not exist, or is fabricated | Hallucination rate |
| **C. Wrong attribution** | Real person, wrong hospital, wrong role, or wrong entity (Foundation↔hospital) | Precision + error taxonomy |
| **D. Out of window** | Real and correct but outside the evaluation window | Nothing — exclude both ways |
| **E. Out of scope** | Real, but excluded by scope rule (Foundation CEOs, committee-only members, non-voting community members, administrative/trainee staff) | Nothing — exclude both ways |

**Buckets A, D and E do not count as errors.** Precision must be computed after this adjudication or it is not defensible.

### 1.6 Metric definitions — mutually exclusive, no double-reporting

| Metric | Formula / definition |
|---|---|
| **Recall (by tier)** | matched gold items ÷ in-scope gold items, reported separately for Tier A / B / C |
| **Recall (independent subset)** | same, restricted to gold rows NOT originating from any system under test |
| **Precision** | (matched + bucket A) ÷ (all returned items − buckets D and E) |
| **F1** | harmonic mean of precision and recall (secondary — see note) |
| **Hallucination rate** | bucket B items ÷ all returned items |
| **Field accuracy** | per field, correct ÷ matched entities where gold field is populated |
| ~~Citation validity~~ **Specificity** (1.4a) | NOT computed this round (incomplete citation capture, see 1.4 addendum) — mean 0–3 specificity score reported instead; and % scoring 3 |
| **Omission rate** | of matched entities, proportion with a REQUIRED FIELD LEFT BLANK (name, role, date, link). Distinct from recall |
| **Completeness** | did the response cover all 3 hospitals, and both incoming AND outgoing changes? Reported as coverage flags, not a rate |
| **Consistency** (Copilot only) | mean pairwise Jaccard of returned entity sets across Runs 1–5 (10 pairs); plus per-item stability = % of items appearing in all 5 runs |

**Note on F1:** included as requested, but report precision and recall as primary. For a health-system tool a hallucination and a miss carry different costs, and F1 averages them away.

**Note on MS Copilot Agent's runs (2026-08-31):** Copilot is the only system with 5
runs per hospital/task; every other system has Run 1 only. **All cross-system
comparison metrics (recall, precision, field accuracy, specificity, omission,
completeness, error taxonomy) use Copilot's Run 1 only**, matching every other
system's single-run basis — never aggregate or average Copilot across runs for
these. **Runs 1–5 are used exclusively for the Consistency metric above**, which
is single-system and not a cross-system comparison (see PART 3, item 3).

### 1.7 Error taxonomy — apply to every miss and every bucket B/C item

Six categories, fixed:
1. **Fabricated person/event**
2. **Wrong role**
3. **Wrong date**
4. **Organisational confusion** (Foundation vs hospital; wrong hospital)
5. **Stale** (superseded by a later change in the window)
6. **Unsupported citation** (claim not backed by the link given) — **NOT applied this round**: citation validity itself isn't computed this round (see 1.4 addendum), so this category has no reliable basis for this dataset. Report the other 5 categories only, and note the gap.

### 1.8 Provenance stratification — REQUIRED for the preprint

Tag every gold row by origin before scoring:
- `agent-derived` — sourced from Copilot/agent output
- `other-tool-derived` — sourced from Perplexity/Claude/ChatGPT/Gemini output
- `independent` — found via source research (the ~141 rows marked NEWLY ADDED)

**Report recall overall AND on the `independent` subset.** Without this, the agent gets credit for finding items that entered the gold set because the agent found them — a circularity a reviewer will catch immediately.

### 1.9 Judge validation — REQUIRED

Human-adjudicate a stratified random sample of **≥60 items** spanning all systems, tasks and buckets. Report Cohen's κ between human and LLM judge. Disclose the judge model; do not use the same model family as a system under test without noting it.

### 1.10 Gold-sheet column rubric (added 2026-08-31)

Every column in the gold sheets and how it's used, so nothing is scored on an
undocumented assumption:

| Column | Sheets | Used for |
|---|---|---|
| `item_id` | all 3 | Stable row identity; referenced by matched/adjudicated output and by these notes. |
| `task` | all 3 | Routes rows to the correct extraction/matching/scoring pass (ceo / phipa / supervisor). |
| `hospital` | all 3 | Canonical hospital name for the row. |
| `hospital_aliases` | all 3 | Alias list (semicolon-separated) for hospital-name matching, section 1.1. |
| `name_or_issue` | all 3 | Formatted `"Name - Role (detail)"` (or `"Issue - description"` for PHIPA) — matching parses the core name/issue before the first `" - "` and treats the rest as role/detail text, not part of the identity string. |
| `date (YYYY-MM-DD)` | all 3 | Ground-truth date; precision (day/month/year) drives the date-tolerance rules in 1.3. |
| `source` / `link` | all 3 | Human-readable provenance for the gold row itself (not the system's citation, which is a separate field on the extracted item). |
| `in_scope` | all 3 | TRUE/FALSE per the scope rule (1.5). FALSE rows (e.g. Foundation CEOs) stay in gold deliberately — see `status` below — and are excluded from the recall denominator; a system item matching one of these rows is excluded from precision's numerator and denominator too, the same as bucket E. |
| `notes` | all 3 | Free text; used for documented date/title tolerances (1.3) and for provenance/verification annotations added during adjudication checkpoints. |
| `status` | **CEOs only** | See rubric below — this column had no documented handling before 2026-08-31. |
| `confidence_tier` | **CEOs only** | Drives tiered recall (1.6): Tier A (dated announcement), Tier B (directory-confirmed, undated — excluded from date-field scoring, not from recall), Tier C (inferred/approximate date). PHIPA and Supervisor sheets have no tier column; report a single recall for those tasks and say so explicitly in every table that reports CEO tiers. |

**`status` column — CEOs sheet only.** Four values, all currently in use:

| Value | Meaning | Provenance (1.8) | Scoring weight |
|---|---|---|---|
| `Verified by Wendy's team` | Original human-verified baseline row. | tool-derived (unless the row was independently sourced — this status implies it wasn't) | Full weight, no caveat. |
| `NEWLY ADDED - please verify` | Row added to gold after initial collection (~141 rows, including 3 added 2026-08-31 during the Stage 3 checkpoint). | **independent** (per 1.8's literal rule: this exact status string is what "NEWLY ADDED" means) | Full weight for scoring, but disclose in the preprint's limitations that "please verify" rows carry a lighter verification pass than "Verified by Wendy's team" rows — some entered gold because a system under test surfaced them and a human then confirmed them against a primary source, which is a softer form of the exact circularity 1.8's independent-subset control exists to catch. Report this honestly rather than silently treating all "independent" rows as equally clean. |
| `INCLUDED DUE TO SCOPE CHANGE - please verify` | Row added after the scope rule (1.5) was revised/expanded (e.g. VP/Chief roles added later). | tool-derived (per the literal NEWLY-ADDED-only provenance rule — this status string is NOT "NEWLY ADDED") | Full weight, same "please verify" caveat as above. |
| `Excluded - Foundation CEO` | Row IS a Foundation CEO — kept in gold on purpose, with `in_scope = FALSE`, so a system correctly naming a Foundation CEO is recognised as a real identification of a real (but out-of-scope) entity, rather than silently absent from gold and mis-adjudicated as a hallucination. | tool-derived | Excluded from recall denominator and from precision (treated like bucket E — see `in_scope` row above). |

---

## PART 2 — CLAUDE CODE PROMPT SEQUENCE

Run these as **separate sessions with human checkpoints between**. Do not chain into one agentic run — you need to inspect structured output before it propagates into scores.

---

### STAGE 0 — Repository setup

```
I am building an evaluation harness comparing 5 AI systems (Microsoft Copilot
Hospital News Agent, Perplexity, Claude, ChatGPT, Google Gemini) against a
human-verified gold dataset, for a research preprint.

Set up this structure:

/eval
  /data
    gold.xlsx                 # 3 sheets: ceo, phipa, supervisor
    /raw                      # existing: prompt_v0 + 3 task folders + per-LLM runs
  /schema
    extraction_schema.json
  /output
    /extracted /matched /adjudicated /scores /figures
  /scripts
  /docs
    EVALUATION_PLAN.md        # this document

Then:
1. Load gold.xlsx. Print per sheet: row count, column names, in_scope
   TRUE/FALSE counts, confidence_tier distribution (ceo sheet), and count of
   rows with blank dates.
2. Walk /data/raw and print the exact file tree with file sizes, so we can
   confirm which systems have which runs for which tasks.
3. Report any structural inconsistency between the 3 gold sheets.

Do not write any scoring logic yet. Just load, inspect and report.
```

**Checkpoint:** confirm row counts match expectations (CEO = 243) and the raw file tree is complete.

---

### STAGE 1 — Extraction schema and structured extraction

```
Read /eval/docs/EVALUATION_PLAN.md.

Build the extraction stage.

1. Define extraction_schema.json. Each extracted item:
   item_index, system, task, hospital, run_number,
   person_or_issue, role, direction (incoming|outgoing|unclear),
   date_raw, date_normalised (YYYY-MM-DD|YYYY-MM|YYYY|null),
   citation_url (nullable), citation_text (nullable),
   verbatim_snippet   # the exact sentence(s) the item came from

2. Write scripts/extract.py. For each raw response file, use an LLM to convert
   free text into a list of schema-conforming items.

   Extraction rules the prompt MUST enforce:
   - Extract every distinct leadership/CEO/board/supervisor/PHIPA item mentioned,
     including ones you think are wrong. Do NOT filter or correct.
   - One item per person per event. If a person has both an incoming and an
     outgoing event, that is two items.
   - Never invent a citation. If no link is given, citation_url = null.
   - verbatim_snippet must be copied exactly from the response, not paraphrased.
   - If a response says a system could not find information, emit zero items
     for that hospital and record it in a separate `refusals` list.

3. Run extraction over all raw files. Write one JSON per system/task/run to
   /output/extracted/.

4. Print a summary table: system × task × run → item count, refusal count,
   items with null citation.

Use a fixed random seed and temperature 0. Log the exact prompt used to
/output/extracted/_extraction_prompt.txt for the paper's appendix.
```

**Checkpoint:** manually read 10–15 extracted items against their source responses. Extraction errors here contaminate everything downstream.

---

### STAGE 2 — Entity matching

```
Read /eval/docs/EVALUATION_PLAN.md sections 1.1 and 1.3.

Write scripts/match.py.

For each extracted item, attempt a match against the gold sheet for that task:
- Match requires BOTH person/issue AND hospital to match.
- Implement the name-matching rules in section 1.1 (honorifics, nicknames,
  parentheticals, suffixes, documented spelling variants, unambiguous
  misspellings).
- Use the hospital_aliases column for hospital matching.
- Use fuzzy matching as a CANDIDATE GENERATOR only (rapidfuzz, threshold ~85),
  then have an LLM confirm or reject each candidate pair with a one-line reason.
  Never auto-accept a fuzzy match.
- Right person + wrong hospital = NO match; tag as organisational error.

Output to /output/matched/: for every extracted item, matched_gold_item_id or
null, match_confidence, match_reason.
Also output unmatched_gold.json: gold rows no system found, per task.

Print: system × task → matched count, unmatched-system-item count,
unmatched-gold count. Flag any match where the LLM confidence is low for
human review.
```

**Checkpoint:** review every low-confidence match and a 20-item sample of accepted matches.

---

### STAGE 3 — Adjudication of unmatched items

```
Read /eval/docs/EVALUATION_PLAN.md section 1.5.

Write scripts/adjudicate.py.

For every system item with no gold match, classify into exactly one bucket:
A gold gap · B hallucination · C wrong attribution · D out of window · E out of scope

Rules:
- Use the evaluation windows: CEO and supervisor 2021-07-16 to 2026-07-16;
  PHIPA 2026-01-16 to 2026-07-16. Anything outside = bucket D.
- Apply the scope rule: IN = board directors/governors (hospital and Foundation),
  Foundation Chairs and officers, senior leadership (VP/Chief and equivalent).
  OUT = Foundation CEOs and equivalents, committee-only members without a board
  seat, non-voting community members, administrative and trainee staff.
- For bucket A vs B, the judge must state what evidence would confirm the item
  and give a confidence score. Do NOT let the judge browse the web — it will
  hallucinate confirmation. Instead output a `needs_human_check` list.

Output /output/adjudicated/ with bucket, reason and confidence per item.
Print bucket distribution per system per task, and write
/output/adjudicated/needs_human_check.csv for manual resolution.
```

**Checkpoint — the most important one.** Manually resolve every A-vs-B call. This determines both precision and hallucination rate. Do not skip.

---

### STAGE 4 — Scoring

```
Read /eval/docs/EVALUATION_PLAN.md sections 1.2, 1.4, 1.6, 1.7, 1.8.

Write scripts/score.py. Compute exactly the metrics in section 1.6 — no others.

Requirements:
1. Recall by confidence_tier (CEO task). PHIPA and supervisor sheets have no
   tier column — report a single recall for those and say so.
2. Recall on the `independent` provenance subset as well as overall.
   Derive provenance from the gold status column:
   NEWLY ADDED -> independent; everything else -> tool-derived.
3. Precision computed AFTER adjudication, excluding buckets D and E.
4. Field accuracy per field, only over matched entities where the gold field
   is populated. Apply the tolerances in section 1.3 — both values correct.
5. Citation validity on the 0-3 scale. Systems producing no links score 0,
   not N/A.
6. Omission rate = matched entities with a required field blank.
7. Completeness = per response, did it cover all 3 hospitals and both
   directions. Report as flags.
8. Consistency: Copilot only, Runs 1-5. Mean pairwise Jaccard over the 10
   pairs, plus per-item stability (% of items present in all 5 runs).
   LABEL THIS CLEARLY AS SINGLE-SYSTEM — it is not comparative.
9. Apply the 6-category error taxonomy to every miss and every bucket B/C item.

Bootstrap 95% confidence intervals (1000 resamples) for recall, precision and
hallucination rate. With 3 hospitals the CIs will be wide — report them anyway
rather than presenting point estimates as precise.

Write /output/scores/metrics.json and metrics.csv (long format, tidy).
```

**Checkpoint:** sanity-check that recall on the independent subset is lower than overall recall for Copilot. If it isn't, investigate — that would be surprising.

---

### STAGE 5 — Judge validation

```
Read /eval/docs/EVALUATION_PLAN.md section 1.9.

1. Draw a stratified random sample of 60-80 decisions across systems, tasks,
   and decision types (match/no-match, and each adjudication bucket).
2. Write /output/scores/judge_validation_sample.csv with the item, the judge's
   decision, the judge's reason, and a BLANK human_decision column.
3. After I fill it in, compute Cohen's kappa overall and per decision type,
   and write the confusion matrix.
4. Report which decision types the judge is least reliable on.
```

---

### STAGE 6 — Figures

```
Read /eval/docs/EVALUATION_PLAN.md. Produce publication-quality figures to
/output/figures/ as both PNG (300 dpi) and PDF (vector). Colourblind-safe
palette, no chartjunk, consistent system ordering and colours throughout.

FIGURE 1 — Recall by confidence tier (grouped bar)
x = system, grouped bars = Tier A/B/C, y = recall, error bars = bootstrap 95% CI.
CEO task only. This is the headline figure.

FIGURE 2 — Precision vs recall scatter
One point per system per task. Marker shape = task, colour = system.
Diagonal iso-F1 contour lines in light grey. Shows the trade-off directly.

FIGURE 3 — Recall: overall vs independent-provenance subset (paired dot plot)
Two dots per system joined by a line. This is the circularity-control figure
and belongs in the main paper, not the appendix.

FIGURE 4 — Error taxonomy composition (stacked horizontal bar)
One bar per system, segments = the 6 error categories, normalised to 100%.
Carries the qualitative narrative.

FIGURE 5 — Citation validity (stacked bar)
One bar per system, segments = citation scores 3/2/1/0. Annotate mean score.

FIGURE 6 — Field accuracy heatmap
Rows = system, columns = role / date / direction. Cell = accuracy, annotated.
Conditional on entity match — state this in the caption.

FIGURE 7 — Copilot repeat-run consistency (Runs 1-5)
Panel A: item-presence matrix, rows = gold items, columns = runs 1-5, filled
cells = returned. Panel B: pairwise Jaccard heatmap.
Caption must state this is single-system reliability, not a cross-system
comparison.

FIGURE 8 (supplementary) — Per-task metric table rendered as a figure.

For every figure also write a .txt caption file stating what it shows, the n,
and any limitation a reviewer would need. Save the underlying data for each
figure as a CSV next to it so figures are reproducible.
```

---

### STAGE 7 — Results write-up support

```
Generate /output/RESULTS_SUMMARY.md containing:
1. A tidy results table: system × task × metric, with CIs.
2. The 5 largest gold gaps (bucket A) per system — these are findings, since
   they show what the gold set missed.
3. The 10 most common specific errors across all systems.
4. A limitations section drafted from what the harness actually observed,
   covering: n=3 hospitals; repeat runs on one system only; gold-set
   provenance circularity and how it was controlled; LLM-judge error and the
   measured kappa; evaluation-window boundary effects; and the fact that
   PHIPA uses a 6-month window while CEO/supervisor use 5 years.

Be conservative in wording. Do not state a system is better unless the CIs
separate. Where they overlap, say so explicitly.
```

---

## PART 3 — THINGS THAT WILL BITE

1. **Model knowledge cutoffs vs the window.** Events from mid-2026 may be unreachable for some systems for reasons unrelated to retrieval quality. Record each system's stated cutoff and note it in limitations.
2. **PHIPA's window is 6 months, CEO/supervisor 5 years.** Recall is not comparable across tasks. Never put them on the same axis without labelling.
3. **Copilot has 5 runs, others 1.** If you aggregate Copilot across runs you inflate its recall relative to single-run systems. **Use Run 1 only for all cross-system comparisons**, and use Runs 1–5 solely for the consistency metric.
4. **Refusals are not zeros.** A system saying "I cannot find this" is different from a system confidently returning nothing. Track separately.
5. **n = 3 hospitals.** Every CI will be wide. Frame findings as directional, and let the error taxonomy carry the argument.
