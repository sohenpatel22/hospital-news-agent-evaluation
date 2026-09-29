"""Quick smoke test — extract 3 docs to verify API key and pipeline work."""
import os, json, pathlib
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Quick test
print("Testing API connection...")
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say 'API OK' and nothing else."}]
)
print("Response:", msg.content[0].text)
print("API key valid!")

# Quick extraction test on 2 docs
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import importlib.util, pandas as pd

spec = importlib.util.spec_from_file_location("extract", pathlib.Path(__file__).parent / "01_llm_extract.py")
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)

raw_csv = pathlib.Path(__file__).parent.parent / "evaluation" / "raw_outputs" / "raw_outputs.csv"
df = pd.read_csv(raw_csv)

print("\n--- Testing extraction on 2 sample docs ---")
for _, row in df.sample(2, random_state=42).iterrows():
    print(f"\nDoc: [{row['task']}] {row['model']} / {row['hospital']} run {row['run_number']}")
    result = extract.extract_doc(row)
    print(f"Events extracted: {len(result.get('events', []))}")
    print(f"model_declared_none: {result.get('model_declared_none')}")
    if result.get('events'):
        print(f"First event: {json.dumps(result['events'][0], indent=2)[:300]}")
print("\nSmoke test passed!")
