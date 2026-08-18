---
name: author-csv-data-template
description: >-
  Author a Tableau Next CSV Data Template — an App Template Framework (ATF)
  template (templateType App) that ships CSV files and, on Create, builds a
  full analytics app bottom-up: CSV -> Data Stream -> Data Lake Object ->
  (optional Data Model Object + mapping + Calculated Insight) -> Semantic
  Model -> Visualizations -> Dashboard. Use when the user asks to package a
  dataset as an installable app template, build a create-from-CSV template,
  turn CSVs/a semantic model/a dashboard into a portable ATF app, author
  datastreams/create-chain for data ingestion, make an analytics app
  reproducible across orgs, or fix a template that only works in the org it
  was exported from. Distinct from wrap-tn-lwc-as-template (which packages a
  visualization LWC as a wizard).
---

# author-csv-data-template

> **Provenance.** This skill and its bundled `references/` come from the Salesforce **aftest
> template pack** (see `references/PROVENANCE.md`). The reference templates are read-only truth:
> mirror their shapes, never edit them. Bundled JSON only; the packs' sample CSVs and preview
> images were omitted for size.

## Purpose

Build an ATF **CSV Data Template**: a template that carries its own CSV data and, when a
user clicks Create in any Tableau Next org, ingests that data and assembles the whole
analytics stack on top of it — no manual upload, no pre-existing assets, no code edits.

This is the *data + model + native vizzes* track. For packaging a custom visualization
**LWC** as a configurable wizard, use `wrap-tn-lwc-as-template` instead.

Reference implementations (read them, mirror them):
- `references/CSV_Example/` — canonical, minimal, **full node
  menu** (incl. optional DMO + mapping + Calculated Insight). **Read-only — never modify.**
- `references/superstore_demo_template/` — realistic multi-CSV app
  on **DLOs directly**; dates-gotcha survivor.
Full write-ups: `references/csv-data-templates-guide.md` (human on-ramp),
`references/FOR-CODING-AGENTS.md` (rule-dense playbook), and the case study
`references/superstore-case-study.md`.

## Critical gates (must follow)

1. **Ship your own data; assume nothing in the target org.** The chain must *create* the
   DLO via `DataStreamUpsert` from a CSV under `csvs/`. Verify in a **clean** org, never the
   one you authored in.
2. **Never hardcode a resolved asset name.** No physical `…__dll` DLO name (or any hashed
   name) may appear in shipped JSON. If an SDM was UI-exported, it *will* contain these —
   you must replace them with `${App.…}` tokens.
3. **Confirm scope before writing files:** which CSV(s), which columns/types, and whether
   the Semantic Model needs a **DMO path** or sits **directly on DLOs**. Present this and
   get a "yes" before generating.

## Deliverable

```
<Template_Name>/
├── template-info.json      # identity card; templateType App
├── variables.json          # Create* toggles (↔ chain conditions) + optional SampleSize + LabelSuffix
├── layout.json             # Configuration page(s); platform draws left-nav
├── create-chain.json       # the dependency graph of nodes (the heart of it)
├── template-policy.json    # visibility policy — WITHOUT IT the template may not surface
├── csvs/                    # the raw data shipped (dates as ISO yyyy-MM-dd!)
├── datastreams/            # one ingestion def per CSV
├── dmos/ + cis/            # OPTIONAL — only if the SDM needs a DMO / Calculated Insight
├── sdms/                    # Semantic Model, data objects bound to ${App.DataLakeObjects...}
├── workspaces/             # the workspace
├── visualizations/         # native viz defs (reference SDM by token)
├── dashboards/             # dashboard (sources = viz nodes)
└── images/                  # background/preview (cosmetic)
```

## The rules that matter (each earned from a real failure)

### Tokenization (portability — #1 correctness issue)

- **R1 — Reference every asset by its chain-node token, never a physical name.**
  DLO → `${App.DataLakeObjects.<dataLakeObject.name on the DataStreamUpsert node>.Name}`;
  DMO → `${App.DataModelObjects.<DMO node name>.Name}`;
  SDM → `${App.SemanticModels.<SDM node name>.Name}`/`.Id`;
  Workspace → `${App.Workspaces.<node name>.Name}`;
  Viz → `${App.Visualizations.<node name>.Name}`/`.Id`.
  The DLO token key is the node's `dataLakeObject.name` (not the stream name, not the
  physical name). It resolves even when Data Cloud suffixes the physical name to dodge a
  collision (observed: `Superstore_Orders_DLO4__dll`).

### CSV / ingestion

- **R2 — Dates MUST be ISO `yyyy-MM-dd` in the shipped CSV.** The datastream `format` hint
  does NOT reliably override Data Cloud's default ISO parser through `DataStreamUpsert`.
  Non-ISO dates (`M/d/yyyy`) → every row fails → whole stream rejected fast (~120 s, 0 rows),
  error visible ONLY in Data Cloud's Refresh History UX. Fix: reformat CSV to ISO, set
  datastream `format: "yyyy-MM-dd"`, keep the column typed `Date` (not `Text`).
- **R3 — Datastream source fields use camelCase `dataType`.** The read API shows lowercase
  `datatype`, but the deploy schema requires `dataType`; lowercase fails deploy
  ("Unrecognized field [datatype]"). Do not copy casing from a read response.
- **R4 — DLO fields materialize as `<datastream fields[].name>__c` verbatim** (+ system
  columns). Name datastream fields with the clean names the SDM should bind to; don't invent
  positional names (those are manual-upload-wizard artifacts).

- **R4a: `Boolean` is a valid `dataType` and survives ingestion.** Neither reference template
  uses it, so it looks unsupported; it is not. Declared `Boolean` on both `sourceFields` and
  `dataLakeObjectInfo.fields`, a CSV column of `true`/`false` materializes as a real DLO
  `Boolean`, and `WHERE IsClosed__c AND NOT IsWon__c` evaluates as a predicate rather than a
  string compare. **This matters:** a semantic model whose logic reads `IF [Obj].[Flag] THEN`
  silently returns wrong numbers if the column lands as Text, and it does not fail loudly.
  Verified live 2026-08-18 (25 rows, every aggregate exact against source).
  Confirmed working set: `Text`, `Number`, `Date`, `Boolean`.

### Chain topology

- **R5 — Serial ingestion. Each `DataStreamRun` sources only its own `DataStreamUpsert`.**
  A `sources` barrier firing runs together does NOT reduce wall time (Data Cloud aligns jobs
  on its own ~5-min tick) and breaks the SDM node with `[dataType] field is missing` (schema
  race). Serial gaps are protective.
- **R6 — `SemanticModelUpsert.sources` depends (transitively) on every `DataStreamRun`.**
- **R7 — Optional branches fully conditioned.** `"condition": "${Variables.CreateX}"` on
  every node in the branch (DMO node *and* its Mapping, CI upsert *and* run).
- **R8 — `DashboardUpsert.sources` = its viz nodes; vizzes source the SDM node.**

### Structure / deploy

- **R9 — `template-policy.json` is mandatory** or the template may not surface. Copy
  `CSV_Example`'s.
- **R10 — Deploy the whole template directory**, never a subfolder.

## Workflow

```
- [ ] Step 1: Confirm CSV(s), columns/types, and DMO-path vs DLO-only
- [ ] Step 2: Prep CSVs — ISO dates (R2), LF endings, clean headers
- [ ] Step 3: Author datastreams (camelCase dataType R3, dataLakeObject.name R1, PK)
- [ ] Step 4: Author/fix SDM — bind data objects to ${App.DataLakeObjects...} (R1), strip __dll names
- [ ] Step 5: Author vizzes + dashboard (reference SDM by token)
- [ ] Step 6: Author create-chain — serial (R5), SDM sources all runs (R6), conditions (R7), dashboard (R8)
- [ ] Step 7: variables + layout (Create* toggles ↔ conditions) + template-info + policy (R9)
- [ ] Step 8: Deploy whole dir (R10); Create in a CLEAN org; verify end-to-end
```

Variable types: `BooleanType` (one per optional branch, wired to node conditions);
`StringType` + `enums`/`enumsLabels` (SampleSize dropdown — only if demoing the mechanism);
`StringType` (LabelSuffix). Write real `description` strings.

## Headless verification (never claim done without it)

See `references/FOR-CODING-AGENTS.md` for the narrative. The corrected mechanics, all
verified live 2026-08-18 against a v67.0 org. The older recipe gets three details wrong:

- **V1: Every `app-framework` path needs a trailing `?`.** Without it the endpoint returns
  `NOT_FOUND` and reads as "this org doesn't have the feature." It does.
  ```bash
  sf api request rest "/services/data/v67.0/app-framework/templates?" -o <org>   # list; find your id
  sf api request rest "/services/data/v67.0/app-framework/apps?" -o <org>     --method POST --body @body.json                                              # create
  ```
  `body.json`: `{"templateSourceId":"<1zD...>","label":"...","name":"...","templateValues":{...}}`
- **V2: The create response nests under `app`.** Read `d["app"]["id"]`, not `d["id"]`.
  A top-level read returns `None` and looks like a failed create.
- **V3: There is no `requestStatus` on the app record.** Do not poll it; it is absent, and
  `url` / `latestActivityUrl` / `assetUrl` come back null. **Poll the data stream instead:**
  `GET /services/data/v67.0/ssot/data-streams/<dataLakeObject.name>?` and watch
  `lastRunStatus` go `PENDING` -> `SUCCESS`. One stream took ~6.5 min end to end.
- **Then verify the DATA, not the deploy.** Query the DLO over the SQL API
  (`POST /services/data/v67.0/ssot/queryv2?`) and check row count and aggregates against the
  source file. Note its response `metadata` key order does **not** match the `data` array
  order. Zip them and you will mislabel every column.
- If a `DataStreamRun` fails fast (~120 s, 0 rows), suspect **R2 (dates)** first, because the real
  error is only in Data Cloud's Refresh History UX.
- **Cleanup is incomplete by design.** `DELETE /app-framework/apps/<id>?` (with a `--body`
  file, even on DELETE) removes the app's *assets*, streams and DLOs go, but the app record
  itself persists in the list, and a `destructiveChanges.xml` for the
  `AppFrameworkTemplateBundle` fails. Expect to clear the leftover shells in the UI.

## Self-check before reporting done

- [ ] No hardcoded `…__dll` / physical name in shipped JSON (R1)
- [ ] CSV dates ISO; datastream `format` matches; column typed `Date` (R2)
- [ ] Datastream source fields camelCase `dataType` (R3)
- [ ] Boolean columns declared `Boolean` on BOTH sourceFields and dataLakeObjectInfo.fields (R4a)
- [ ] Each `DataStreamRun` sources only its own upsert; no barrier (R5)
- [ ] SDM depends on all runs (R6); optional branches fully conditioned (R7)
- [ ] `template-policy.json` present (R9)
- [ ] Deployed whole dir; verified end-to-end in a CLEAN org (R10)

## References

| Reference | Path | When to read |
|-----------|------|--------------|
| **Minimal + full menu** | `references/CSV_Example/` | **Read first** — mirror; never edit |
| **Realistic, DLO-only** | `references/superstore_demo_template/` | Multi-CSV, dates-gotcha survivor |
| Case study | `references/superstore-case-study.md` | Ingestion debugging + timing |
| Human on-ramp | `references/csv-data-templates-guide.md` | Understand the pieces |
| Agent playbook | `references/FOR-CODING-AGENTS.md` | Rule-dense build + verify |
| Wrap a viz LWC instead | `wrap-tn-lwc-as-template` (aftest pack, not bundled here) | If packaging a component, not data |
