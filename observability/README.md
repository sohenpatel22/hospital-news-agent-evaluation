# Observability with Langfuse

`langfuse/log_experiments.py` reads the metric files of every experiment and logs them to a Langfuse project.

- **Trace** = one experiment × prompt version × system × task (deterministic id → re-runs overwrite, never duplicate)
- **Session** = experiment id (`exp02_updated_gold_full_eval`, …)
- **Tags** = experiment, `prompt:<v>`, `system:<name>`, `task:<t>`, `gold:<version>`
- **Scores** = recall, precision, f1, hallucination_rate, field accuracy, specificity, … (numeric)
- **Metadata** = gold version, evaluation window, source file, bootstrap CI bounds (exp02)

Setup: create a project in Langfuse, copy its API keys into `.env` (see `.env.example`), then run the script.
In the UI use *Scores* / *Traces* filtered by tag to compare prompt versions or systems.

## Hospital-level traces (exp02)

`langfuse/log_hospital_traces.py` adds one trace per **system x task x hospital x run**
(`exp02/<task>/<hospital>/<system>/run<n>`, tag `level:hospital`), reusing `score.py`'s own record builder so the
numbers reconcile with the aggregate table.

- Scores: recall, precision, hallucination_rate, n_gold, n_extracted, n_tp, n_bucket_a/b/c
- Child span per extracted item: input = person/role/direction/date/citation, output = adjudication bucket
  (TP / A / B / C) and matched gold row; hallucinations and wrong attributions (B/C) are flagged `ERROR`
- Trace metadata lists the gold rows the system **missed** at that hospital
- MS Copilot has runs 1-5 (consistency analysis); filter `run:1` for cross-system comparisons
