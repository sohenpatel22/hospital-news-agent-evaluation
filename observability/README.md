# Observability with Langfuse

`langfuse/log_experiments.py` reads the metric files of every experiment and logs them to a Langfuse project.

- **Trace** = one experiment × prompt version × system × task (deterministic id → re-runs overwrite, never duplicate)
- **Session** = experiment id (`exp02_updated_gold_full_eval`, …)
- **Tags** = experiment, `prompt:<v>`, `system:<name>`, `task:<t>`, `gold:<version>`
- **Scores** = recall, precision, f1, hallucination_rate, field accuracy, specificity, … (numeric)
- **Metadata** = gold version, evaluation window, source file, bootstrap CI bounds (exp02)

Setup: create a project in Langfuse, copy its API keys into `.env` (see `.env.example`), then run the script.
In the UI use *Scores* / *Traces* filtered by tag to compare prompt versions or systems.
