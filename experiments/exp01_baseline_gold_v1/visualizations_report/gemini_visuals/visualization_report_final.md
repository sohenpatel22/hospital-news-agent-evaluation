# Final Evaluation Visualizations 
### Ontario Health — Copilot Agent Evaluation | Two Test Sets

---

## SET 1 — Deterministic Evaluation

### Visualization 1 · Copilot Agent vs Commercial LLMs — By Metric & Task

Reverting to the unified grid format as requested, this chart clearly visualizes all four deterministic metrics (including Hallucination Rate) side by side for direct comparison across models and tasks.

![Vis1 Deterministic Grid](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/final/deterministic/Vis1_Deterministic_Grid.png)

---

### Visualization 2 · MS Copilot Agent — Prompt Run Consistency (5 Runs)

This chart tracks the Overall Quality (F1 Score) across the 5 repeated prompt runs. Missing or empty runs (like PHIPA run 4) are marked as "Failed" while the lines correctly connect the valid data points to easily trace the consistency trend.

![Vis2 Deterministic Run Consistency](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/final/deterministic/Vis2_Deterministic_Run_Consistency.png)

---

## SET 2 — LLM-as-Judge Evaluation 

### Visualization 3 · Copilot Agent vs Commercial LLMs — Main & Qualitative Metrics

This grid incorporates all 7 metrics (3 deterministic + 4 LLM-judged qualitative metrics) across all models, making it simple to evaluate total performance at a glance.

![Vis3 LLM Judge Grid](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/final/llm_judge/Vis3_LLM_Judge_Grid.png)

---

### Visualization 4 · Copilot Agent — Prompt Run Consistency (LLM Extracted)

To complete the LLM-as-Judge pipeline analysis, this chart computes the exact match F1 score dynamically from the raw extracted JSON files for each of the 5 repeated prompt runs. It confirms that LLM extraction stabilizes and vastly improves the F1 scores for the Supervisors task across runs.

![Vis4 LLM Run Consistency](file:///C:/Users/ASUS/Desktop/OH%20Agent%20Docs/Antigravity%20Evaluation/visualizations_report/gemini_visuals/final/llm_judge/Vis4_LLM_Judge_Run_Consistency.png)
