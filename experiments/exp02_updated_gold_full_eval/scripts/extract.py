"""
Extraction stage mechanics.

This script does NOT call an external LLM API (none is configured in this
environment). Per an explicit decision by the user (2026-08-30), the actual
free-text -> schema-item conversion is performed directly by Claude (acting as
the extraction "LLM") reading each staged text file and writing the
corresponding JSON to /output/extracted/. That is a deliberate, logged
deviation from "script calls API with temperature=0/fixed seed" — see
/output/extracted/_extraction_prompt.txt for the exact rules applied and the
methods-section caveat to disclose in the paper.

This script provides:
  --stage       walk /data/raw, convert every .docx/.txt response to plain
                text, write it to /output/extracted/_staging/, and write a
                manifest.json enumerating every (system, task, hospital,
                run_number, source_file, staged_text_file).
  --validate    validate every /output/extracted/*.json file against
                /schema/extraction_schema.json and print the
                system x task x run summary table (item count, refusal
                count, items with null citation).
"""

import argparse
import json
import os
import re
import sys

try:
    import docx
except ImportError:
    docx = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /eval
RAW_DIR = os.path.join(ROOT, "data", "raw", "Prompt V0")
EXTRACTED_DIR = os.path.join(ROOT, "output", "extracted")
STAGING_DIR = os.path.join(EXTRACTED_DIR, "_staging")
SCHEMA_PATH = os.path.join(ROOT, "schema", "extraction_schema.json")

TASK_FOLDER_TO_TASK = {
    "CEOs": "ceo",
    "PHIPA": "phipa",
    "Interim Supervisor": "supervisor",
}

RUN_FILENAME_RE = re.compile(r"^Run\s*(\d+)\.docx$", re.IGNORECASE)


def read_docx_text(path):
    d = docx.Document(path)
    parts = []
    for para in d.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def sanitize(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def walk_raw():
    """Yield (system, task, hospital, run_number, abs_path) for every
    per-hospital Run N.docx response file under /data/raw/Prompt V0."""
    entries = []
    for task_folder, task in TASK_FOLDER_TO_TASK.items():
        task_dir = os.path.join(RAW_DIR, task_folder)
        if not os.path.isdir(task_dir):
            continue
        for system in sorted(os.listdir(task_dir)):
            system_dir = os.path.join(task_dir, system)
            if not os.path.isdir(system_dir):
                continue
            for hospital in sorted(os.listdir(system_dir)):
                hospital_dir = os.path.join(system_dir, hospital)
                if not os.path.isdir(hospital_dir):
                    continue
                for fname in sorted(os.listdir(hospital_dir)):
                    m = RUN_FILENAME_RE.match(fname)
                    if not m:
                        continue
                    run_number = int(m.group(1))
                    entries.append(
                        {
                            "system": system,
                            "task": task,
                            "hospital": hospital,
                            "run_number": run_number,
                            "source_file": os.path.relpath(
                                os.path.join(hospital_dir, fname), ROOT
                            ),
                            "abs_path": os.path.join(hospital_dir, fname),
                        }
                    )
    return entries


def stage():
    if docx is None:
        print("ERROR: python-docx not installed. pip install python-docx")
        sys.exit(1)

    os.makedirs(STAGING_DIR, exist_ok=True)
    entries = walk_raw()
    manifest = []
    for e in entries:
        text = read_docx_text(e["abs_path"])
        staged_name = (
            f"{sanitize(e['task'])}__{sanitize(e['system'])}__"
            f"{sanitize(e['hospital'])}__run{e['run_number']}.txt"
        )
        staged_path = os.path.join(STAGING_DIR, staged_name)
        with open(staged_path, "w", encoding="utf-8") as f:
            f.write(text)
        manifest.append(
            {
                **{k: v for k, v in e.items() if k != "abs_path"},
                "staged_text_file": os.path.relpath(staged_path, ROOT),
                "expected_output_json": os.path.relpath(
                    os.path.join(
                        EXTRACTED_DIR,
                        staged_name.replace(".txt", ".json"),
                    ),
                    ROOT,
                ),
            }
        )

    manifest_path = os.path.join(EXTRACTED_DIR, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Staged {len(manifest)} raw response files to {STAGING_DIR}")
    print(f"Manifest written to {manifest_path}")

    by_task = {}
    for e in manifest:
        by_task.setdefault(e["task"], set()).add(e["system"])
    for task, systems in by_task.items():
        print(f"  task={task}: systems={sorted(systems)}")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_item(item, item_schema, errors, context):
    required = item_schema["required"]
    for field in required:
        if field not in item:
            errors.append(f"{context}: missing required field '{field}'")
    allowed = set(item_schema["properties"].keys())
    for field in item:
        if field not in allowed:
            errors.append(f"{context}: unexpected field '{field}'")
    if "direction" in item and item["direction"] not in ("incoming", "outgoing", "unclear"):
        errors.append(f"{context}: invalid direction '{item.get('direction')}'")
    dn = item.get("date_normalised")
    if dn is not None and not re.match(r"^(\d{4}-\d{2}-\d{2}|\d{4}-\d{2}|\d{4})$", dn):
        errors.append(f"{context}: invalid date_normalised '{dn}'")


def validate():
    schema = load_schema()
    item_schema = schema
    file_schema = schema["file_level_schema"]

    files = [
        f
        for f in sorted(os.listdir(EXTRACTED_DIR))
        if f.endswith(".json") and not f.startswith("_")
    ]
    if not files:
        print(f"No extracted JSON files found in {EXTRACTED_DIR}")
        return

    errors = []
    rows = []  # (system, task, run, hospital, item_count, refusal_count, null_citation_count)

    for fname in files:
        fpath = os.path.join(EXTRACTED_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        for field in file_schema["required"]:
            if field not in data:
                errors.append(f"{fname}: missing required file-level field '{field}'")

        items = data.get("items", [])
        refusals = data.get("refusals", [])
        null_citations = 0
        for idx, item in enumerate(items):
            validate_item(item, item_schema, errors, f"{fname}[{idx}]")
            if item.get("citation_url") is None:
                null_citations += 1

        rows.append(
            (
                data.get("system", "?"),
                data.get("task", "?"),
                data.get("run_number", "?"),
                data.get("hospital", "?"),
                len(items),
                len(refusals),
                null_citations,
            )
        )

    if errors:
        print(f"=== {len(errors)} SCHEMA VALIDATION ERRORS ===")
        for e in errors[:200]:
            print(f"  {e}")
        if len(errors) > 200:
            print(f"  ... and {len(errors) - 200} more")
    else:
        print("All extracted files pass schema validation.")

    print("\n=== system x task x run -> item count / refusal count / null-citation count ===")
    agg = {}
    for system, task, run, hospital, n_items, n_ref, n_null in rows:
        key = (system, task, run)
        a = agg.setdefault(key, [0, 0, 0])
        a[0] += n_items
        a[1] += n_ref
        a[2] += n_null

    header = f"{'system':<18} {'task':<12} {'run':<5} {'items':<7} {'refusals':<10} {'null_citation':<14}"
    print(header)
    print("-" * len(header))
    for (system, task, run), (n_items, n_ref, n_null) in sorted(agg.items()):
        print(f"{system:<18} {task:<12} {run:<5} {n_items:<7} {n_ref:<10} {n_null:<14}")

    totals_items = sum(a[0] for a in agg.values())
    totals_ref = sum(a[1] for a in agg.values())
    totals_null = sum(a[2] for a in agg.values())
    print("-" * len(header))
    print(f"{'TOTAL':<18} {'':<12} {'':<5} {totals_items:<7} {totals_ref:<10} {totals_null:<14}")

    print(f"\nFiles processed: {len(files)} / manifest expects: ", end="")
    manifest_path = os.path.join(EXTRACTED_DIR, "_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        print(len(manifest))
        expected_names = {os.path.basename(m["expected_output_json"]) for m in manifest}
        actual_names = set(files)
        missing = expected_names - actual_names
        if missing:
            print(f"MISSING extraction outputs ({len(missing)}):")
            for m in sorted(missing):
                print(f"  {m}")
    else:
        print("? (no manifest found)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true", help="Convert raw docx/txt to staged plain text + manifest")
    parser.add_argument("--validate", action="store_true", help="Validate extracted JSON + print summary table")
    args = parser.parse_args()

    if not args.stage and not args.validate:
        parser.print_help()
        sys.exit(1)

    if args.stage:
        stage()
    if args.validate:
        validate()
