# Evaluation Pipeline — README

## What's in this folder

| File | Purpose |
|---|---|
| `gold_task1_phipa.csv` | Gold standard for Task 1 (PHIPA) — already filled in |
| `gold_task2_ceo.csv` | Gold standard for Task 2 (CEO/Leadership) — already filled in |
| `gold_task3_supervisors.csv` | Gold standard for Task 3 (Interim Supervisors) — already filled in |
| `extraction_prompt_template.md` | Fixed prompt to paste into Gemini to convert a response doc into rows |
| `extracted_responses_template.csv` | Empty CSV with the right headers — build your master file from this |
| `score_evaluation.py` | The scoring script — run once per task |

## End-to-end workflow

1. **Collect responses** — you're already doing this (one .docx per tool/task/prompt-version/run).
2. **Extract** — for each response doc, paste it into Gemini using `extraction_prompt_template.md`
   (fill in the 4 metadata fields first). Copy the returned rows into a growing
   `extracted_responses_task1.csv` / `_task2.csv` / `_task3.csv` (one master file per task,
   matching `extracted_responses_template.csv`'s columns).
3. **Score** — run:
   ```
   python3 score_evaluation.py --gold gold_task1_phipa.csv --responses extracted_responses_task1.csv --out results_task1/
   ```
   Repeat for task2 and task3 with their respective gold files.
4. **Review flagged hallucinations by hand** — open `results_task1/item_level_results.csv`,
   filter to `result == FLAGGED_POSSIBLE_HALLUCINATION_REVIEW_MANUALLY`, and check each one.
   Some will be real hallucinations; some may reveal a gap in your gold dataset (a real
   item you missed) — either outcome is useful, but don't report the raw flagged count
   as "hallucination rate" without this check.
5. **Read the outputs**:
   - `hospital_summary.csv` — per-hospital recall/precision/F1/date-accuracy, one row per (tool, prompt_version, run, hospital)
   - `tool_summary.csv` — aggregated per (tool, prompt_version) — this is your headline comparison table
   - `consistency_results.csv` — only populated for `prompt_version == v0` (your 5-repeat-run set)
   - `link_check_results.csv` — HTTP validity + credibility tier per unique link

## Important caveats to keep in mind

- **Matching is fuzzy-text + date-proximity, not semantic.** `NAME_MATCH_THRESHOLD` (0.55)
  and `DATE_TOLERANCE_DAYS` (3) are starting points — if you see obviously-same items not
  matching, or obviously-different items matching, lower/raise the threshold at the top
  of `score_evaluation.py` and re-run. Spot-check `item_level_results.csv` after your
  first real run before trusting the numbers.
- **Hallucination flags need a human pass.** The script can't tell "the tool invented
  this" from "this is real but my gold dataset doesn't have it yet." Always check.
- **Link checking only tests whether the URL resolves** (HTTP status) — it does NOT
  confirm the page actually supports the claim. That "link support" check still needs
  a bounded LLM read or a manual check on a sample, as discussed separately.
- **Consistency only makes sense for `v0`** (your 5-repeat-run baseline) — V1/V2/Wendy's-
  original are single runs, so there's nothing to compare across.
- **Tool-level rates are computed from summed counts, not averaged ratios** — this avoids
  a common distortion where a hospital with 1 gold item and a hospital with 10 gold items
  get equal weight in an average. If you want equal-weight-per-hospital instead, that's
  a one-line change in the `tool_summary` aggregation — ask if you want that variant too.
- **Extend `CREDIBILITY_TIERS` and `HOSPITAL_DOMAINS`** at the top of the script as you
  encounter new source domains in real responses (e.g. specific local news sites).

## If something looks wrong

- Re-run with a small hand-crafted `test_responses.csv` (a few rows you know the "right"
  answer for) to sanity-check the matching logic before trusting a big batch.
- The script never overwrites your gold CSVs or your extracted-responses CSV — it only
  writes into the `--out` directory, so it's always safe to re-run.
