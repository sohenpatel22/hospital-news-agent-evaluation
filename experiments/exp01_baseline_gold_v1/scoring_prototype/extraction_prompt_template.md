# Extraction Prompt Template

Use this exact prompt (fill in the bracketed metadata) each time you paste a response
document into Gemini (or any LLM) for extraction. Keeping the prompt IDENTICAL every
time is what makes the extraction step trustworthy — you are asking it to reformat,
never to judge correctness.

---

## PROMPT TO PASTE (fill in the 5 bracketed fields, then paste the response text below it)

```
You are a data-extraction assistant. Do NOT judge whether any item is correct,
real, or in-scope. Do NOT add information that isn't in the text. Do NOT skip
any item, even if it looks irrelevant or like "noise."

Extract every distinct item (a person/appointment/decision/event) mentioned in
the response text below into a table with EXACTLY these columns:

hospital | name_or_issue | date | source | link

Rules:
- One row per distinct item. If the same hospital appears with multiple items,
  give each item its own row.
- "name_or_issue": the person's name and role, OR the decision/order name
  (e.g. "PO-4820", "PHIPA Decision 338"), OR a short description if neither
  applies. Keep it close to the source wording.
- "date": copy exactly as written in the text (do not reformat or guess).
  Write NONE if no date is given for that item.
- "source": the named source (e.g. "Ontario.ca Order in Council", "CBC",
  hospital name) if stated. Write NONE if not stated.
- "link": the URL if one is given. Write NONE if not given.
- If the response says "no items found" for a hospital, still include ONE row
  for that hospital with name_or_issue = "NONE FOUND" and all other fields NONE.
- Output ONLY the table, no commentary, no summary, no markdown headers.

Metadata for this batch (repeat these values in every row as extra columns):
tool: [ChatGPT / Claude / Gemini / Perplexity / Agent]
task: [phipa / ceo / supervisors]
prompt_version: [wendys_original / v0 / v1 / v2]
run_number: [1-5, or 1 for single-run versions]

Add these 4 metadata values as 4 additional columns at the START of every row,
so each row is:
tool | task | prompt_version | run_number | hospital | name_or_issue | date | source | link

Here is the response text to extract from:

[PASTE THE FULL RESPONSE TEXT HERE]
```

---

## After Gemini returns the table

1. Copy the table rows (not the header, you already have headers) into your
   master `extracted_responses.csv` — same column order every time.
2. Do a 10-second visual scan: does the row count roughly match what you saw
   in the original response? If Gemini silently dropped an item, you'll
   usually notice a hospital with fewer rows than expected.
3. Repeat for every (tool, task, prompt_version, run) file you've saved.

## Why the metadata columns matter

Every row must carry `tool`, `task`, `prompt_version`, and `run_number` because
the scoring script groups and compares by these fields. If you forget to fill
them in for a batch, that batch cannot be scored or compared against anything
else — double check these 4 fields before moving to the next document.
