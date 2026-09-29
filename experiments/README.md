# Experiments

Each folder is self-contained: scripts read and write only inside their own experiment folder, so results can be
reproduced without the rest of the repo. Every experiment pins the gold-dataset snapshot it was scored against
(`data/gold/` keeps the full version history).

| ID | Original name | Question | Gold | Prompt | Key scripts |
|---|---|---|---|---|---|
| exp01 | Antigravity Evaluation_v1 | First baseline: deterministic matching vs LLM-as-judge | v1 baseline | V0 | `deterministic_pipeline/run_pipeline.py`, `llm_judge_pipeline/run_pipeline_llm.py` |
| exp02 | Code for Updated Dataset Evaluation_v2 | ★ Full study, 5 systems x 3 tasks, adjudication, bootstrap CIs, Copilot 5-run consistency | v2 updated | V0 | `scripts/extract.py → match.py → adjudicate.py → score.py → plot_*.py` |
| exp03 | Code for Updated CEO Task_v3 | Does prompt engineering help on the short-window CEO task? | CEO (16 / 7 items) | V0, V1 (persona+scope rules), V2 (CoT+few-shot) | `prompt_v*/…evaluator.py` |
| exp04 | Code for New Verified CEO Dataset_v4 | Baseline on the verified 5-year CEO dataset (133 items) | ceo_5yr | V0 | `workspace/v4_evaluator.py` |
| exp05 | …v5-ChainOfThoughtPrompt | Same dataset with chain-of-thought prompt | ceo_5yr | V2 (CoT) | `workspace/v5_evaluator_corrected.py` |
| — | comparision | Cross-version summary and figures | — | — | `cross_version_comparison/*.md` |

Folder conventions inside an experiment: `raw_responses/` (system outputs, `.docx`), `gold/` or `data/` (pinned gold),
`scripts/` or `workspace/` (code), `output/` or `Metrics/`+`Visualizations/` (generated results).
