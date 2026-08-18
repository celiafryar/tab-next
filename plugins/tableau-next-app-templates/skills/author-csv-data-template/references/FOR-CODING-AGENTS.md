# CSV Data Templates — Coding-Agent Playbook

Rule-dense companion to [README.md](./README.md). Hand this to a coding agent building a
Tableau Next **CSV Data Template**: an ATF template (`templateType: App`) that ships CSV
files and, on Create, builds a full analytics app bottom-up — CSV → Data Stream → DLO →
(optional DMO/CI) → Semantic Model → Visualizations → Dashboard.

**Reference implementations (read before writing anything):**
- `force-app/main/default/appTemplates/CSV_Example/` — canonical, minimal, **full node
  menu** (incl. optional DMO + mapping + Calculated Insight). **Read-only truth — never
  modify it.** Mirror its file shapes.
- `force-app/main/default/appTemplates/superstore_demo_template/` — realistic multi-CSV app
  on **DLOs directly (no DMO path)**; the dates-gotcha survivor.
- `docs/appTemplates/SUPERSTORE_DEMO_COMPLETENESS.md` — the full case study; cite it for any
  ingestion debugging.

---

## The hard rules (each earned from a real failure)

### Structure

- **S1 — Ship your own data.** The template must carry its CSVs under `csvs/` and the chain
  must *create* the DLO via `DataStreamUpsert`. Nothing may assume a pre-existing DLO, DMO,
  stream, or model in the target org. Test in a **clean** org, never the one you authored in.
- **S2 — Five framework files are mandatory:** `template-info.json`, `variables.json`,
  `layout.json`, `create-chain.json`, `template-policy.json`. **Missing `template-policy.json`
  → the template may not surface in the gallery.** Copy `CSV_Example`'s policy verbatim.
- **S3 — Only include node types you need.** `CSV_Example` ships the full menu (DMO +
  mapping + CI). If your SDM sits directly on DLOs (like `superstore_demo_template`), **omit
  the `dmos/`, `cis/`, and their chain nodes entirely.** Fewer nodes = fewer failure modes.

### Tokenization (portability — the #1 correctness issue)

- **T1 — NEVER hardcode a resolved asset name.** No physical DLO/DMO/SDM name (anything with
  a hash like `…26132319529__dll`) may appear in any shipped JSON. If you exported an SDM
  from a UI, it *will* contain these — you must replace them.
- **T2 — Reference assets by their chain-node token:**
  - DLO → `${App.DataLakeObjects.<node's dataLakeObject.name>.Name}`
  - DMO → `${App.DataModelObjects.<DMO node's parameters.name>.Name}`
  - SDM → `${App.SemanticModels.<SDM node's parameters.name>.Name}` (or `.Id`)
  - Workspace → `${App.Workspaces.<node name>.Name}`
  - Visualization → `${App.Visualizations.<node name>.Name}` / `.Id`
- **T3 — The DLO token key is the `dataLakeObject.name` on the `DataStreamUpsert` node**, not
  the stream name and not the DLO's physical name. Confirmed: `CSV_Example` declares
  `dataLakeObject.name: "CustomersDLO"`; `SObject_Example`'s mapping references
  `${App.DataLakeObjects.SObject_DLO.Name}`. The token resolves even when Data Cloud suffixes
  the physical name to avoid a collision (observed live: `Superstore_Orders_DLO4__dll`).

### CSV / ingestion (the biggest time-sink)

- **C1 — Dates MUST be ISO `yyyy-MM-dd` in the shipped CSV.** Data Cloud parses dates with
  its default ISO parser; the datastream `format` hint does **not** reliably override it
  through `DataStreamUpsert`. US-style `M/d/yyyy` → every row fails → whole stream rejected
  (~120 s, **0 rows**), with the real error visible **only in Data Cloud's Refresh History
  UX** (not queryable via REST or sObjects). Reformat the CSV to ISO; set datastream
  `format: "yyyy-MM-dd"`; keep the column typed `Date` (not `Text`) so time-series works.
- **C2 — Datastream source-field casing is `dataType` (camelCase).** The runtime *read* API
  serializes it lowercase (`datatype`), but the **template deploy schema
  (`DataStreamSourceFieldInputRepresentation`) requires camelCase `dataType`** — lowercase
  fails deploy with "Unrecognized field [datatype]". Do not copy casing from a read response.
- **C3 — DLO field names come out as `<datastream fields[].name>__c` verbatim**, plus fixed
  system columns (`cdp_sys_SourceVersion__c`, `DataSource__c`, `DataSourceObject__c`,
  `InternalOrganization__c`, `KQ_<PK>__c`). Name your datastream fields with the clean names
  you want the SDM to bind to (e.g. `Sales`, `Order_Date`, `Sub_Category`). Do **not** invent
  positional names like `Sales_r` — those are manual-upload-wizard artifacts, not what the
  datastream path produces.
- **C4 — Prefer LF line endings and match `CSV_Example`'s byte shape.** (CRLF was *not* the
  cause of the Superstore failure, but LF is the proven-good reference format.)

### Chain topology

- **X1 — Serial ingestion. One `DataStreamRun` sources only its own `DataStreamUpsert`.** Do
  NOT add a `sources` barrier to fire multiple runs together: it doesn't reduce wall time
  (Data Cloud aligns jobs on its own ~5-min scheduler tick) **and** it breaks the SDM node
  with `Creation of semantic entities … The [dataType] field is missing` — a race where the
  SDM reads DLO field schema before `dataType` has propagated. The serial gaps are protective.
- **X2 — `SemanticModelUpsert.sources` must (transitively) depend on every `DataStreamRun`**,
  so the model builds only after all DLOs are populated. In multi-stream templates, point the
  SDM node at all the run nodes.
- **X3 — Conditions gate optional branches.** Put `"condition": "${Variables.CreateX}"` on
  every node in an optional branch (e.g. both the DMO node *and* its Mapping node). A dangling
  conditioned child of a skipped parent will fail.
- **X4 — `DashboardUpsert.sources` = the viz nodes it lays out.** Vizzes source the SDM node.

### Wizard

- **W1 — One `BooleanType` variable per optional branch**, wired 1:1 to that branch's node
  `condition`s. This is the teaching pattern; keep the names aligned (`CreateDMO` ↔
  `${Variables.CreateDMO}`).
- **W2 — Sizing is a deliberate choice.** Ship a `SampleSize` `StringType`+`enums` dropdown
  only if the point is to demo the mechanism (like `CSV_Example`). For a canonical dataset,
  ship the full data and omit the variable (like `superstore_demo_template`).
- **W3 — Include a `LabelSuffix` free-text var** and append it to asset labels so repeated
  installs don't collide.

### Deploy

- **D1 — Deploy the whole template directory**, e.g.
  `sf project deploy start --source-dir force-app/main/default/appTemplates/<Name>`.

---

## Build sequence

```
[ ] 1. Confirm data + intent: which CSV(s), which columns, does the SDM need a DMO path?
[ ] 2. Prep CSVs: reformat dates to ISO yyyy-MM-dd (C1); LF endings (C4); clean headers.
[ ] 3. Author datastreams/*.json (one per CSV): sourceFields with camelCase dataType (C2),
       dataLakeObject.name (the token key, T3), format "yyyy-MM-dd" for dates, PK, mappings.
[ ] 4. Author/adjust sdms/*.json: bind each data object to ${App.DataLakeObjects.<node>.Name}
       (T2) — strip every hardcoded __dll name (T1).
[ ] 5. Author visualizations/*.json + dashboards/*.json: reference the SDM by token.
[ ] 6. Author create-chain.json: CSVUpsert → DataStreamUpsert → DataStreamRun per object
       (serial, X1); SDM sources all runs (X2); optional branches conditioned (X3);
       dashboard sources the vizzes (X4).
[ ] 7. variables.json + layout.json: Create* toggles ↔ conditions (W1), sizing (W2),
       LabelSuffix (W3).
[ ] 8. template-info.json + template-policy.json (copy CSV_Example's policy, S2).
[ ] 9. Deploy the whole dir (D1). Create in a CLEAN org. Verify (below).
```

---

## Headless verification (never claim done without it)

Drive Create via the platform API and confirm the app builds end-to-end. Default test org
here is `headless` (Wave API is disabled there — use the `app-framework` endpoint).

```bash
# List installed templates to get the templateSourceId
sf api request rest "/services/data/v64.0/app-framework/templates" --target-org headless

# Create an app from the template (templateValues carry the wizard answers)
sf api request rest "/services/data/v64.0/app-framework/apps" \
  --method POST --target-org headless \
  --body '{"templateSourceId":"<id>","templateValues":{ ... }}'

# Poll the returned app's requestStatus until SuccessStatus (this takes MINUTES — see below)
```

**What to verify after Create:**
- `requestStatus: SuccessStatus`, and **every node `CompleteStatus`** (all `DataStreamRun`s,
  the SDM, every viz, the dashboard).
- Each DLO holds the expected **row count** with **real values** — for a date column, confirm
  values sort chronologically (`2014-01-03 → 2017-12-30`), not lexicographically
  (`1/1/2017 … 9/9/2017`), which would mean the date parse silently fell back to Text.
- The SDM's data objects resolved to the **chain-created DLOs** (the token bound), not to any
  hardcoded name.

**Timing expectation:** ingestion is fixed-latency-dominated (~330–340 s per stream
regardless of row count); streams run **serially**; total = ~875 s (~15 min) for a
3-stream app. If a `DataStreamRun` fails fast (~120 s, 0 rows), suspect **C1 (dates)** first
— the actual error is only in Data Cloud's Refresh History UX. Clean up test apps when done.

---

## Self-check before reporting done

- [ ] No hardcoded `…__dll` / physical asset name anywhere in shipped JSON (T1)
- [ ] Every cross-asset ref is an `${App.…}` token keyed to a chain node (T2, T3)
- [ ] CSV dates are ISO `yyyy-MM-dd`; datastream `format` matches; column typed `Date` (C1)
- [ ] Datastream source fields use camelCase `dataType` (C2)
- [ ] Each `DataStreamRun` sources only its own upsert; no parallel barrier (X1)
- [ ] SDM node depends on all `DataStreamRun`s (X2)
- [ ] Optional branches fully conditioned, both node and its children (X3)
- [ ] `template-policy.json` present (S2)
- [ ] Deployed whole dir; created + verified in a CLEAN org, end-to-end (D1)

---

## References

| Reference | Path | When to read |
|-----------|------|--------------|
| **Minimal + full menu** | `appTemplates/CSV_Example/` | **Read first** — mirror shapes; never edit |
| **Realistic, DLO-only** | `appTemplates/superstore_demo_template/` | Multi-CSV, relationships, dates-gotcha survivor |
| Case study | `docs/appTemplates/SUPERSTORE_DEMO_COMPLETENESS.md` | Ingestion debugging, ruled-out dead-ends, timing |
| Human on-ramp | `docs/csvDataTemplates/README.md` | To understand the pieces |
| Extension templates | `docs/gettingStartedWithExtensionTemplates/` | The complementary "wrap a viz LWC" track |
