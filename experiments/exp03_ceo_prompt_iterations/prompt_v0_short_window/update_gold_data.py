import json
import pandas as pd
from openpyxl import load_workbook

# 1. Update gold_llm.json
gold_file = 'Gold_Parsed/gold_llm.json'
with open(gold_file, 'r', encoding='utf-8') as f:
    gold_data = json.load(f)

new_entries = [
    {
        "item_id": "C126",
        "task": "ceo",
        "hospital": "North York General Hospital",
        "hospital_aliases": ["North York General", "NYGH"],
        "name": "Dr. Kathryn Nichol",
        "role": "Board Governor",
        "date": "2026-06",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    },
    {
        "item_id": "C127",
        "task": "ceo",
        "hospital": "Arnprior Regional Health",
        "hospital_aliases": ["ARH"],
        "name": "Dr. Matthew Dick",
        "role": "Board Director",
        "date": "2026-06",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    },
    {
        "item_id": "C128",
        "task": "ceo",
        "hospital": "Arnprior Regional Health",
        "hospital_aliases": ["ARH"],
        "name": "Katrina Roberts",
        "role": "Board Director",
        "date": "2026-06",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    },
    {
        "item_id": "C129",
        "task": "ceo",
        "hospital": "Arnprior Regional Health",
        "hospital_aliases": ["ARH"],
        "name": "Bill Stevens",
        "role": "Board Director",
        "date": "2026-06",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    },
    {
        "item_id": "C130",
        "task": "ceo",
        "hospital": "Mackenzie Health",
        "hospital_aliases": ["MH"],
        "name": "Mary-Agnes Wilson",
        "role": "Interim President and CEO (outgoing)",
        "date": "2026-04-13",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    },
    {
        "item_id": "C131",
        "task": "ceo",
        "hospital": "Mackenzie Health",
        "hospital_aliases": ["MH"],
        "name": "Stav D'Andrea",
        "role": "VP People Services & CHRO",
        "date": "2026-02",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "B - approximate month"
    },
    {
        "item_id": "C132",
        "task": "ceo",
        "hospital": "Mackenzie Health",
        "hospital_aliases": ["MH"],
        "name": "Marissa Salmon",
        "role": "Interim CHRO",
        "date": "2026-04-13",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    },
    {
        "item_id": "C133",
        "task": "ceo",
        "hospital": "Mackenzie Health",
        "hospital_aliases": ["MH"],
        "name": "David Stolte",
        "role": "Interim VP People Services",
        "date": "2026-04-13",
        "source": "LLM Discovery Verified",
        "in_scope": True,
        "status": "ADDED FROM LLM AUDIT",
        "confidence_tier": "A - dated announcement"
    }
]

gold_data.extend(new_entries)

with open(gold_file, 'w', encoding='utf-8') as f:
    json.dump(gold_data, f, indent=4)

# 2. Update gold.xlsx using pandas
df = pd.DataFrame(gold_data)
# Convert hospital_aliases list to string for Excel
df['hospital_aliases'] = df['hospital_aliases'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
df.to_excel('gold.xlsx', index=False)

print("Updated gold_llm.json and gold.xlsx successfully.")
