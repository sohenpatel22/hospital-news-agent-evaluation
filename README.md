# Hospital News Agent Evaluation

Evaluation of a **Microsoft 365 Copilot "Hospital News Agent"** against Perplexity, Claude, ChatGPT and Google Gemini
on three Ontario-hospital monitoring tasks:

| Task | What the system must find | Window |
|---|---|---|
| **CEO / leadership changes** | Incoming/outgoing executives and board leadership | 5 years (2021-07-16 → 2026-07-16) |
| **PHIPA decisions** | Privacy-commissioner decisions involving hospitals | 6 months (2026-01-16 → 2026-07-16) |
| **Interim supervisors** | Ministry-appointed hospital supervisors | 5 years |

Each system's answers are matched against a manually verified **gold dataset**, adjudicated (gold gap / hallucination /
wrong attribution / out-of-window / out-of-scope), and scored for recall, precision, hallucination rate, field accuracy
(role, date, direction), specificity, omission and run-to-run consistency. See [`docs/methodology`](docs/methodology).

## Repository layout

```
docs/                     methodology, evaluation plan, rubric, reports, agent instructions, prompts
data/gold/                every version of the gold datasets (history); experiments pin their own snapshot
experiments/              one self-contained folder per evaluation round (code + raw responses + outputs)
  exp01_baseline_gold_v1            first gold set; deterministic scoring + LLM-as-judge
  exp02_updated_gold_full_eval      ★ main study: updated gold, 5 systems x 3 tasks, full pipeline
  exp03_ceo_prompt_iterations       CEO task, short window, prompts V0 / V1 / V2
  exp04_ceo_5yr_baseline            CEO task, 5-year window, baseline prompt
  exp05_ceo_5yr_chain_of_thought    CEO task, 5-year window, chain-of-thought prompt
  cross_version_comparison          F1 / hallucination comparison across versions
observability/langfuse/   logs every experiment's metrics to Langfuse
```

Details for each experiment: [`experiments/README.md`](experiments/README.md).

## Headline findings (CEO task, F1)

| Model | 5-yr baseline (exp04) | 5-yr chain-of-thought (exp05) |
|---|---|---|
| ChatGPT | 0.253 | **0.569** |
| MS Copilot Agent | 0.247 | 0.418 |
| Perplexity | 0.157 | 0.417 |
| Claude | 0.196 | 0.372 |
| Gemini | 0.092 | 0.070 |

Chain-of-thought prompting sharply reduced hallucination (ChatGPT 78% → 27%). In the main study (exp02) CEO recall is
low for every system (13–26%) and 7 of 10 system pairs have overlapping 95% CIs – read
[`docs/reports/RESULTS_SUMMARY.md`](docs/reports/RESULTS_SUMMARY.md) for caveats (n = 3 hospitals per task,
gold-set provenance circularity, citation validity not scored).

## Running

```bash
pip install -r requirements.txt

# main study (exp02) - stages run in order, all paths are relative to the experiment folder
cd experiments/exp02_updated_gold_full_eval/scripts
python extract.py && python match.py && python adjudicate.py && python score.py && python plot_figures.py

# CEO-task experiments (exp04 / exp05): run from the workspace folder
cd experiments/exp04_ceo_5yr_baseline/workspace && python v4_evaluator.py && python v4_visualizer_updated.py
```

## Observability (Langfuse)

```bash
cp .env.example .env            # fill in Langfuse keys
python observability/langfuse/log_experiments.py --dry-run
python observability/langfuse/log_experiments.py
```

One trace per *experiment × prompt version × system × task*, grouped by session (= experiment), tagged, with every
metric attached as a score. See [`observability/README.md`](observability/README.md).

## Notes

- Presentations/slides and internal correspondence are deliberately **not** part of this repository.
- Prompt "V3 (completeness checklist + recall-first)" was never run; the placeholder folder from the original
  workspace contained copies of V0 responses and was dropped.
- Never commit API keys; use `.env` (git-ignored).
