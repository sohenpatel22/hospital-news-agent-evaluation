# Comprehensive Evaluation Metrics Comparison (v3, v4, v5)

This report aggregates and compares the evaluation metrics from the different versions of the CEO task dataset and prompt engineering efforts.

## 1. Version 3: CEO Task - Iterative Prompting
This phase evaluated three different prompting strategies. We compare the **F1 Score** (which balances precision and recall) for the models.

| Model | v3_V0 (Short Time Window) | v3_V1 (Structured Prompt) | v3_V2 |
| :--- | :--- | :--- | :--- |
| **Claude** | **0.640** (Best Overall) | 0.428 | 0.500 |
| **ChatGPT** | 0.608 | 0.580 | 0.285 |
| **MS Copilot Agent** | 0.615 | 0.551 | 0.235 |
| **Gemini** | 0.454 | 0.400 | 0.307 |
| **Perplexity** | 0.434 | 0.173 | 0.285 |

**Conclusion for v3:** The `V0 - Short Time Window` prompt surprisingly yielded the best results on this dataset, with **Claude** achieving the highest F1 Score of **0.640**. The V2 prompt iteration saw a severe degradation in performance across all models, likely due to overly restrictive constraints or hallucination spikes.

---

## 2. Version 4 vs Version 5: The 5-Year Dataset Challenge
In versions 4 and 5, the dataset was expanded to a much more rigorous 5-year timeframe, significantly increasing the complexity of extraction.

* **v4**: Baseline evaluation on the 5-year dataset.
* **v5**: Applying **Chain-of-Thought (CoT)** reasoning with Prompt V2 on the 5-year dataset.

### F1 Score Comparison (v4 vs v5)
| Model | v4 (Baseline Prompt) | v5 (Chain-of-Thought) | Improvement |
| :--- | :--- | :--- | :--- |
| **ChatGPT** | 0.253 | **0.568** | +124% |
| **MS Copilot Agent**| 0.247 | 0.418 | +69% |
| **Perplexity** | 0.156 | 0.416 | +166% |
| **Claude** | 0.196 | 0.372 | +89% |
| **Gemini** | 0.092 | 0.070 | -23% |

### Hallucination Rate (v4 vs v5)
| Model | v4 (Baseline Prompt) | v5 (Chain-of-Thought) |
| :--- | :--- | :--- |
| **ChatGPT** | 78.0% | **27.0%** (Massive Reduction) |
| **Claude** | 46.6% | 36.3% |
| **MS Copilot** | 80.9% | 31.0% |

**Conclusion for v4 vs v5:** The 5-year dataset proved extremely difficult for the baseline prompt in v4. However, the introduction of **Chain-of-Thought (CoT)** prompting in v5 resulted in a **massive breakthrough**. ChatGPT's F1 score more than doubled (from 0.25 to 0.56) and its hallucination rate plummeted from 78% to 27%.

---

## 🏆 Final Verdict

### Best Dataset / Prompt Combination
The absolute highest F1 Score (0.640) was achieved on the smaller dataset context in **v3_V0 (Short Time Window)** using Claude.

However, for the more rigorous and representative **5-year dataset**, the **v5 (Chain-of-Thought Prompting)** is unequivocally the best performer.

* **Best Prompt for Complex Data**: `v5 Chain-of-Thought Prompt`
* **Best Model for Complex Data**: `ChatGPT` (F1: 0.568, Hallucination: 27%)
* **Most Reliable Strategy**: Forcing the model to output its reasoning step-by-step (Chain-of-Thought) drastically lowered hallucination rates and improved F1 scores across almost all models in the most complex 5-year evaluation.
