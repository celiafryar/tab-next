---
name: semantic-descriptions-from-spreadsheet
description: >-
  Turn a metadata spreadsheet (table names, field names, basic descriptions, example values,
  recommended roles, and a business-synonyms tab) into agent-optimized field and table
  descriptions, then write them into a Tableau Next semantic model and deploy. Use when the
  user has a data dictionary / metadata workbook and wants bulk, high-quality descriptions for
  conversational analytics (Tableau Pulse / Agentforce) — dozens of tables / hundreds of fields.
  Companion to the tableau-semantics-dx skill (which owns the retrieve/validate/deploy mechanics).
---

# Bulk Semantic Descriptions from a Metadata Spreadsheet

Repeatable playbook for authoring agent-ready descriptions at scale and loading them into a
Tableau Next semantic model. Proven on the Alderstone "All Tables" model (25 tables, 287 fields).
For org auth, project setup, retrieve/validate/deploy, and platform gotchas, use the
**`tableau-semantics-dx`** skill — this skill focuses on the description authoring + matching.

## Expected input
A spreadsheet (single- or multi-tab) describing the model. The ideal shape is a **Field
Descriptions** tab (`Table Name, Field Name, Field Description, Example Value, Recommended Role`),
plus a **Table Index**, a **Relationships** tab, and a **Business Synonyms** tab
(`Business Term, Explanation, Related Words and Phrases`). Sample-data tabs can be ignored.

Be forgiving about the shape:
- **Minimum to proceed:** table names + field names. Drafted descriptions, example values,
  recommended roles, and synonyms all improve the output but are **not required** — infer role
  (dimension vs measure) and format from the field name + example when they're missing.
- Accept a **single tab** that holds everything (a `Table Name` column beside field rows), or a
  **tab-per-table** layout (tab name = table).
- Tolerate **column-name variants** (e.g., "Column"/"Field", "Description"/"Definition",
  "Example"/"Sample", "Role"/"Type") — map them, and confirm the mapping with the user.

## Process

### 0. Get the worksheet — ask first, don't assume
- If the user hasn't handed over a metadata workbook, **ask for it** — the file path/location (or
  have them paste/upload it). Never invent one or guess a path.
- Once you have it, **echo back what you found** — the tabs, the detected columns and how they map
  to the roles above, and row/table counts — and get a quick confirmation before extracting.
- **If the user doesn't have a worksheet yet**, offer to bootstrap one instead of stalling:
  - Hand them a **blank template** with the expected columns (Field Descriptions tab +
    Business Synonyms tab) to fill in.
  - **Seed it from an existing model** — retrieve the target semantic model and populate
    table + field rows from `dataObjects.json` (labels), so they only fill in descriptions.
  - **Extract from source** — run the `snowflake-dbt-to-semantic-metadata` skill to pull
    tables/fields/descriptions/keys from Snowflake or a dbt project into this shape.
- Confirm the **target model** (workspace + semantic model name) too, since Step 6 matches to it.

### 1. Extract the source to JSON
- **Excel locks its open files** — if you hit `PermissionError [Errno 13]`, copy the workbook to
  a scratch dir and read the copy (`openpyxl`, `data_only=True`).
- Emit one JSON working file: `{"fields":[...], "tables":[...], "relationships":[...], "synonyms":[...]}`.
- Report tab names, columns, row counts, and fields-per-table so the user confirms scope.

### 2. Lock the style on a small sample FIRST
Show ~10 before→after examples (mix of IDs, dimensions, measures, scores, a synonym-anchored
field) and get sign-off before generating everything. Saves regenerating hundreds in the wrong style.

### 3. Generate in parallel, grouped by domain
Split the tables into ~6 domain groups (reference/lookups; each large fact table on its own;
schedule; cost/procurement; quality/safety/risk). Run **one subagent per group** (Agent tool,
`general-purpose`, sonnet is sufficient), each given the recipe below + the shared JSON path,
writing a strict JSON file `out_gN.json`:
`{"tables":[{"table","table_description","fields":[{"field","improved"}]}]}`.
Launch them in one message so they run concurrently. Then assemble + QC yourself.

### 4. The description recipe (per field)
1. **Business meaning first** in the domain's real-world context — never restate the field name.
2. **Units/format**: USD for money; decimal rate (0.154 = 15.4%); 0–100 score (say if higher is
   better); days; Yes/No flag; dates. Infer format from Example Value.
3. **IDs/keys**: what it identifies + what it links to (from the Relationships tab); mark PKs.
4. **Synonyms — anchors only, curated only**: embed "Also called …" ONLY on the table
   description + the entity's ID and Name fields, drawn strictly from the Business Synonyms tab.
   Never invent synonyms; never sprinkle on every column.
5. **≤255 characters** (hard platform cap — see gotchas) and 1–2 sentences.
6. One **table-level description** per table (grain: "one row per …") with entity synonyms.

### 5. Assemble a review spreadsheet and QC
Build `<Name>_Descriptions_Review_v1.xlsx`: tab **Field Descriptions**
(`Table · Field · Role · Example · Original · Improved`) + tab **Table Descriptions**. Verify
100% field coverage and that every description ≤255. Let the user review/tweak before writing.

### 6. Write into the model and deploy
- Retrieve the target model (via `tableau-semantics-dx`). Match each row to the model by
  **label**, not API name.
- **Object labels may carry a `.csv` suffix** (File-Upload DMOs) — strip it when matching table
  names. **Field labels are usually clean** and match the spreadsheet.
- Set `description` on each matched field object and each matched data object (top-level
  `description`) in `dataObjects.json`. Skip system fields (`cdp_sys_*`, `KQ_*`, `Data_Source*`,
  `Internal_Organization*`).
- **Run a dry-run match report first**: how many of your rows matched, which rows have no model
  field (renames), which model business-fields got no description, which tables in the sheet
  aren't in the model. Surface all of this — don't silently drop.
- Enforce `assert all(len(d)<=255 for d in descriptions)` before deploy.
- Write with `json.dump(..., indent=2, ensure_ascii=False, sort_keys=True)` + trailing newline
  (matches server format → clean additive diff). Commit, then user validates → deploys → retrieves.

## Gotchas learned
- **255-char hard cap** on any description; Validate passes but Deploy fails
  `data value too large (max length=255)`. Enforce at generation and re-check before deploy.
- **Tables in the spreadsheet may not be in the model.** Report them; they can't be described
  until their DMOs are added to the model. Keep their text in the review sheet regardless.
- **Match by label, not apiName** — apiNames get numeric suffixes and won't equal the sheet.
- **Excel file locks** on open workbooks — copy to scratch before reading.
- Descriptions are what the agent reads to map NL → fields; keep a curated synonyms glossary as
  the human source of truth AND embed synonyms at anchors (the deployed model is all the agent sees).

## Reference implementation
Alderstone "All Tables": project `C:\Users\celia\source\repos\construction-sdx`
(GitHub `celiafryar/construction-sdx`); source workbook + review sheet under
`...\Tableau Next\Data Files\Construction Demo Data\`. See the `alderstone-construction-model` memory.
