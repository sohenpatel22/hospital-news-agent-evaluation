# Evaluation Visualization Report (Clean Style)
### Ontario Health — Copilot Agent Evaluation | Two Test Sets

---

## SET 1 — Deterministic Evaluation

### Visualization 1 · Copilot Agent vs Commercial LLMs — By Metric & Task

![Copilot vs Commercial LLMs — Deterministic](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/deterministic/Vis1A_Copilot_vs_LLMs_Deterministic.png)

> **Reading the chart:** Each column represents a metric (Recall, Precision, F1, Hallucination Rate). Each row is a task (CEO/Board, PHIPA, Supervisors).
>
> **Key finding:** Copilot Agent strongly leads on Recall across all 3 tasks, meaning it finds the most gold-standard items. Commercial LLMs (especially Gemini & Claude) achieve higher Precision but miss more events. Hallucination Rate is notable across all models for the CEO task.

---

### Visualization 2 · MS Copilot Agent — Prompt Run Consistency (5 Runs)

![Copilot Run Comparison — Deterministic](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/deterministic/Vis1B_Copilot_Run_Comparison_Deterministic.png)

> **Reading the chart:** Each panel shows Recall, Precision, and F1 across 5 identical prompt runs for the Copilot Agent. Run 1 is the baseline prompt. The dashed line marks the best-performing run (highest F1).
>
> **Key finding:**
> - **CEO task:** Performance improves steadily from Run 1 to Run 5, showing that repeated runs or optimized prompting yield higher F1.
> - **PHIPA task:** High variance — Run 4 drops to 0, while Runs 1, 3, and 5 perform well. This indicates instability in the agent's PHIPA event detection.
> - **Supervisors:** Runs 1 and 3–5 are excellent, while Run 2 fails, suggesting occasional zero-result responses even for confirmed hospitals.

---

## SET 2 — LLM-as-Judge Evaluation (7 Metrics)

### Visualization 3 · Copilot Agent vs Commercial LLMs — All 7 Quality Metrics

![Copilot vs Commercial LLMs — LLM Judge](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/llm_judge/Vis2A_Copilot_vs_LLMs_LLM_Judge.png)

> **Reading the chart:** This expands the deterministic metrics with 4 additional LLM-judged qualitative metrics (Relevance, Groundedness, Completeness, Answer Relevancy). 
>
> **Key findings:**
> - **Supervisors task:** Near-perfect scores across all models for all 7 metrics, showing that LLM extraction correctly handles previously malformed outputs.
> - **PHIPA task:** Copilot uniquely achieves Recall = 1.0 but low Precision and Groundedness. It over-reports but doesn't miss events.
> - **CEO task:** Copilot leads on F1 and Relevance, while Claude achieves the highest Precision and Groundedness.

---

### Visualization 4 · Qualitative Dimension Deep-Dive — Radar by Task

![Qualitative DeepDive — LLM Judge](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/llm_judge/Vis2B_Qualitative_DeepDive_LLM_Judge.png)

> **Reading the chart:** Each radar chart displays the 4 LLM-judged quality dimensions per task. A larger filled area indicates better overall quality. MS Copilot Agent is highlighted with the thickest line.
>
> **Key findings:**
> - **CEO task (left):** Copilot and Claude provide the strongest responses. Many other models scored 0 as they returned completely off-topic answers for certain hospitals.
> - **PHIPA task (centre):** The key differentiator is Completeness — Copilot and Gemini are the only models that successfully identified the Hamilton PHIPA decision.
> - **Supervisors task (right):** All models perform very well. Claude and ChatGPT lead slightly on Relevance, but all models achieve full Completeness.
