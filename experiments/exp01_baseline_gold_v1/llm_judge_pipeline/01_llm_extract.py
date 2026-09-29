"""
01_llm_extract.py
=================
Stage 1: Use Claude Sonnet 3.5 to extract structured events from all 162 raw
document texts. Results are cached to disk as JSON — re-runs cost nothing.

Output per doc: extracted_events/<task>/<model_slug>/<hospital_slug>_run<N>.json
  {
    "task": "phipa|ceo|supervisors",
    "model": "...",
    "hospital": "...",
    "run_number": N,
    "model_declared_none": true|false,
    "events": [
      {
        "name_or_issue": "...",
        "person_name": "...",       # extracted name if applicable
        "phipa_id": "...",          # PHIPA/PO decision ID if applicable
        "date": "YYYY-MM-DD or free text",
        "source": "...",
        "link": "https://..."
      }
    ]
  }
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
RAW_CSV = BASE.parent / "deterministic_pipeline" / "raw_outputs" / "raw_outputs.csv"
OUT_DIR = BASE / "extracted_events"

# ---------------------------------------------------------------------------
# Task-specific extraction prompts
# ---------------------------------------------------------------------------

PROMPTS = {
    "phipa": """You are a data extraction assistant for Ontario Health hospital performance research.
Extract ALL PHIPA-related events from the hospital performance response below.
Return ONLY a valid JSON object with no markdown fencing, matching this schema exactly:
{{
  "model_declared_none": false,
  "events": [
    {{
      "name_or_issue": "concise label for the PHIPA event (include decision/order number if present)",
      "phipa_id": "e.g. PHIPA Decision 338 or PO-4820 (null if not stated)",
      "date": "YYYY-MM-DD or free text date (null if not stated)",
      "source": "publication or institution name (null if not stated)",
      "link": "URL (null if not stated)"
    }}
  ]
}}
If the response explicitly states no PHIPA events were found, set model_declared_none to true and events to [].
Do NOT include events the response explicitly excluded or flagged as out-of-scope.
Hospital: {hospital}
Response text:
{text}""",

    "ceo": """You are a data extraction assistant for Ontario Health hospital performance research.
Extract ALL leadership changes (CEO, Board Chair, Board Directors, Interim/Acting roles) from the response below.
Return ONLY a valid JSON object with no markdown fencing, matching this schema exactly:
{
  "model_declared_none": false,
  "events": [
    {
      "name_or_issue": "Person Name - Role (incoming/outgoing)",
      "person_name": "Full name of the person",
      "role": "e.g. President/CEO, Board Chair, Board Director",
      "direction": "incoming or outgoing",
      "date": "YYYY-MM-DD or free text date (null if not stated)",
      "source": "publication or institution name (null if not stated)",
      "link": "URL (null if not stated)"
    }
  ]
}
If the response says no leadership changes were found, set model_declared_none to true and events to [].
Do NOT include executive roles below Board Director level (e.g. Chiefs of Departments) unless they are CEO/President.
Hospital: {hospital}
Response text:
{text}""",

    "supervisors": """You are a data extraction assistant for Ontario Health hospital performance research.
Extract ALL Government of Ontario-appointed hospital supervisors or investigators from the response below.
Return ONLY a valid JSON object with no markdown fencing, matching this schema exactly:
{
  "model_declared_none": false,
  "events": [
    {
      "name_or_issue": "Person Name - Role (e.g. Supervisor (s.9))",
      "person_name": "Full name of the appointed person",
      "role": "Supervisor or Investigator",
      "appointment_date": "YYYY-MM-DD or free text (null if not stated)",
      "termination_date": "YYYY-MM-DD or free text (null if not stated)",
      "order_in_council": "e.g. Order in Council 1271/2024 (null if not stated)",
      "source": "publication or institution name (null if not stated)",
      "link": "URL (null if not stated)"
    }
  ]
}
If the response explicitly states no supervisor appointments were found, set model_declared_none to true and events to [].
Hospital: {hospital}
Response text:
{text}"""
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slug(s):
    return re.sub(r'[^\w]', '_', str(s))[:50]

def call_claude(prompt: str, max_retries=3) -> str:
    for attempt in range(max_retries):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
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

def extract_doc(row) -> dict:
    task = row["task"]
    prompt_template = PROMPTS[task]
    # Truncate very long texts to ~6000 chars to stay within context limits cheaply
    text = str(row["raw_text"])[:8000]
    prompt = prompt_template.replace("{hospital}", str(row["hospital"])).replace("{text}", text)
    
    raw_response = call_claude(prompt)
    
    # Parse JSON from response
    try:
        # Strip any accidental markdown fencing
        clean = re.sub(r'^```(?:json)?\s*', '', raw_response.strip(), flags=re.MULTILINE)
        clean = re.sub(r'```\s*$', '', clean.strip())
        result = json.loads(clean)
    except json.JSONDecodeError:
        print(f"  Warning: JSON parse failed for {task}/{row['model']}/{row['hospital']} run {row['run_number']}")
        result = {"model_declared_none": False, "events": [], "parse_error": raw_response[:200]}
    
    result["task"] = task
    result["model"] = row["model"]
    result["hospital"] = row["hospital"]
    result["run_number"] = int(row["run_number"])
    return result

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_extraction(force_rerun=False):
    print("--- Stage 1: LLM Event Extraction ---")
    df = pd.read_csv(RAW_CSV)
    
    total = len(df)
    done = 0
    skipped = 0
    errors = 0
    
    for _, row in df.iterrows():
        task_dir = OUT_DIR / row["task"] / slug(row["model"])
        task_dir.mkdir(parents=True, exist_ok=True)
        out_file = task_dir / f"{slug(row['hospital'])}_run{row['run_number']}.json"
        
        if out_file.exists() and not force_rerun:
            skipped += 1
            continue
        
        print(f"  Extracting [{row['task']}] {row['model']} / {row['hospital']} run {row['run_number']} ...", end=" ")
        try:
            result = extract_doc(row)
            out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            n = len(result.get("events", []))
            print(f"OK ({n} events)")
            done += 1
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1
        
        # Rate limit: be polite to the API
        time.sleep(0.5)
    
    print(f"\nDone. Extracted: {done}, Skipped (cached): {skipped}, Errors: {errors}")
    print(f"Total docs: {total}")

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run_extraction(force_rerun=force)
