---
name: tableau-semantics-dx
description: >-
  Build, modify, and deploy Tableau Next semantic models using the Tableau
  Semantics DX pro-code workflow (Salesforce CLI + the "Salesforce Tableau
  Semantics" VS Code extension, model stored as JSON, versioned in git). Use
  whenever working with a retrieved semantic model folder (calculatedMeasurements.json,
  calculatedDimensions.json, metrics.json, dataObjects.json, model.json, relationships.json,
  etc.), authoring semantic calculated fields / metrics / field or table descriptions,
  deploying changes to a Salesforce Data 360 org, or debugging Semantics DX deploy errors.
  Also relevant for Tableau Pulse / Tableau Agent metadata quality.
---

# Tableau Semantics DX — Pro-Code Semantic Model Workflow

How to develop Tableau Next semantic models as code. The semantic model is retrieved
from a Salesforce Data 360 org as a folder of JSON files, edited locally, validated,
and deployed back. All steps are proven against a real Partner/OrgFarm demo org.

## When to use
- Editing any file inside a retrieved `Semantic Models/<Model Name>/` folder.
- Adding/changing calculated measures, calculated dimensions, metrics, or descriptions.
- Deploying to the org, or diagnosing a failed deploy.
- Bulk metadata work (e.g., "add descriptions to a dozen fields at once").

## Start here — confirm the target (ask, don't assume)
Before retrieving or deploying, confirm three things with the user; ask if any is unstated and
never invent an org alias, folder path, or model name:
- **Which org** — is it authorized to the `sf` CLI? Check `sf org list`; if not, do the
  domain-targeted login below.
- **Which project folder** — an existing SFDX project / git repo, or scaffold a new one.
- **Which semantic model** — the exact model name to retrieve and operate on.

## Prerequisites (all installable; verify, don't reinstall blindly)
- **Git**, **Node/npm**, **Salesforce CLI** (`sf`), **VS Code**.
- VS Code extensions: **Salesforce Extension Pack** (`salesforce.salesforcedx-vscode`)
  and **Salesforce Tableau Semantics** (`salesforce.salesforce-tableau-semantics`).
  Install headless with `code --install-extension <id> --force`.
- A Salesforce org with **Data 360 + Tableau Next** provisioned.

## Org authorization — KNOWN GOTCHA
`sf org login web` against generic `login.salesforce.com` tends to time out
(`AuthTimeoutError`) or land on an "Agentforce DX" marketing page — the OAuth redirect
doesn't return to the CLI's localhost callback. **Fix: target the org's own My Domain.**

```bash
# Get the domain from the org's browser URL, e.g. orgfarm-XXXX.lightning.force.com
sf org login web --instance-url https://orgfarm-XXXX.my.salesforce.com \
  --alias <alias> --set-default -b chrome
```

Run it in the background so the tool/CLI timeout doesn't kill the callback while the
user logs in. This CLI generation has **no device-code flow** — only
`web`, `jwt`, `access-token`, `sfdx-url`. Verify with `sf org list`.

## Project setup
```bash
sf project generate --name <proj> --template standard --output-dir .
cd <proj> && git init && git add . && git commit -m "Initial commit: SFDX project scaffolding"
```
Create a `Semantic Models` folder at the project root to retrieve into.

## The core loop
1. **Retrieve** — right-click the `Semantic Models` folder (or Command Palette) →
   **Tableau Semantic: Retrieve Model to Folder** → pick the model. Writes a JSON folder.
   Commit this as the baseline.
2. **Edit** the JSON (see file map + rules below).
3. **Validate** — right-click `model.json` → **Tableau Semantic: Validate Model**
   (expects "Model is Valid"). NOTE: **validation can pass while deploy still fails.**
4. **Deploy** — right-click `model.json` → **Tableau Semantic: Deploy Model**.
5. **Retrieve again** to capture server-auto-populated fields, then commit a save point.
6. Hard-refresh the Tableau Next browser UI (Ctrl+Shift+R) to see changes.

The retrieve/validate/deploy commands are **extension-only** — there is **no `sf` CLI
plugin** for them.

## File map (inside `Semantic Models/<Model>/`)
- `calculatedMeasurements.json` — calculated measures (items[])
- `calculatedDimensions.json` — calculated dimensions (items[])
- `metrics.json` — metrics (items[])
- `dataObjects.json` — the DMOs and their fields; also holds **field- and table-level descriptions**
- `relationships.json` — joins between objects
- `model.json` — model-level settings (right-click target for validate/deploy)
- `modelInfo.json`, `modelFilters.json`, `fieldsOverrides.json`, `logicalViews.json`,
  `dimensionHierarchies.json`, `groupings.json`, `parameters.json`, `metadata/`

## CRITICAL rules for editing

### 1. Field API names get numeric suffixes — ALWAYS verify in `dataObjects.json`
Data 360 makes field API names **globally unique per org**. If a source (e.g. Superstore)
was uploaded more than once, plain names collide and get numeric suffixes:
`Profit` → `Profit2`, `Sales` → `Sales2`, `Region` → `Region9`, `Ship Mode` → `Ship_Mode2`,
`Data Source` → `Data_Source13`, etc. Sample formulas from docs (`[Sales]`, `[Order_ID]`)
will **deploy-fail** on such an org. Before writing any formula, read `dataObjects.json`
and use the real `apiName` of each field. Objects are also referenced by apiName
(e.g. `Superstore_Orders`, spaces → underscores).

### 2. Formula syntax (verified)
- Reference fields as `[Object_ApiName].[Field_ApiName]` (underscores, not display names).
- Conditionals: `IF <cond> then <a> ELSE <b> END` (lowercase `then`, uppercase `ELSE`/`END`).
- String literals in double quotes (escape as `\"` in JSON).
- Functions seen working: `SUM`, `COUNTD`, `count`, arithmetic `/`, comparisons.
- Measures: `"aggregationType": "UserAgg"` (server sets `level: AggregateFunction`).
  Dimensions get `level: Row`.

### 3. The `%` literal breaks the parser
`[Discount2] > 15%` fails with `Syntax Error - no viable alternative at input 'then'`.
Discounts are stored as decimals, so use `> 0.15`. Prefer plain decimals over `%`.

### 4. Cross-table references in a calc
A row-level calc can reference a field on a **related object** when that object is on the
**"one" side of a Many-to-One relationship**. Example (Orders → Returns, Many-to-One):
```
Return Status (dim):  IF [Superstore_Returns].[Returned1] = "Yes" then "Returned" ELSE "Kept" END
Net Sales   (measure): SUM(IF [Superstore_Returns].[Returned1] = "Yes" then 0 ELSE [Superstore_Orders].[Sales2] END)
```
Relying on `= "Yes"` (null falls through to ELSE) is lower-risk than an `ISNULL()` you
haven't confirmed is supported.

### 5. Descriptions (both levels are pro-code editable and round-trip)
- **Field description**: add a `"description"` key directly on the field object inside
  `dataObjects.json` (NOT in `fieldsOverrides.json` — that stays empty here).
- **Table/object description**: add a `"description"` key at the top level of the object's
  item in `dataObjects.json` (objects start with none; adding one deploys and persists).
- **Calc/metric description**: the `"description"` key on the object in the respective file.
- Table descriptions can also be set on the DMO in Data 360 and inherited down.
- Good descriptions materially improve how **Tableau Agent / Pulse** map natural-language
  questions to fields: state business meaning, units/format (dollars, decimal fraction,
  date), known category values, synonyms, and key/relationship notes.

### 6. Object display labels are pro-code editable
An object's display name is the `label` key on its item in `dataObjects.json`; edit it, deploy,
and it persists. The **`apiName` is the immutable identity** (relationships reference it via
`leftSemanticDefinitionApiName`/`rightSemanticDefinitionApiName`), so renaming a `label` is
cosmetic and safe — it won't break joins or field refs. (Example: File-Upload DMOs come in
labeled like `Budgets.csv`; strip the `.csv` from `label` for clean titles. The apiName stays
`Budgets_csv`.)

### 7. Data Cloud primary key must be TEXT (surrogate keys for date dimensions)
A DLO/data-stream primary key must be a **text** field — Date and Number columns are NOT
offered as PK candidates. For a **date-dimension / Calendar scaffold** (unique key = the date),
add a **text surrogate key** before upload, e.g. `Date ID = "DT-" + ISO date` ("DT-2025-01-01").
The leading letters force text typing (a bare `YYYYMMDD` would be read as a Number, also
ineligible). Keep the real `Date` column as a Date type for time logic; use the text key as PK.
Category for a Calendar scaffold = **Other** (it's reference data, not Profile or Engagement).

### 8. Field visibility, primary keys, and the Many-to-One lever
All confirmed on the HR test model:
- **Hide a field** — set `"isVisible": false` on it in `dataObjects.json` and deploy; it stays
  hidden on round-trip. No `overriddenProperties` entry needed. Use to hide Data Cloud
  system/lineage fields, matched by apiName prefix: `cdp_sys_*`, `KQ_*`, `Data_Source*`,
  `Internal_Organization*`, `uuid_temp*` (≈5–6 per File-Upload table).
- **`isPrimaryKey` is read-only** — the field-level flag deploys without error but has no effect
  (reverts to `false`). Don't use it to try to set a key.
- **Many-to-One lever = object-level `primaryNameField`** — set it to the table's business key
  (e.g. `Department.primaryNameField = "department_id2"`) and joins into that table can be
  Many-to-One. Writable pro-code, no Data Stream reload. Details in `tableau-semantic-relationships`.
- File-Upload DMOs auto-generate a `uuid_temp` + `KQ_uuid_temp` surrogate identity when no business
  key is designated at ingest — hide these, and set `primaryNameField` for real keys.

## Authoring descriptions for Tableau Agent / Pulse (recipe)
Descriptions are what the conversational agent reads to map natural-language questions
to fields, so write them for recall, not just documentation. Proven recipe:
1. **Lead with business meaning** in the domain's context — never restate the field name
   ("Business-friendly field describing X" is useless).
2. **State units/format** for measures and coded fields: currency (USD), decimal rate
   (0.154 = 15.4%), 0–100 score (say if higher is better), days, Yes/No flag, date.
3. **For IDs/keys**, say what it identifies and what it links to (from `relationships.json`);
   mark primary keys.
4. **Synonyms — anchors only, curated only.** Embed "Also called …" at *anchor points*
   for an entity (the **table description** + the entity's **ID** and **Name** fields), not
   on every column. Pull synonyms from a curated business glossary; do NOT invent new ones.
   Keep the glossary as the human source of truth AND embed at anchors — the deployed model
   is the only thing the agent sees, so a synonyms-only spreadsheet tab won't reach it.
5. **Keep it tight**: 1–2 sentences, and **≤255 characters** (hard platform cap — see below).

### Description length limit — 255 characters (CONFIRMED)
Semantic descriptions (both field- and table/object-level) are capped at **255 characters**.
The docs don't publish this; deploy fails with `SemanticAuthoringError` /
`Semantic Definition Description: data value too large ... (max length=255)`. Validate does
NOT catch it — only deploy does. Keep every description ≤255 chars (aim ≤250 for margin).
When authoring in bulk, enforce the cap at generation time and re-check before deploy:
```python
assert all(len(x)<=255 for x in descriptions)
```

## Bulk description workflow (large models)
For a model with dozens of tables / hundreds of fields, driven from a metadata spreadsheet
(columns like Table, Field, basic Description, Example Value, Recommended Role, plus a
Business Synonyms tab and a Relationships tab):
1. **Extract** all tabs to a single JSON working file (fields, tables, relationships, synonyms).
2. **Lock the style** on a small sample with the user before generating everything.
3. **Generate in parallel** — split by domain (group related tables) and run one subagent per
   group with the recipe above + the shared JSON path; each writes a strict JSON file
   (`{"tables":[{"table","table_description","fields":[{"field","improved"}]}]}`).
4. **Assemble + QC** into a review spreadsheet (Original vs Improved side by side, plus a
   Table Descriptions tab); verify 100% field coverage and max lengths.
5. After sign-off, **write into `dataObjects.json`**: match each row to the real (suffixed)
   field API name, set field `description` keys and object-level `description` keys, then
   validate → deploy → retrieve. Excel may lock the source file — copy it to a scratch dir
   before reading with openpyxl (`PermissionError [Errno 13]` = it's open in Excel).

## Relationships (relationships.json)
Each relationship item:
```json
{ "apiName":"Child_Parent", "cardinality":"ManyToMany",
  "criteria":[{"joinOperator":"Equals","leftFieldType":"TableField",
               "leftSemanticFieldApiName":"<left field apiName>","rightFieldType":"TableField",
               "rightSemanticFieldApiName":"<right field apiName>"}],
  "isEnabled":true, "isQueryable":"Queryable", "joinType":"Auto",
  "label":"Child : Parent",
  "leftSemanticDefinitionApiName":"<obj apiName>", "rightSemanticDefinitionApiName":"<obj apiName>" }
```
`leftSemanticFieldApiName` is a field on `leftSemanticDefinitionApiName`; resolve all names by
**label → real (suffixed) apiName** from `dataObjects.json`. Omit server fields (id/createdBy/dates).

Three constraints learned the hard way:
1. **Cardinality needs a primary key for Many-to-One.** If no field has `isPrimaryKey:true` in the
   model (common — File-Upload DMOs expose `KQ_<id>` key-qualifier fields but none flagged PK),
   the platform rejects `ManyToOne` on deploy (500: *"API Name has no mapped semantic definition
   ID"*) and the GUI offers **only Many-to-Many**. Use **`ManyToMany`** — it is Tableau's safe
   default and gives correct aggregation even when the data is many-to-one (M:1 is only a perf
   optimization that requires a recognized key). To get M:1, establish DMO primary keys upstream.
2. **The relationship graph must be ACYCLIC.** Validate fails with `CYCLIC_RELATIONSHIP_ERROR`
   listing the objects in the loop. Two fact tables sharing 2+ common dimensions IS a cycle
   (conformed dimensions aren't allowed). Resolve: make one fact the **dimension hub**; the other
   connects via a single **conversion/leaf link** and slices on its own denormalized inline columns
   (e.g., Projects owns Clients/Offices/Project Types; Opportunities links only via
   Projects→Opportunities and uses its inline Client Name / Project Type / Nearest Office).
   Also avoid redundant second paths (e.g., don't add Tasks→Projects when Tasks→Milestones→Projects
   already exists).
3. **Validate catches cycles; deploy catches cardinality/key-mapping.** Both gates matter — a set
   can validate clean and still fail deploy on cardinality.

Seed one relationship in the GUI + retrieve to confirm the exact structure and the cardinality the
platform will accept (same trick as descriptions/field-overrides).

## Clean-diff formatting convention
The server emits JSON as 2-space indent, alphabetically sorted keys, UTF-8, trailing
newline. To keep git diffs minimal and additive when editing programmatically:
```python
json.dump(data, open(path,"w",encoding="utf-8"), indent=2, ensure_ascii=False, sort_keys=True)
open(path,"a",encoding="utf-8").write("\n")
```
Then confirm the diff is purely additive (`git diff --stat`).

## Debugging a failed deploy (e.g., "Error 400")
The extension logs the **outgoing payload** (not the response body) to the VS Code Output
channel **"Semantic Layer Deploy"**, on disk under
`AppData/Roaming/Code/logs/<session>/window1/exthost/output_logging_*/*Semantic Layer Deploy.log`.
The full error is surfaced as a toast — ask the user to copy it from the toast or the
Output panel. To capture the raw server response yourself, replay the PUT with the org token
(a 400 creates nothing, so it's non-mutating):
```bash
# token/instance from: sf org display --verbose --json  (result.accessToken / result.instanceUrl)
curl -sS -w "\nHTTP:%{http_code}\n" -X PUT \
  "$INSTANCE/services/data/v66.0/ssot/semantic/models/<modelApiName>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary @payload.json
```
The `<modelApiName>` (e.g. `New_Semantic_Model_xxxx`) is in the deploy log's endpoint line
and in `model.json` (`apiName`). Common 400 causes: wrong field apiName (missing suffix),
unsupported formula syntax (`%`), malformed JSON (missing comma between items).

## Reusable calc patterns
- **Ratio measure**: `SUM([Obj].[A]) / SUM([Obj].[B])` with `UserAgg`.
- **Classification dimension**: `IF [Obj].[Field] = "X" then "A" ELSE "B" END`.
- **Threshold dimension** (decimals!): `IF [Obj].[Discount2] > 0.15 then "High" ELSE "Standard" END`.
- **Distinct-count metric base**: `SUM([Obj].[Sales2]) / COUNTD([Obj].[Order_ID2])` (AOV).
- **Returns / Net Sales**: see cross-table example above.

## Reference projects & companion skills
Worked examples:
- `C:\Users\celia\source\repos\superstore-sdx` (GitHub `celiafryar/superstore-sdx`) — the Superstore
  SDM; smallest end-to-end run of the loop. See the `semantics-dx-project` memory.
- `C:\Users\celia\source\repos\construction-sdx` (GitHub `celiafryar/construction-sdx`) — the
  Alderstone "All Tables" model at scale: 25 tables described, 287 field descriptions, 21
  relationships. Source of the 255-char, acyclic, and Many-to-Many lessons above. See the
  `alderstone-construction-model` memory.

Companion skills (this one owns the retrieve/validate/deploy mechanics they call into):
- `semantic-descriptions-from-spreadsheet` — bulk field/table descriptions from a metadata workbook.
- `tableau-semantic-relationships` — joins & cardinality authored in `relationships.json`.
- `snowflake-dbt-to-semantic-metadata` — extract source metadata (Snowflake/dbt) to feed the pipeline.
