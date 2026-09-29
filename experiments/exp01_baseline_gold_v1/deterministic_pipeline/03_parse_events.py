import os
import pandas as pd
import re
import csv

def parse_events():
    print("--- Phase 4: Structured Event Extraction ---")
    
    input_file = "raw_outputs/raw_outputs.csv"
    out_dir = "structured_outputs"
    os.makedirs(out_dir, exist_ok=True)
    
    df_raw = pd.read_csv(input_file)
    parsed_events = []
    
    # Common negatives
    negatives = [
        r"no items found",
        r"no publicly available",
        r"could not find any",
        r"did not find any",
        r"no relevant information",
        r"identified no phipa-related",
        r"no recent phipa",
        r"no phipa decisions",
        r"found no phipa",
        r"does not appear to be any publicly reported",
        r"no records of any",
        r"none fall within",
        r"no supervisor/investigator",
        r"no interim supervisor",
        r"no results",
        r"zero events"
    ]
    neg_pattern = re.compile('|'.join(negatives), re.IGNORECASE)
    
    for idx, row in df_raw.iterrows():
        raw_text = str(row['raw_text'])
        lines = raw_text.split('\n')
        
        events_found_for_doc = False
        
        # 1. Look for table format
        # The Copilot Agent uses: Hospital | Issue | Paragraph blurb | Date | Source | Source link
        # BUT the "Hospital" column often contains "Hospital Name → Person Name"
        # We must extract the person name from there for supervisor/ceo tasks.
        in_table = False
        headers = []
        for line in lines:
            if 'Hospital | Issue' in line or 'Hospital | Person' in line:
                in_table = True
                headers = [h.strip().lower() for h in line.split('|')]
                continue
                
            if in_table:
                if '|' not in line or len(line.strip()) < 5:
                    in_table = False
                    continue
                    
                cells = [c.strip() for c in line.split('|')]
                if len(cells) < 3:
                    continue
                    
                if all(c.startswith('-') for c in cells if c):
                    continue
                    
                hospital_cell = cells[0] if len(cells) > 0 else ""
                issue_cell = cells[1] if len(cells) > 1 else ""
                date = ""
                source = ""
                link = ""
                
                if len(cells) == len(headers):
                    for i, h in enumerate(headers):
                        if 'date' in h: date = cells[i]
                        elif 'source' in h and 'link' not in h: source = cells[i]
                        elif 'link' in h or 'url' in h: link = cells[i]
                else:
                    if len(cells) >= 4: date = cells[3]
                    if len(cells) >= 5: source = cells[4]
                    if len(cells) >= 6: link = cells[5]
                
                # KEY FIX: For supervisor/ceo tasks, the hospital cell often contains
                # "Hospital Name → Person Name" or "Hospital Name → Person Name, Role"
                # Extract the person name after the arrow as the primary name_or_issue.
                person_name = ""
                arrow_match = re.search(r'[→\->]+\s*(.+)', hospital_cell)
                if arrow_match:
                    person_name = arrow_match.group(1).strip()
                    # Strip trailing role info like ", Supervisor" if too long
                    person_name = re.sub(r',\s*(Supervisor|Interim|Acting|CEO|President).*$', '', person_name, flags=re.IGNORECASE).strip()
                
                # Use person_name as name_or_issue if we found one; else use issue column
                name_or_issue = person_name if person_name else issue_cell.strip()
                
                if name_or_issue:
                    parsed_events.append({
                        'task': row['task'],
                        'model': row['model'],
                        'hospital_eval': row['hospital'],
                        'run_number': row['run_number'],
                        'extracted_hospital': hospital_cell,
                        'name_or_issue': name_or_issue,
                        'date': date,
                        'source': source,
                        'link': link
                    })
                    events_found_for_doc = True


        # 2. Labelled-field block format (used by Gemini, some Claude outputs):
        # "Record N\nHospital: ...\nIssue: ...\nParagraph blurb: ...\nDate: ...\nSource: ...\nSource link: ..."
        if not events_found_for_doc:
            # Split on "Record N" or numbered headings
            record_blocks = re.split(r'(?:Record\s+\d+|^\d+\.\s)', raw_text, flags=re.IGNORECASE | re.MULTILINE)
            for block in record_blocks:
                # Extract labelled fields
                hosp_m = re.search(r'Hospital\s*:\s*(.+)', block, re.IGNORECASE)
                issue_m = re.search(r'Issue\s*:\s*(.+)', block, re.IGNORECASE)
                date_m = re.search(r'Date\s*:\s*(.+)', block, re.IGNORECASE)
                source_m = re.search(r'(?:Source link|Source)\s*:\s*(.+)', block, re.IGNORECASE)
                
                if not (hosp_m or issue_m):
                    continue
                    
                extracted_hosp = hosp_m.group(1).strip() if hosp_m else ""
                extracted_issue = issue_m.group(1).strip() if issue_m else ""
                extracted_date = date_m.group(1).strip() if date_m else ""
                extracted_source = source_m.group(1).strip() if source_m else ""
                
                # For CEO/supervisor tasks: try to pull person name from blurb or issue
                # Look for "appointed [Person Name]" or "named [Person Name]" patterns
                name_from_blurb = ""
                blurb_m = re.search(r'Paragraph blurb\s*:\s*(.+?)(?=\nDate|\nSource|$)', block, re.IGNORECASE | re.DOTALL)
                blurb_text = blurb_m.group(1).strip() if blurb_m else ""
                
                # Extract capitalized names (e.g., "Eric Hanna", "David Musyj")
                name_match = re.search(r'appointed\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', blurb_text)
                if name_match:
                    name_from_blurb = name_match.group(1)
                
                # Use person name if found (more useful for matching), else use issue
                name_or_issue = name_from_blurb if name_from_blurb else extracted_issue
                
                # Skip if it looks like a "none found" block
                if re.search(r'none|no results|not applicable|n/a|no interim|no supervisor', name_or_issue, re.IGNORECASE):
                    continue
                    
                if name_or_issue and len(name_or_issue) > 3:
                    parsed_events.append({
                        'task': row['task'],
                        'model': row['model'],
                        'hospital_eval': row['hospital'],
                        'run_number': row['run_number'],
                        'extracted_hospital': extracted_hosp or row['hospital'],
                        'name_or_issue': name_or_issue[:200],
                        'date': extracted_date[:50],
                        'source': extracted_source[:100],
                        'link': ""
                    })
                    events_found_for_doc = True

        # 3. Look for paragraph format
        if not events_found_for_doc:
            # Escape hospital name to use in regex
            h_escaped = re.escape(row['hospital'])
            
            # Split by hospital name followed by some separator, or literal "Hospital ->"
            # Some LLMs used "Hospital: Ottawa" or "Ottawa ->" or "1. Ottawa ->"
            pattern = r'(?:Hospital[\s]*[→\->:]|' + h_escaped + r'[\s]*[→\->:])'
            blocks = re.split(pattern, raw_text, flags=re.IGNORECASE)
            
            if len(blocks) > 1:
                for block in blocks[1:]:
                    block_lines = block.split('\n')
                    # the first part up to the next -> is the issue, or "Issue ->"
                    issue_match = ""
                    date_match = ""
                    source_match = ""
                    link_match = ""
                    
                    # Split the block by arrows/delimiters
                    parts = re.split(r'[\s]*[→\->|][\s]*', block)
                    
                    if len(parts) >= 3:
                        # Format is roughly: Issue -> Blurb -> Date -> Source -> Link
                        # If the block started with "Hospital -> [name]", parts[0] might be the hospital name
                        # Let's clean up
                        issue_idx = 0
                        if h_escaped.lower() in parts[0].lower():
                            issue_idx = 1
                            
                        issue_match = parts[issue_idx] if issue_idx < len(parts) else ""
                        
                        # Date is usually the 3rd or 4th item
                        for p in parts:
                            if re.search(r'\b(202[1-6]|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', p):
                                if not date_match and len(p) < 40:
                                    date_match = p
                            if 'http' in p or 'www' in p:
                                link_match = p
                                
                    if not issue_match:
                        # Fallback to keyword matching
                        im = re.search(r'Issue[\s]*[→\->:](.*?)(?:\n|Date|Source|Paragraph|→)', block, re.IGNORECASE | re.DOTALL)
                        if im: issue_match = im.group(1).strip()
                        
                        dm = re.search(r'Date[\s]*[→\->:](.*?)(?:\n|Source|Link|Paragraph|→)', block, re.IGNORECASE | re.DOTALL)
                        if dm: date_match = dm.group(1).strip()
                        
                        sm = re.search(r'Source[\s]*[→\->:](.*?)(?:\n|Source link|Link|Paragraph|→)', block, re.IGNORECASE | re.DOTALL)
                        source_match = sm.group(1).strip() if sm else ""
                        
                        lm = re.search(r'(?:Source link|Link)[\s]*[→\->:](.*?)(?:\n|$)', block, re.IGNORECASE | re.DOTALL)
                        link_match = lm.group(1).strip() if lm else ""

                    # Even simpler fallback: just take the first line as the issue if we have parts
                    if not issue_match and len(parts) > 1:
                        issue_match = parts[0]

                    if issue_match and len(issue_match) > 3:
                        parsed_events.append({
                            'task': row['task'],
                            'model': row['model'],
                            'hospital_eval': row['hospital'],
                            'run_number': row['run_number'],
                            'extracted_hospital': row['hospital'],
                            'name_or_issue': issue_match[:200],
                            'date': date_match[:50],
                            'source': source_match[:100],
                            'link': link_match[:200]
                        })
                        events_found_for_doc = True
        
        # 3. Detect negative / zero findings
        if not events_found_for_doc:
            if neg_pattern.search(raw_text):
                parsed_events.append({
                    'task': row['task'],
                    'model': row['model'],
                    'hospital_eval': row['hospital'],
                    'run_number': row['run_number'],
                    'extracted_hospital': 'NONE FOUND',
                    'name_or_issue': 'NONE FOUND',
                    'date': '',
                    'source': '',
                    'link': ''
                })
            else:
                parsed_events.append({
                    'task': row['task'],
                    'model': row['model'],
                    'hospital_eval': row['hospital'],
                    'run_number': row['run_number'],
                    'extracted_hospital': 'UNPARSABLE',
                    'name_or_issue': raw_text[:100].replace('\n', ' '),
                    'date': '',
                    'source': '',
                    'link': ''
                })

    df_parsed = pd.DataFrame(parsed_events)
    out_file = os.path.join(out_dir, 'all_predictions.csv')
    df_parsed.to_csv(out_file, index=False)
    print(f"Extracted {len(df_parsed)} events.")
    
    print("\nExtraction Audit Summary:")
    print(df_parsed['model'].value_counts())
    
    unparsable = df_parsed[df_parsed['extracted_hospital'] == 'UNPARSABLE']
    if not unparsable.empty:
        print(f"\nWARNING: {len(unparsable)} documents were unparsable.")
    else:
        print("\nPASS: All documents were parsed successfully (events or NONE FOUND).")
        
    print(f"\nSaved to {out_file}")

if __name__ == "__main__":
    parse_events()
