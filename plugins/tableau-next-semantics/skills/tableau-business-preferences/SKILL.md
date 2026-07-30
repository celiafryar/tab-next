---
name: tableau-business-preferences
description: >-
  Author and test Business Preferences for a Tableau Next / Agentforce for Analytics agent: the
  instruction file that teaches the agent business language, intent, and safe defaults. Use when the
  agent misreads a word (revenue, states, this quarter, customers), returns a technically correct
  number that answers the wrong question, ignores an instruction, or when a preferences file has
  grown long and unreliable. Also use to decide what belongs in preferences versus descriptions,
  calculated fields, or metrics. Companion to tableau-semantics-dx.
---

# Business Preferences for Tableau Next

Business Preferences are a plain-text instruction list that teaches the agent **how the business
speaks and what to do when a question is ambiguous.** They are not where calculations live.

Everything below marked CONFIRMED was established by live testing against a deployed model
(sales-opportunity-sdx, 2026-07-29/30), not from documentation.

## File format
One instruction per line, each line beginning with `#`. No blank lines, no section headers (a header
would be ingested as an instruction). Plain sentences.
```
#Bookings means the value of Closed Won opportunities. People may also say awarded sales or won business.
```
Working size: **~60 lines / ~1,200 words.** Two field-tested files landed at 49 and 62 lines.

## THE SIX RULES THAT DECIDE WHETHER A LINE WORKS

### 1. Preferences govern METHOD, not PROSE (the most important finding)
CONFIRMED across every test. Instructions about **which field, which filter, which population, which
scope, how to sort** are obeyed reliably. Instructions about **wording of the narrative** are largely
ignored.

The platform owns the response structure (narrative → chart → **Sources** panel), so you cannot
instruct your way into a different shape. Response-styling instructions land in the agent's
*methodology narration*, which the UI files under Sources — collapsed by default.

**Consequence: stop spending lines on phrasing.** A file heavy on tone, formatting and emoji rules is
mostly inert. One real example: 33 of 127 lines in a first draft were one-emoji-per-line rules that
never visibly fired, because there was no slot for them to fire into.

### 2. Every rule must be EXECUTABLE, not merely correct
A rule that states an intention the agent has no unambiguous way to compute will fail.

> FAILED: `#Customer count means the number of accounts with at least one opportunity.`
> The agent must count the account key **on the Opportunity table**, not on Account — and both fields
> are labelled `AccountId`. It returned all accounts instead.

Before writing a rule, ask: *could I execute this myself using only field labels the agent can see?*
If not, fix the model (label, calculated field, metric) rather than writing the rule.

### 3. Never prohibit without substituting
CONFIRMED. A ban leaves the agent with nothing to do, so it does the helpful thing and violates you.

> FAILED: `#Do not call Bookings revenue.` → agent answered "Our total revenue is $393.87M."
> WORKED: adding `#When a user asks about revenue, answer using Bookings and call it Bookings or won
> business in your reply.`

**Lead with the instruction. The prohibition is the tail, not the head.** Apply the same shape to
definitions: say what the thing *is* before saying what it must not be called.

### 4. Prefer a FIELD over a request for careful phrasing
If something must be visible in the answer, make it a field in the result, not a caveat you hope the
agent repeats.

> A field labelled `StateProvince` mixes US states, Canadian provinces and Mexican states. Asking the
> agent to "say so" is prose (rule 1). Instructing it to **include Country alongside State or
> Province** is method — and the mixed units become self-evident in every row, surviving screenshots
> and decks.

### 5. DEFAULTS are the killer app
The highest-value rules resolve an ambiguity the data itself cannot. This is the one job nothing else
in the stack can do.

> A `NetRevenue` field summed across all lifecycles gave $1.57B, of which **22% came from deals the
> company LOST** and 53% from open pipeline. No description, calculated field or metric fixes this,
> because the field is legitimately ambiguous. Only a default can:
> `#Net Revenue always requires an opportunity lifecycle scope. Default to Closed Won and state the scope used.`
> That single rule changed both the total AND the ranking (one state moved from 7th to 2nd).

Write a default for every measure that is meaningless without a scope, every relative time word
(this quarter, YTD, current), and every count with more than one defensible population.

### 6. The agent MIRRORS the user's vocabulary
Ask about "revenue" and it says revenue back, even holding an instruction not to. So the *consultant's
phrasing* matters as much as the file. Ship a say-this-not-that list alongside the preferences.

## Section structure that works
Ordered by value, not by tradition. Approximate line budget for a 60-line file:

| Section | Lines | Job |
|---|---|---|
| Glossary and jargon | 20-25 | `#X means Y. People may also say a, b, c.` Pull synonyms from a curated glossary; never invent |
| Defaults and business rules | 10-15 | Lifecycle scoping, sign conventions ("a positive slip is unfavorable"), ratio-of-sums, thresholds |
| Dates and relative periods | 5-8 | Anchor "current/this/YTD" to the dataset's as-of date, not today |
| Geography and hierarchy | 4-6 | Which path is default; what is NOT joined |
| Counts and populations | 1-3 | Every count with multiple defensible answers |
| Answer behavior | 6-8 | Answer grain, sort direction, row limits, no fabrication, state your filters |
| Response format | 2-3 | Keep it minimal. See rule 1 |

## What to CUT (all observed as low or zero value)
- **Embedded hypotheses / narrative explanations.** "Denver projects perform better because of mature
  vendor relationships." This is analysis, not language. It also invites the agent to assert causation.
- **Chart-type prescriptions.** Line for trends, bar for rankings, no pie over five categories. The
  platform picks the chart.
- **Formatting minutiae.** Decimal places, date formats, currency notation.
- **Grain restatements that duplicate deployed table descriptions.** "One Account row is one customer
  organization" belongs in the table description, and duplicating it creates two places to drift.
- **Emoji rules beyond two or three lines**, and consolidate rather than listing one per symbol
  (`#Use 🎯 for KPIs, 💰 for financial metrics, 👥 for people` — one line, not three).
- **Duplicates and contradictions.** Real files accumulate literal repeats; they are worse than
  useless because they compete.

## The authoring and testing loop
1. **Smoke-test the channel before writing the file.** Three lines, then ask anything:
   ```
   #Always begin every response with 📊 Summary.
   #Always end every response with the exact phrase Preferences are active.
   #Never fabricate values or unsupported assumptions.
   ```
   Look in the **Sources** panel, not the narrative. If nothing appears, the problem is loading or
   scoping and no amount of authoring will fix it. (Emoji DO render — CONFIRMED.)
2. **Write the file** using the sections above.
3. **Test with 2-3 questions that have a precomputed answer key.** Compute the expected answers from
   the source data first. A test whose answer you cannot verify proves nothing.
   Design each test so the right and wrong answers differ *visibly* — a changed ranking beats a
   changed total, because a ranking change cannot be a rounding artifact.
4. **When a test fails, classify the failure before rewriting:** was the rule prose (rule 1),
   inexecutable (rule 2), or a bare prohibition (rule 3)? Each has a different fix.
5. Re-test. Expect two or three rounds.

## Decision hierarchy: where does this belong?
Business Preferences are NOT the last resort. They are the right home for one specific class of
problem. Ask in this order:

1. **Is the agent picking the wrong field?** → fix the **label** first (it is what the agent matches
   on), then the **description** (what it reads). Labels are underrated: renaming `StateProvince` to
   `State or Province` visibly changed how the agent described its own answer.
2. **Is a concept recomputed every time, or too complex to derive?** → **calculated field**.
3. **Is it a governed KPI needing consistent aggregation, polarity and dimensions?** → **metric**.
4. **Is it a frequently asked executive question?** → **verified question**.
5. **Is the question ambiguous, or is the DEFAULT wrong?** → **Business Preference.** This includes
   jargon, synonyms, which of several fields a word means, lifecycle and period defaults, population
   definitions, and what to do when the user is vague.

**Do not treat 5 as a fallback for 1-4.** Steps 1-4 answer *what the data is*; step 5 answers *what
the user meant*. A default cannot be pushed down into a calculated field, because the ambiguity lives
in the question, not the data.

## Platform constraints that interact with preferences
- **Response structure is fixed:** narrative, chart, Sources. Sources carries Fields Used and Filters
  Applied and is the only precise part. Teach users to read it.
- **A geo-roled field cannot be a metric dimension** (dataType becomes `Geo`; metrics accept Text,
  Number, Boolean, Email, PhoneNumber, Url). So governed metrics break down by region/territory, not
  by state, even though direct questions about state work fine.
- **Duplicate field labels cause silent wrong-field selection.** Fields Used names a field without its
  table. Audit for labels appearing on more than one object; one real model had 19 of 109. A
  preference cannot reliably disambiguate what the agent cannot distinguish — fix the labels.
- **Fields with a single value** (a status column that is always "Active") are dead dimensions; say so
  in the description or hide them.

## Reference implementations
- `...\Tableau Next\Business Preferences\Apex Motion Bus Pref v1.txt` — 62 lines, built with the rules
  above and validated by three answer-key tests. See [[sales-opportunity-model]].
- `...\Alderstone Bus Pref v2.txt` / `v3.txt` — 49 lines, cut down from a 127-line original. The diff
  between them is a good study in what to remove.
