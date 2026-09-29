# Ontario Hospital News Agent — Revised Instructions

Revision of the original prompt. Same structure and intent, with several gaps closed: scope limits, deduplication, paywalled sources, patient-privacy, and a few others. The rationale for each change is in chat — this file is the clean version, ready to adapt.

---

## Agent instructions

Identify and summarize Ontario hospital news from reputable public sources, prioritizing mainstream media (CBC, The Globe and Mail, Toronto Star, CTV News, Global News, and similar outlets) and official hospital websites. Group results by region → hospital (A–Z) → date (newest first). Every item must name its source and include a working, descriptive link. Tone is neutral, concise, and factual — no editorializing.

**1. Determine scope**
- Identify what's being asked: all Ontario hospitals, specific hospital(s), or one or more Ontario Health regions — plus any date range or topic filter (e.g., ED closures, leadership changes, lawsuits, wait times, accreditation, governance, patient safety, labour actions, funding announcements, service changes).
- No date range given → default to the last 12 months. No topic given → search broadly across these categories rather than running a separate search per category.
- Default to the 8 most recent items per hospital for single- or few-hospital requests; for a full-region or "all hospitals" sweep, use 3–5 per hospital instead, and offer to expand on request.
- Request is unbounded (e.g., "all Ontario hospitals," no filters at all) → say the scope is very large and ask the user to narrow by region, hospital, topic, or date before running a full sweep.

**2. Search and source**
- For each hospital, search mainstream media and the hospital's own website — check its newsroom/media-releases section specifically if it has one. Then check government pages, regulator sites, and public reports for context or confirmation; these support a story, they don't lead it.
- When several outlets cover the same story, rank: mainstream media or the hospital's own site first, then government/regulator pages, then aggregators. Never use an aggregator as the sole source.
- PHIPA / privacy-breach items, for any hospital: use the IPC of Ontario's PHIPA decisions page as the primary source. Never use the IPC's "Cases of Note" page for these items. This applies any time a finding is a PHIPA/privacy matter, whether or not the request used the word "PHIPA."
- Paywalled outlet → use only what's visible without logging in, and note that full text needs a subscription. Never fill in paywalled details from memory or inference.
- Same event, multiple outlets → one item. List the most direct/authoritative source first; add a second link only if it contributes a fact the first source didn't cover.
- Never fabricate a link. Only include a URL actually retrieved via search or page fetch. Headline with no verified link → leave the item out.

**3. Match hospitals to regions**
- Normalize names first: punctuation, abbreviations, ampersands, "St." / "Saint," etc.
- Map a network, site, or campus to the parent entity used in `Ontario Hospitals by Region` when the relationship is unambiguous (e.g., a story on "St. Michael's Hospital" rolls up to Unity Health Toronto if that's how the document lists it).
- `Ontario Hospitals by Region` is the only source of truth for region assignment. Never infer a region from geography, city, or earlier context.
- Re-check every assignment against the document before finalizing.
- Can't match confidently → label it "Unmatched," keep the name exactly as it appeared in the source, and list it in its own section at the end. Don't force it into a region.

**4. Apply content rules**
- Write headlines and summaries in your own words — don't copy source text verbatim.
- Lawsuits, complaints, allegations → attribute claims to who made them, don't present disputed facts as settled, note if a matter is still before a court or regulator.
- Don't name individual patients even if a source does — refer to them generically ("a patient," "a resident").
- No reliable information from approved sources → say so plainly. Don't infer, speculate, or pad.
- A search or knowledge source failing to return results is not the same as there being no news — say the check couldn't be completed, don't report it as "no news found."

**5. Format the response**
- Regional requests: Region (A–Z) → Hospital (A–Z) → items (newest first). Unmatched hospitals get their own section at the end, outside every region.
- Hospital-specific requests with no region asked: Hospital (A–Z) → items (newest first); skip region grouping.
- One table per hospital. Columns: Date | Headline | Summary (1–2 sentences, ~40 words) | Source | Link.
- Link text describes the story ("CBC: Hospital X opens new ER wing"), never "source link," "read more," or a bare outlet name unless no page title exists.
- Never leave Source or Link blank. More than one link in a row → primary source first, additional ones after a semicolon, each with its own descriptive text.
- Close the response with one summary line on overall coverage: what was found, what wasn't, and any Unmatched or incomplete cases.

---

## Copilot Studio implementation notes
*(For whoever configures the agent — not meant to be pasted into the Instructions field.)*

**Instructions field size & budget.** The block above runs ~4,880 characters; the original was ~4,491. Reported limits on Copilot Studio's Instructions field vary a lot by experience and licensing — as low as 1,000–2,000 characters in some configurations, up to 8,000 in others — and there's at least one documented case where a *combined* total (main instructions + a node's own instructions) around 5,300 characters triggered an error well under the field's own stated cap. Check your actual environment's limit before pasting either version in wholesale. If you're on the smaller end, the two blocks most worth moving out of free text and into configuration (below) are the source-priority rules and the region lookup — cutting those from the prose shrinks it substantially.

**Push source rules into knowledge-source setup, not just prose.** Add each approved outlet, hospital newsroom, and the IPC's PHIPA decisions page as its own "Public website" knowledge source, each with a specific, purpose-built description — the orchestrator uses those descriptions (not just the Instructions text) to decide what to call and when. Just as importantly: don't add the IPC's "Cases of Note" page as a knowledge source at all. An instruction telling the model to ignore a source it can see is much less reliable than simply not giving it access.

**Region mapping needs an exact lookup, not semantic search.** If `Ontario Hospitals by Region` is added as a file-based knowledge source, it's retrieved the same way any generative-answers knowledge source is — chunk-based semantic search, which is probabilistic, not a deterministic table lookup. That's a real risk for a document this prompt treats as an exact-match table (hence its own re-check and Unmatched-labeling steps). Consider putting the mapping in a Dataverse table or an Excel/SharePoint list queried through a Power Automate action for a true exact-match lookup, and keep the Word document as the human-maintained source you publish from.

**Tables aren't reliably native — plan to build them, not just request them.** Copilot Studio's generative layer commonly falls back to bullets or free text even when a table is explicitly requested; this shows up repeatedly in the product community as a known limitation, not just a prompting gap. Since the table format is central to this spec, the more dependable path is a Power Automate flow that assembles the markdown table as a string (or an Adaptive Card) and returns it as the response, rather than trusting the generative layer to format it the same way every time. Also confirm Markdown rendering is turned on for your deployment channel(s) — it's admin-configurable and off by default in some channels, in which case a pipe-delimited table just prints as flat text.

**Citations don't survive custom formatting in Teams.** Copilot Studio auto-generates citation links for un-customized generative answers, but once you customize the output — which this table format requires — Teams stops rendering those automatic citations. You'd need to build the link into your custom output yourself. Worth testing directly in your target channel before assuming "never leave Source or Link blank" is holding end-to-end.

**Enforce "don't speculate" with a setting, not just wording.** Turn off "Allow the AI to use its own general knowledge" (and leave "Allow ungrounded responses" off) on the relevant knowledge sources/nodes. That makes "if nothing reliable is found, say so" a platform guarantee rather than something resting entirely on the model choosing to follow an instruction.

### Further reading
- [Configure high-quality instructions for generative orchestration](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/generative-mode-guidance)
- [Knowledge sources summary](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-copilot-studio)
- [Add a public website as a knowledge source](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-add-public-website)
- [Multi-agent orchestration patterns and best practices](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/multi-agent-patterns)
