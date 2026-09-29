# Enhanced Prompts — Hospital Leadership Change Task

## Why the Original Prompt Under-Performed

By studying all 5 raw model responses against the 16-item gold dataset, the evaluation identified these repeating failure modes:

| Failure Mode | Who Failed | Root Cause |
|---|---|---|
| Missed named Board Governors (Nichol, Dick, Roberts, Stevens) | Claude, Gemini, Perplexity, Copilot | AGM appointments have no press release; models only searched newsrooms |
| Missed Jeremy Stevenson departure | ChatGPT | Collapsed into background prose instead of a separate row |
| Missed Mary-Agnes Wilson outgoing interim | All except Copilot | Reported only the incoming CEO; never asked "who left?" |
| Missed CHRO-level transitions (Stav D'Andrea) | All except ChatGPT | Original prompt says "leadership, CEO and board" — models excluded VP roles |
| Board recruitment ≠ Board appointment | Gemini, Perplexity, Copilot | Correctly flagged uncertainty but produced zero appointment rows |
| Tier C items (Shah, Fanjoy) missed | All models | Physician governance not seen as in-scope |

> [!NOTE]
> All three prompts below preserve the original output format **exactly** — `Hospital → Issue → Paragraph blurb → Date → Source → Source link` — and keep `[INSERT HOSPITAL]` and the `January 16, 2026 – July 16, 2026` date window unchanged.

---

## PROMPT 1 — Role-Based Persona + Structured Scope Rules
**Strategy**: Adds a role persona and explicit include/exclude ruleset *before* the original task statement  
**Best for**: Any model; most universally applicable  
**Targets**: Scope ambiguity, missed dual events, missed AGM board appointments

```
You are a Senior Governance Intelligence Analyst at Ontario Health, responsible for maintaining an authoritative registry of hospital executive and board-level transitions used for performance management and accountability reporting.

I'm a Chief Regional Officer for Ontario Health, interested in hospital performance management. Provide an exhaustive list of hospital leadership, CEO and board member changes in the [INSERT HOSPITAL] between January 16, 2026 and July 16, 2026, formatted as:
Hospital → Issue → Paragraph blurb → Date → Source → Source link

Before you search, apply these scope rules strictly:

INCLUDE in your search:
• President & CEO — incoming AND outgoing are two SEPARATE rows. Never combine both people into one row.
• Interim / Acting CEO — the start of an interim assignment AND its conclusion are each a separate reportable event
• Board of Directors / Board of Governors — any named individual who joined, departed, changed office (Chair, Vice-Chair, Treasurer, Secretary), or was reappointed — even if the only evidence is an updated board roster page, LinkedIn post, or recruitment firm announcement rather than a press release
• C-Suite roles reporting directly to the CEO: CFO, CNO, CHRO/VP HR, CMO, Chief of Staff, Chief Communications Officer, Chief Planning Officer
• President, Medical Staff Association

EXCLUDE:
• Foundation board or Foundation executive roles (unless the person also holds a hospital governance seat)
• Board recruitment/vacancy postings that did not produce a confirmed named appointment by July 16, 2026
• Appointments announced AND effective before January 16, 2026

CRITICAL — Board AGM Appointments:
Most Ontario hospitals hold their AGM in June. AGM board appointments are rarely announced by standalone press release. You MUST check: (a) the hospital's current board roster page for any name that appears new vs. 2025, (b) LinkedIn announcements by the appointee, (c) recruitment firm sites (Boyden, Mirams Becker, Odgers Berndtson). Report any named individual confirmed through any of these sources.

CRITICAL — Dual-Event Rule:
Every CEO or interim leadership transition produces at least TWO rows: one for the outgoing person's last day, one for the incoming person's first day. Never write a single row mentioning both people.

After each row, append one confidence tag:
[CONFIRMED — dated primary source] | [PROBABLE — roster/LinkedIn/recruitment firm only] | [UNCONFIRMED — secondary source only]

If a scope category has zero changes, write explicitly: "No [Category] changes located for this period" — do not silently omit the section.
```

---

## PROMPT 2 — Chain-of-Thought Reasoning + Few-Shot Examples
**Strategy**: Step-by-step CoT scaffold + 2 correct worked examples + 1 negative example  
**Best for**: Models that over-filter or collapse multiple events (Perplexity, Gemini)  
**Targets**: Missed named board governors, collapsed dual events, recruitment ≠ appointment confusion

```
I'm a Chief Regional Officer for Ontario Health, interested in hospital performance management. Provide an exhaustive list of hospital leadership, CEO and board member changes in the [INSERT HOSPITAL] between January 16, 2026 and July 16, 2026, formatted as:
Hospital → Issue → Paragraph blurb → Date → Source → Source link

Before writing your final answer, work through this reasoning chain step by step:

STEP 1 — MAP ALL LEADERSHIP TIERS
List every tier that could have changes: permanent CEO, interim CEO, acting CEO, direct-report C-Suite VP roles, Board of Directors/Governors, Medical Staff Association President. For each tier, note whether this hospital typically announces changes by press release or only reflects them in board roster updates or AGM minutes.

STEP 2 — SEARCH BY EVIDENCE TYPE, NOT JUST PRESS RELEASES
For each tier, check these sources in order:
  (a) Hospital newsroom / press releases
  (b) Hospital board roster / leadership page — look for names new or absent vs. late 2025
  (c) LinkedIn posts by the executive (search: "[name] + [hospital] + appointed/joined/honoured")
  (d) Recruitment firm announcements (Boyden, Mirams Becker, Odgers Berndtson, KPMG Executive)
  (e) AGM notices and published board minutes

STEP 3 — APPLY THE DUAL-EVENT TEST
For every incoming appointment you find, ask: "Who held this role immediately before? Did their departure or conclusion of interim duty also fall within January 16 – July 16, 2026?" If yes, add a SECOND separate row for that outgoing person.

STEP 4 — APPLY THE NAMED-INDIVIDUAL STANDARD
A change is reportable only if it names a specific individual. A recruitment notice for "two governors" is NOT a change row. Only add a row once you can name the person.

STEP 5 — WRITE YOUR OUTPUT using the format: Hospital → Issue → Paragraph blurb → Date → Source → Source link

---
WORKED EXAMPLE A — correct: dual-event handling

Mackenzie Health → Interim President and CEO concluded — Mary-Agnes Wilson → Mary-Agnes Wilson served as Mackenzie Health's Interim President and CEO from July 2025 following Altaf Stationwala's departure. Her interim assignment concluded April 13, 2026 when Carmine Stumpo assumed the permanent CEO role. For performance management, the conclusion of an interim CEO arrangement is a distinct governance event: it closes an accountability-gap period and resets the CEO-performance monitoring baseline. → 2026-04-13 → Mackenzie Health, "Announcing Mackenzie Health's new President and CEO" → https://www.mackenziehealth.ca/...
[CONFIRMED — dated primary source]

Mackenzie Health → President and CEO appointed — Carmine Stumpo → Carmine Stumpo joined as President and CEO on April 13, 2026, following a national search, coming from Orillia Soldiers' Memorial Hospital. His appointment restores permanent CEO accountability and initiates a new strategic mandate period for performance monitoring baselines. → 2026-04-13 → Mackenzie Health, "Announcing Mackenzie Health's new President and CEO" → https://www.mackenziehealth.ca/...
[CONFIRMED — dated primary source]

---
WORKED EXAMPLE B — correct: board appointment without press release

North York General Hospital → Board Governor appointed — Dr. Kathryn Nichol → Dr. Kathryn Nichol, President and CEO of VHA Home HealthCare, joined the NYGH Board of Governors in June 2026 as part of the hospital's annual governance renewal. Her appointment was not announced by NYGH press release but was confirmed publicly by recruitment firm Mirams Becker and on LinkedIn. Named board appointments represent a change in the composition of the accountability body overseeing hospital performance. → 2026-06 → Mirams Becker appointment announcement; Dr. Nichol LinkedIn post → [URL]
[CONFIRMED — recruitment firm and LinkedIn corroboration]

---
WORKED EXAMPLE C — INCORRECT — do not do this

❌ North York General Hospital → Board of Governors recruitment — two new governors sought → NYGH publicly sought two Board Governors for the board year commencing June 2026... → February 24, 2026

WHY THIS IS WRONG: This is a recruitment notice, not a named appointment. Do not include it as a change row. Only add a row once you can name the appointed individual.
---

Now apply this reasoning chain to [INSERT HOSPITAL] and produce your output.
```

---

## PROMPT 3 — Completeness Checklist + Recall-First Directive
**Strategy**: Explicit checklist forcing all 6 scope categories + recall-maximising instruction  
**Best for**: Models with high precision / low recall (ChatGPT achieved 100% precision but only 43.8% recall)  
**Targets**: Recall uplift — ensures every scope category is checked and explicitly declared

```
I'm a Chief Regional Officer for Ontario Health, interested in hospital performance management. Provide an exhaustive list of hospital leadership, CEO and board member changes in the [INSERT HOSPITAL] between January 16, 2026 and July 16, 2026, formatted as:
Hospital → Issue → Paragraph blurb → Date → Source → Source link

IMPORTANT — PRIORITISE COMPLETENESS:
I need maximum recall. Include every verifiable change even if the only evidence is a board roster update, a LinkedIn post, or a recruitment firm announcement with no hospital press release. Flag confidence level on each row rather than omitting uncertain items.

Before writing your final output, complete this checklist and mark every item:

☐ CEO (permanent) — incoming AND outgoing as separate rows
☐ Interim CEO — start of interim assignment AND end of interim assignment as separate rows
☐ Acting CEO — any bridge period, even described as "a few weeks", as its own row
☐ C-Suite / VP roles reporting to CEO (CFO, CNO, CHRO/VP HR, CMO, Chief of Staff, Chief Communications Officer, Chief Planning Officer) — any person who started, ended, or moved to interim status during the window
☐ Board of Directors / Governors — any NAMED individual who joined, departed, changed board office (Chair/Vice-Chair/Treasurer/Secretary), or was reappointed; check board roster page, AGM minutes, LinkedIn, and recruitment firm sites — do not rely on press releases alone
☐ Medical Staff Association President or equivalent physician governance lead

For each checklist item, write one of:
  FOUND: [name, role, date]
  NOT FOUND — sources checked: [list sources]
  UNCERTAIN — [describe evidence seen but not confirmable to a named individual]

SCOPE RULES:
• Foundation board/executive roles: EXCLUDE unless the individual simultaneously holds a hospital board seat
• Board recruitment notice with no named appointee by July 16, 2026: do NOT add a row; mark UNCERTAIN in checklist
• If the hospital held its AGM in the window (most Ontario hospitals hold AGMs in June), treat as high-probability of board composition change — actively search for the outcome before writing NOT FOUND

CONFIDENCE TAGS — add after every output row:
[A — confirmed by dated primary source]
[B — confirmed by secondary source: LinkedIn / recruitment firm / media]
[C — inferred from roster comparison; no dated announcement found]

FINAL CHECK before submitting:
Count your output rows. If you have fewer than 2 rows for a hospital where a CEO transition occurred, review your checklist — you are very likely missing the outgoing person's departure row or the conclusion of an interim assignment.
```

---

## At-a-Glance Comparison

| Improvement | Prompt 1 | Prompt 2 | Prompt 3 |
|---|:---:|:---:|:---:|
| Original format preserved | ✅ | ✅ | ✅ |
| `[INSERT HOSPITAL]` placeholder preserved | ✅ | ✅ | ✅ |
| `Jan 16 – Jul 16, 2026` date window preserved | ✅ | ✅ | ✅ |
| Dual-event rule (outgoing + incoming separately) | ✅ | ✅ Example A | ✅ |
| Named board governors via AGM/LinkedIn/firm | ✅ | ✅ Example B | ✅ |
| Blocks recruitment notice as a change row | ✅ | ✅ Example C | ✅ |
| CHRO/VP scope explicitly included | ✅ | ✅ Step 1 | ✅ |
| Physician governance (MSA President) included | ✅ | ✅ Step 1 | ✅ |
| Recall-first / completeness-first directive | — | ✅ Evidence types | ✅ Explicit |
| Confidence tagging for auditability | ✅ | ✅ | ✅ |
