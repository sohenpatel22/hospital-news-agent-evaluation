# Gold Standard Dataset — Hospital News Agent Evaluation
### Ontario Health / MOH-OH Oversight Dashboard — Agent vs. LLM Benchmark

**Prepared by:** Sohen Patel | **Methodology:** Independent, registry/primary-source-anchored gold sets, built blind to tool outputs, cross-checked against Wendy's team's prior analysis where available.

---

## Methodology Notes (read before using this dataset)

1. **Independence from the Agent.** Unlike Wendy's team's original comparison (which used the Agent's own output as the reference standard — a circular method that structurally cannot detect the Agent's own omissions), this gold set is built from independent, authoritative sources: the IPC decisions database, Ontario Orders in Council, and hospital primary-source documents (annual reports, AGM minutes, official press releases).
2. **Fixed reference date.** To avoid a moving "last N months/years" target, all windows are anchored to **July 16, 2026** (the date Wendy's team's investigation materials were shared) rather than the live current date. When you run prompts against agents/LLMs, either (a) rewrite the prompt to state this window as explicit absolute dates, or (b) accept that live tools' outputs may include events after this date and score accordingly.
3. **Confidence tiers matter.** Not everything in this dataset carries equal evidentiary weight. Each section notes its confidence basis. Treat a "confirmed zero" (verified via exhaustive registry search) very differently from a "no news found" negative (absence of press coverage — weaker evidence).
4. **A note on process, for the write-up.** Two attempts to close remaining gaps via a second LLM produced one confirmed fabrication (an invented WRH board roster + citation) and one case where the underlying facts were accurate but the cited source was invented and never verified. Recommend citing this as a finding: even to build a *reference* dataset, ungrounded LLM output must be independently verified before use — the same standard the whole project applies to the tools under test.

---

## TASK 1 — PHIPA Identification

**Window:** 2026-01-16 to 2026-07-16 | **Source:** IPC Advanced Decisions Search (decisions.ipc.on.ca) | **Scope rule:** PHIPA correction requests (s.55) excluded, per Wendy's team's established precedent

### In-scope items

| Hospital | Issue | Blurb | Date | Source |
|---|---|---|---|---|
| The Ottawa Hospital | Access dispute — EMR screenshots | Patient sought screenshots/"samples" of 25 items from her Epic EMR record; hospital offered printed copies but not screenshots. Adjudicator confirmed a right of access in principle but dismissed the complaint since the hospital doesn't create or retain screenshots. | 2026-06-25 | IPC — PHIPA Decision 340 |
| The Ottawa Hospital | Access dispute — records re: unnotified care meeting | Substitute decision-maker sought records of an undisclosed meeting between hospital staff and the Ministry of Health about his son's care. Adjudicator found the hospital's search inadequate and ordered a further search. | 2026-04-29 | IPC — PO-4820 (confirmed independently by Wendy's team) |
| Hamilton Health Sciences | Access dispute — child's full medical records | Parents sought their child's complete medical records; hospital's search was too narrow by its own admission. Adjudicator ordered a fresh, hospital-wide search. | 2026-05-13 | IPC — PHIPA Decision 338 (confirmed independently by Wendy's team) |
| Hamilton Health Sciences | Access dispute — pediatric-death review records (merged: PO-4849, PO-4850, PO-4851-F — same underlying event, 3 procedural appeal numbers) | Journalist sought internal/external review records into two pediatric deaths after tonsil/adenoid surgery. Hospital withheld under FIPPA's quality-of-care exemption; IPC upheld the exemption across all three appeals. | 2026-06-17 | IPC — PO-4849, PO-4850, PO-4851-F |

### Excluded — correction requests (matches Wendy's team's own exclusion pattern)
| Hospital | Issue | Date | Source |
|---|---|---|---|
| William Osler Health System | Correction request re: physician report | 2026-05-05 | PHIPA Decision 336 |
| The Ottawa Hospital | Correction request re: after-visit summary | 2026-01-26 | PHIPA Decision 326 (independently confirmed by Wendy's team's exclusion) |

### Excluded — false-positive keyword hits (verified as unrelated)
- **PO-4833**: custodian = Ministry of the AG (SIU case); named hospital = Queensway Carleton, a separate corporate entity from Ottawa Hospital
- **PO-4795**: custodian = University of Windsor; "Ottawa" appears only in a cited precedent

### Confirmed zero (registry search returned 0 results)
Anson General Hospital · Geraldton District Hospital · Baycrest Health Sciences

**Net gold set: 4 in-scope items, 2 hospitals; 4 hospitals at true zero.**

---

## TASK 3 — Interim Supervisors

**Window:** 2021-07-16 to 2026-07-16 (5-year, per prompt text) | **Source:** Orders in Council (ontario.ca) | **Scope:** includes both Public Hospitals Act s.9 (supervisor) and s.8 (investigator) appointments — **flagged as an open scope question for Wendy's team**, since their own table implicitly excludes investigators

| Hospital | Person | Role | Appointed | Ended | Source |
|---|---|---|---|---|---|
| Stevenson Memorial | **Janice Skot** *(flagged — investigator, not supervisor)* | Investigator (s.8) | 2024-02-01 | 2024-07-26 (sunset clause) | OC 195/2024 |
| Stevenson Memorial | Eric Hanna | Supervisor (s.9) | 2024-09-26 | 2025-06-08 | OC 1271/2024 → OC 767/2025 |
| Stevenson Memorial | Carmine Stumpo | Supervisor (s.9) | 2025-06-09 | active | OC 767/2025 |
| Renfrew Victoria | Altaf Stationwala | Supervisor (s.9) | **2026-06-26** *(verified via OIC primary text — Wendy's team's table states Jul 8, 2024, a confirmed discrepancy; OIC is authoritative)* | 2025-06-20 | OC 886/2024 → OC 766/2025 |
| London Health Sciences | David Musyj | Supervisor (s.9) | 2024-09-24 | active (mandate extended, OC 105/2026) | OC 1219/2024, OC 105/2026 |

**Confirmed zero:** Sault Area Hospital · Sante Manitouwadge Health · Sinai Health System (registry search + independent web search corroboration)

**Notes:**
- Discrepancy flagged for Wendy's team: Stationwala's effective date (their table: Jul 8, 2024; OIC 886/2024: Jun 26, 2024).
- Investigator inclusion is a deliberate scope expansion beyond the team's own precedent — confirm before final use.
- Since the prompt asks for appointments "in the last 5 years" (not "currently serving"), listing a since-ended appointment (e.g., Stationwala) is factually correct — score tools as *incomplete* if they omit historical appointees, not merely "stale."

---

## TASK 2 — CEO / Leadership / Board Changes

**Window:** 2021-07-16 to 2026-07-16 | **In-scope:** President/CEO, Board Chair, Vice Chair, Treasurer, Governors/Directors | **Out-of-scope (per Wendy's team's explicit ruling):** C-suite executives (CFO, COO, CNE, Chief of Staff, CMIO, VP-level roles), Foundation leadership | **Date columns:** Announced = publicly stated; Effective = when the change took effect. "Not confirmed" where genuinely unavailable — do not treat as a negative.

### CENTRAL: Mackenzie Health

| Person | Role | Change | Announced | Effective | Source |
|---|---|---|---|---|---|
| Fay Lim-Lambie | Board Chair | incoming | — | AGM Jun 15, 2023 | Wendy's team (Agent data) |
| Stephanie Zee | Board Vice Chair | incoming | — | AGM Jun 15, 2023 | Wendy's team (Agent data) |
| Joby McKenzie | Board 2nd VP Chair | incoming | — | AGM Jun 15, 2023 | Wendy's team (Agent data) |
| Stephanie Zee | Board Chair | incoming (from VP) | — | AGM Jun 13, 2024 | Wendy's team (Agent data) |
| Ruby Philip-Katyal | Board VP Chair | incoming | — | AGM Jun 13, 2024 | Wendy's team (Agent data) |
| Joby McKenzie | Board VP Chair | incoming | — | AGM Jun 13, 2024 | Wendy's team (Agent data) |
| Altaf Stationwala | President/CEO | outgoing, after 14 yrs | late Mar 2025 | Jun 27, 2025 | Mackenzie Health news, Canadian Healthcare Technology |
| Mary-Agnes Wilson | Interim President/CEO | incoming | Apr 9, 2025 | ~Jul 2025 | Mackenzie Health news |
| Stephanie Zee | Board Chair | outgoing | — | AGM Jun 19, 2025 | Wendy's team (Agent data) |
| Fay Lim-Lambie, Ruby Philip-Katyal | Board Members | outgoing | — | AGM Jun 19, 2025 | Wendy's team (Agent data) |
| Atul Mehta | Board Treasurer | incoming | — | AGM Jun 19, 2025 | Wendy's team (Agent data) |
| John Fursey | Board Chair | incoming | — | AGM Jun 19, 2025 | Mackenzie Health Insider Jul 2025 |
| Carmine Stumpo | President/CEO | incoming | Dec 10, 2025 | Apr 13, 2026 | Mackenzie Health news, Boyden, Newmarket Today |

*Excluded (out-of-scope, per ruling): Dr. David Rauchwerger (Chief of Staff), Purvi Desai (VP Digital Health/CIO), Nicole McCahon (Foundation CEO — noted in Wendy's team's original PHIPA-comparable "foundation noise" finding).*

### EAST: Arnprior Regional Health

| Person | Role | Change | Announced | Effective | Source |
|---|---|---|---|---|---|
| Eric Hanna | President/CEO | outgoing, retired after 13 yrs | Aug 19, 2021 | Sep 30, 2021 | ARH news |
| Leah Levesque | President/CEO | incoming | Aug 19, 2021 | Oct 1, 2021 | ARH news |
| Beth Ciavaglia | Board Director | incoming | — | AGM Jun 28, 2022 | Wendy's team (Agent data) |
| Richard Holock, Peter Kenny, Borys Koba | Board Directors | incoming | — | Jul 18, 2023 | Wendy's team (Agent data) |
| Leah Levesque | President/CEO | retirement announced | Dec 7, 2023 | **not confirmed** (exact departure date unavailable) | Wendy's team (Agent data) |
| Cathy Jordan | Board Chair | outgoing, after 3-yr term | — | after AGM 2024 | ARH news |
| Oliver Jacob | Board Chair | incoming, 3-yr term to Jun 2027 | Jul 3, 2024 | Jul 3, 2024 | ARH news |
| Jeremy Stevenson | President/CEO | incoming | May 10, 2024 | **not confirmed** (exact start date unavailable — a specific "Aug 18, 2024" claim from a secondary AI source was never traceable to a real citation and is excluded) | ARH news, Boyden, Renfrew Today |
| Jeremy Stevenson | President/CEO | stepped down | — | Jun 2, 2026 | ARH official public statement (primary source, directly confirmed) |
| Raeline McGrath | Acting President/CEO | incoming | — | Jul 9, 2026 | Wendy's team (Agent data) |
| Pierre Noel | Interim President/CEO | incoming | — | Jul 13, 2026 | Wendy's team (Agent data) |

*Excluded (out-of-scope): Judith Gilchrist (VP Long-Term Care), Dr. Kathi Kovacs (Chief of Staff).*

### NORTH EAST: Sensenbrenner Hospital

No CEO or Board Chair turnover identified in-window. France Dallaire confirmed as CEO from at least 2017 through Feb 2026. **Low-confidence negative** — small hospital, thin press coverage; this is an absence-of-evidence finding, not a registry-confirmed zero. Recommend direct confirmation with the hospital if precision matters.

### NORTH WEST: Red Lake Margaret Cochenour Memorial Hospital

*Source: RLMCMH Annual Reports 2022-23, 2023-24, 2024-25, 2025-26 (primary source, directly reviewed)*

**CEO lineage:**
| Person | Change | Date | Source |
|---|---|---|---|
| Angela Bishop | outgoing President/CEO | date not stated | AR 2022-23 |
| Sue LeBeau | outgoing President/CEO (resigned) | Jul 2022 | AR 2022-23 |
| Angela Bishop | Interim President/CEO (1st stint, out of retirement) | 2022 | AR 2022-23 |
| Sumeet Kumar | incoming President/CEO | May 2023 | AR 2022-23, 2023-24 |
| Angela Bishop | Interim President/CEO (2nd stint) | ~2024 ("past two years" per AR 2025-26) | AR 2024-25, 2025-26 |
| Jennifer Lawrance | incoming President/CEO | Jun 26, 2026 | AR 2025-26 |

**Board Chair lineage:**
| Person | Change | Date | Source |
|---|---|---|---|
| Sonia Green | outgoing (resigned) | 2023 | AR 2022-23 |
| John Frostiak | incoming | 2023 | AR 2022-23, 2023-24 |
| Trevor Zhukrovsky | incoming | between AR2023-24 and AR2024-25 (exact date not stated) | AR 2024-25, 2025-26 |

**Board directors — full turnover, 2022-2025:**
| Person | Change | Date | Source |
|---|---|---|---|
| Shawnda Norlock | outgoing | 2023 | AR 2022-23 |
| Trevor Zhukrovsky | incoming (filled Norlock vacancy) | 2023 | AR 2022-23 |
| James Russell | incoming | early 2023 | AR 2023-24 |
| Marshall Dumontier | outgoing | late 2023 | AR 2023-24 |
| Jennifer Sedlacek | incoming | late 2023 | AR 2023-24 |
| James Russell | outgoing | May 2024 | AR 2023-24 |
| Eleanor Vachon | outgoing (completed 10-yr term) | ~2024 | AR 2023-24 |
| Scott Macumber, Donna Williams, Ray Hall, Ursula DeKeyser, Vivian Bruchkowski, Jamie Saulnier | incoming | between AR2023-24 and AR2024-25 | AR 2024-25 |
| Arlene Swanwick | Vice-Chair (from Committee Chair) | by AR2024-25 | AR 2024-25 |

**2025-26 board roster:** unavailable — final AR page is a graphic/image, not extractable text.

*Excluded (out-of-scope): Foundation Chairs (Marion Whitton, Angela Bishop, Madeleine Oakes, Roger Cormier), Auxiliary Presidents (Elsie Everley, Mercedes Hopf, Kathy Robinson).*

### TORONTO: North York General Hospital

| Person | Role | Change | Announced | Effective | Source |
|---|---|---|---|---|---|
| Bert Clark | Board Chair | incoming | — | Jun 14, 2021 | Wendy's team (Perplexity/Claude data) |
| Robert Sankey, Dr. Christine Williams, Toni Rossi | Board Governors | incoming | — | AGM Jun 13, 2022 | Wendy's team (Agent data) |
| Karyn Popovich | President/CEO | retirement announced | Mar 7, 2023 | led until successor named | NYGH news |
| Dr. Everton Gooden | President/CEO | incoming (internal) | Sep 29, 2023 | Dec 1, 2023 | NYGH news, CanHealth |
| Mitch Frazer | Board Chair | incoming | — | AGM Jun 17, 2024 | NYGH news |
| Jonathan Mackey, Gillian Akai, Kristina Fanjoy, George Mavroudis | Board Governors | incoming | — | AGM Jun 17, 2024 | Wendy's team (Claude/Gemini data) |
| Paviter Binning | Board Member | incoming | — | AGM Jun 16, 2025 | NYGH news |
| Sean Cohan, Christine Cruz-Clarke, Ted Garrard, Vince Imerti, Richard So | Board Members | incoming | — | AGM Jun 17, 2025 | Wendy's team (Perplexity data) |
| Simone Atungo | Board Governor | incoming (confirmed via own bio page) | — | **not confirmed** (exact appointment date unavailable) | NYGH board-of-governors page (primary source) |
| Dr. Kathryn Nichol | Board Governor | incoming (confirmed via own bio page) | — | **not confirmed** | NYGH board-of-governors page (primary source) |

*Excluded (out-of-scope): Serda Evren (CCO), Dr. Richard Bowry (VP Medical Affairs), Terri Stuart-McEwan (VP Clinical/CNE), Paul Truscott Jr. (VP Finance/CFO), Jennifer Dockery (VP Quality), Young Lee (outgoing CFO), Peter Wegener (Interim CFO), Dr. Simon Raphael (outgoing Chief of Staff), Dr. Phil Shin (CMIO), Dr. Donna McRitchie (VP Medical/Academic Affairs), Linda Jussaume (Interim CNE), Seanna Millar (NYGH **Foundation** CEO — confirmed distinct governance body from the hospital's own Board of Governors).*

### WEST: Windsor Regional Hospital

*Sources: WRH Annual Reports 2021/22 through 2025/26 (primary source, directly reviewed) + 28th AGM Minutes, Jun 23, 2022 (primary source, directly reviewed)*

**CEO / Acting CEO lineage:**
| Person | Role | Change | Announced | Effective | Source |
|---|---|---|---|---|---|
| David Musyj | President/CEO | seconded (open-ended) to LHSC as acting CEO | May 17, 2024 | May 23, 2024 | CBC, Global News, CanHealth, AR 2023/24 |
| Karen Riddell | Acting President/CEO | incoming (from CNE/COO) | May 17, 2024 | May 23, 2024 | CBC, CanHealth |
| David Musyj | President/CEO (WRH) | confirmed not returning; permanent at LHSC | Jul 16, 2025 | — | CTV, WindsorNewsToday |
| Karen Riddell | President/CEO | retirement announced | — | end of FY2025/26 (per Board Chair letter — "effective for the 2026-27 fiscal year" for successor) | AR 2025/26 (Chair's letter, primary source) |
| Kristin Kennedy | President/CEO | incoming (from Erie Shores HealthCare) | Dec 2025 | FY2026-27 | windsoriteDOTca, am800, Boyden, AR 2025/26 |

**Board Chair lineage:**
| Person | In place per | Source |
|---|---|---|
| Anthony Paniccia | FY2021/22, FY2022/23 | WRH Annual Reports (primary source) |
| Patricia France | FY2023/24, FY2024/25 | WRH Annual Reports (primary source) |
| Ian McLeod | FY2025/26 | WRH Annual Reports (primary source) |

*Exact transition dates between chairs not stated in annual reports — only the fiscal-year-boundary is known.*

**Board of Directors, per 2022 AGM (Jun 23, 2022) — verified baseline from actual minutes:**
- Newly elected (to 2025 AGM): Dr. Laurie Freeman, David Malian, Linda Staudt
- Confirmed (to 2024 AGM): Ian McLeod, Mary Dawson, Anthony Paniccia, Paul Lachance, Laura Copat, Penny Allen, Genevieve Isshak
- Confirmed (to 2023 AGM): Patricia France, Cynthia Bissonnette, Michael Lavoie
- Ex-officio non-voting: David Musyj (President/CEO), Dr. Wassim Saad (Chief of Professional Staff/VP Medical Affairs), Dr. Maher Sabalbal (VP Professional Staff), Dr. Larry Jacobs (President Professional Staff/Assoc. Dean Schulich), Karen Riddell (CNE/COO)
- Chair: Anthony Paniccia
- Departed (completed term): Dan Wilson, after ~13 years on the board

**Board roster 2023-2026:** not available — WRH does not appear to publish AGM minutes or board rosters for these years in a form either the annual reports or public search surfaced. This is a documented, genuine gap.

*Excluded (out-of-scope): Mark Fathers (outgoing CFO, 2022), Dr. Wassim Saad (Chief of Staff — listed here only as ex-officio board context, not as an in-scope leadership change).*

---

## Summary of Genuinely Open Items (not pursued further — diminishing returns / unavailable)

| Item | Status |
|---|---|
| WRH board roster, 2023-2026 | Not publicly available in sources checked |
| NYGH: Simone Atungo, Dr. Kathryn Nichol exact appointment dates | Members confirmed via primary source; exact dates unavailable |
| Arnprior: Levesque exact departure date, Stevenson exact start date | Only announcement dates confirmed; effective dates unavailable |
| Red Lake: 2025-26 board roster | Source exists only as an image/graphic, not extractable |
| Sensenbrenner: CEO stability | Low-confidence negative (absence of press coverage, not a registry check) |

## Key Cross-Entity Pattern (worth noting in final write-up)

David Musyj connects three hospitals across this dataset: Windsor Regional Hospital (Task 2, outgoing CEO), London Health Sciences Centre (Task 3, government-appointed supervisor), and — via his successor Altaf Stationwala's later career — Mackenzie Health (Task 2) and Renfrew Victoria Hospital (Task 3, supervisor). Ontario's hospital-executive and supervisor pools substantially overlap. A strong evaluation tool should track this kind of cross-reference correctly; a weak one is likely to conflate or miss it.
