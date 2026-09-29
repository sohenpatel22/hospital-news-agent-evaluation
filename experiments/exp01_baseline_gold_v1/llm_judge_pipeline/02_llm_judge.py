"""
02_llm_judge.py
===============
Stage 2: LLM-as-Judge — Claude Sonnet 3.5 evaluates 4 qualitative metrics
for every (model, task, hospital) group. Uses the extracted JSON from Stage 1
as context. Results cached to judge_scores/.

Metrics scored:
  - relevance       (0-3): Does the response directly answer the user intent?
  - groundedness    (0-3): Are claims supported by cited sources?
  - completeness    (0.0-1.0): What fraction of gold items does it cover?
  - answer_relevancy (0.0-1.0): RAGAS-inspired, how focused/on-topic is the response?
"""

import os
import re
import json
import time
import pathlib
import pandas as pd
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BASE = pathlib.Path(__file__).parent
EXTRACTED_DIR = BASE / "extracted_events"
GOLD_CSV = BASE.parent / "deterministic_pipeline" / "gold" / "all_gold.csv"
OUT_DIR = BASE / "judge_scores"

TASK_INTENT = {
    "phipa": "Provide an exhaustive list of Ontario hospital PHIPA-related news updates for the specified hospital in the last six months.",
    "ceo": "Provide an exhaustive list of hospital leadership, CEO and board member changes for the specified hospital in the last 5 years.",
    "supervisors": "Provide an exhaustive list of interim supervisors appointed by the Government of Ontario to the specified hospital in the last 5 years.",
}

JUDGE_PROMPT = """You are an expert evaluator for an Ontario Health AI agent evaluation study.
Your task is to score a model's response across 4 quality dimensions.

== ORIGINAL USER INTENT ==
{intent}
Hospital: {hospital}

== GOLD STANDARD (ground truth — what should have been found) ==
{gold_items}

== MODEL RESPONSE (structured extraction) ==
Model: {model}
Extracted events:
{extracted_events}
Model declared no results: {declared_none}

== SCORING INSTRUCTIONS ==
Score ONLY based on the information above. Return ONLY a valid JSON object with no markdown fencing.

1. RELEVANCE (0-3): Does the response directly answer the user's intent?
   0 = Completely off-topic or talks about wrong hospital/task
   1 = Partially relevant, significant irrelevant content
   2 = Mostly relevant with minor off-topic content
   3 = Fully relevant, directly answers the intent

2. GROUNDEDNESS (0-3): Are factual claims supported by cited sources?
   0 = No sources cited, or all sources are fabricated/invalid
   1 = Some sources but many uncited or dubious claims
   2 = Most claims have sources; minor gaps
   3 = All significant claims have credible cited sources

3. COMPLETENESS (0.0-1.0): What fraction of gold standard items does this response cover?
   Count how many gold items are mentioned/covered (even partially) and divide by total gold items.
   If gold has 0 items and model correctly says none found: 1.0
   If gold has 0 items but model hallucinates events: 0.0
   Provide a brief "missed_items" list of gold items NOT covered.

4. ANSWER_RELEVANCY (0.0-1.0): RAGAS-inspired metric.
   Generate 3 questions that this response would answer. Then judge how closely those
   questions match the original intent. Score = proportion of generated questions that
   align with the original intent.

Return this exact JSON:
{{{{
  "relevance": <0-3>,
  "relevance_reason": "<one sentence>",
  "groundedness": <0-3>,
  "groundedness_reason": "<one sentence>",
  "completeness": <0.0-1.0>,
  "completeness_reason": "<one sentence>",
  "missed_items": ["<item1>", "<item2>"],
  "answer_relevancy": <0.0-1.0>,
  "answer_relevancy_reason": "<one sentence>",
  "generated_questions": ["<q1>", "<q2>", "<q3>"]
}}}}"""


def slug(s):
    return re.sub(r'[^\w]', '_', str(s))[:50]

def call_claude(prompt: str, max_retries=3) -> str:
    for attempt in range(max_retries):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                print(f"  Retry {attempt+1} after {wait}s: {e}")
                time.sleep(wait)
            else:
                raise

def load_extracted(task, model, hospital) -> list[dict]:
    """Load all runs for (task, model, hospital) from cached extraction JSONs."""
    task_dir = EXTRACTED_DIR / task / slug(model)
    events_by_run = {}
    declared_none = False
    for f in task_dir.glob(f"{slug(hospital)}_run*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            run = data.get("run_number", 1)
            events_by_run[run] = data.get("events", [])
            if data.get("model_declared_none", False):
                declared_none = True
        except Exception:
            pass
    # Flatten: aggregate unique events across all runs (for commercial LLMs which have 1 run)
    all_events = []
    seen = set()
    for run_events in events_by_run.values():
        for e in run_events:
            key = str(e.get("name_or_issue", ""))[:80]
            if key not in seen:
                seen.add(key)
                all_events.append(e)
    return all_events, declared_none

def run_judge(force_rerun=False):
    print("--- Stage 2: LLM-as-Judge ---")
    
    gold_df = pd.read_csv(GOLD_CSV)
    gold_df["in_scope"] = gold_df["in_scope"].astype(str).str.strip().str.lower() == "true"
    
    MODELS = ["MS Copilot Agent", "ChatGPT", "Claude", "Gemini", "Perplexity"]
    TASKS = ["phipa", "ceo", "supervisors"]
    
    done = skipped = errors = 0
    
    for task in TASKS:
        for model in MODELS:
            task_dir = EXTRACTED_DIR / task / slug(model)
            if not task_dir.exists():
                continue
            
            # Find unique hospitals for this task/model
            hospitals = set()
            for f in task_dir.glob("*_run*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    hospitals.add(data.get("hospital", ""))
                except Exception:
                    pass
            
            for hospital in sorted(hospitals):
                if not hospital:
                    continue
                
                out_dir = OUT_DIR / task / slug(model)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"{slug(hospital)}.json"
                
                if out_file.exists() and not force_rerun:
                    skipped += 1
                    continue
                
                print(f"  Judging [{task}] {model} / {hospital} ...", end=" ")
                
                # Get gold items for this task+hospital
                gold_items = gold_df[
                    (gold_df["task"] == task) &
                    (gold_df["hospital"].str.lower().str.strip() == hospital.lower().strip()) &
                    (gold_df["in_scope"] == True)
                ]["name_or_issue"].tolist()
                
                # Also try alias matching if direct match fails
                if not gold_items:
                    gold_items = gold_df[
                        (gold_df["task"] == task) &
                        (gold_df["in_scope"] == True) &
                        (gold_df.apply(lambda r: hospital.lower() in str(r.get("hospital_aliases","")).lower() or
                                       hospital.lower() in str(r.get("hospital","")).lower(), axis=1))
                    ]["name_or_issue"].tolist()
                
                extracted_events, declared_none = load_extracted(task, model, hospital)
                
                gold_str = "\n".join(f"- {g}" for g in gold_items) if gold_items else "(none — this hospital is expected to have zero events)"
                extracted_str = json.dumps(extracted_events[:20], indent=2, ensure_ascii=False)  # cap at 20 events
                
                prompt = JUDGE_PROMPT.format(
                    intent=TASK_INTENT[task],
                    hospital=hospital,
                    gold_items=gold_str,
                    model=model,
                    extracted_events=extracted_str,
                    declared_none=declared_none
                )
                
                try:
                    raw = call_claude(prompt)
                    clean = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
                    clean = re.sub(r'```\s*$', '', clean.strip())
                    scores = json.loads(clean)
                    scores.update({"task": task, "model": model, "hospital": hospital})
                    out_file.write_text(json.dumps(scores, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"OK (rel={scores.get('relevance')}, gnd={scores.get('groundedness')}, cmp={scores.get('completeness'):.2f})")
                    done += 1
                except Exception as e:
                    print(f"ERROR: {e}")
                    errors += 1
                
                time.sleep(0.5)
    
    print(f"\nDone. Judged: {done}, Skipped (cached): {skipped}, Errors: {errors}")

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run_judge(force_rerun=force)
