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

- **R1a: sweep a UI-exported template for org-resident references BY NAME, not just by id.**
  Record-id prefixes and `__dll` names are the easy half. Three consecutive Create failures
  (2026-08-18) were each caused by a reference that is neither:
  | Where | What | Symptom |
  |---|---|---|
  | `sdms/*.json` | `workspaceId`, `cacheKey` | `SemanticModelUpsert` fails `system.security.NoAccessException`. Reads like permissions; means "that record is not in this org" |
  | `dashboards/*.json` | an image widget naming a **ContentAsset** | `DashboardUpsert` fails `RESOURCE_CREATE_FAILURE ... ContentAsset not found`. One missing image kills the WHOLE dashboard, not just the widget |
  Strip `workspaceId` and `cacheKey` entirely; the chain already knows the workspace because
  the SDM node runs downstream of `WorkspaceUpsert`. Compare your SDM's top-level keys against
  a reference template's: anything extra is suspect.

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

- **R11: `style.fonts` is portable, `stylesheet` is not.** Two mechanisms style a chart and
  only one survives packaging:
  | | Carries | Packages? |
  |---|---|---|
  | `style.fonts` | color + size per element | **Yes** |
  | `stylesheet` | color + size + **weight** | **No.** Puts the chart past `assetVersion 67.0` |
  `stylesheet` is what the **UI formatting panel** writes. A chart carrying it is *silently
  dropped* from the bundle, and any dashboard widget pointing at it is emitted as a malformed
  `Rules.CurrentNode` placeholder that fails `DashboardUpsert`. **"Clear Styles" does not fix
  it**: it empties the rules and leaves `"stylesheet": {"rules": []}`, and the bare key still
  blocks. The only recovery is rebuilding the chart from scratch. So: **never restyle a
  template chart in the UI; edit `style.fonts` in the JSON.** Consequence: **bold is
  unreachable** on a packageable chart, since only `stylesheet` carries `weight`.
  Detect blocked charts with a read at 67.0; `DOWNGRADE_VERSION_ERROR` means it will be dropped:
  ```bash
  sf api request rest "/services/data/v67.0/tableau/visualizations/<Name>?" -o <org>
  ```

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
- **V4: a metadata-deployed template is INVISIBLE in the Tableau Next Templates UI.**
  `/tableau/template/<Name>` shows "Your template is empty" and Add Resources fails with
  "Unable to find the template source app id". The page resolves through
  `applicationSourceId`, which is **null** for anything deployed as metadata and only set when
  a template is authored in the UI from an app. Confirmed by contrast: a UI-authored template
  with **18** templated assets renders, while a metadata-deployed one with **38** shows empty.
  The template still works; Create reads the bundle directly. Warn users, they will think the
  package is broken.
- **V5: `chainDefinitions[].name` must be `null`**, never the chain's real name, or create-app
  fails `CHAINNOTFOUND`. A registered `dominoChainId` does NOT prove the chain is runnable;
  only a successful create-app does.
- **Cleanup is incomplete by design.** `DELETE /app-framework/apps/<id>?` (with a `--body`
  file, even on DELETE) removes the app's *assets*, streams and DLOs go, but the app record
  itself persists in the list, and a `destructiveChanges.xml` for the
  `AppFrameworkTemplateBundle` fails. Expect to clear the leftover shells in the UI.

## The Templates UI route: Template Builder and Create App (verified live, org clock 2026-08-14)

Everything above is the metadata route: author JSON, deploy the bundle, create through the API.
There is a second route entirely inside Tableau Next: **Templates page > Add Resources >
Create App**, watched from **Setup > App Hub > Monitor**. It is what a Salesforce partner brief
means by "use ATF bundles", it is what a non-developer will reach for, and it has its own set of
silent failures. Two consecutive apps installed cleanly through it in one org
(`Test 3`, 4 resources, 11 tasks; `test0072`, same shape) once these rules were followed, after
a full day of installs that all died on one misleading error.

- **U1: only Workspace and Semantic Model are selectable resource types.** The picker's type
  filter offers exactly `All Types`, `Workspace`, `Semantic Model`. Dashboards and visualizations
  can only enter a template through a workspace's dependency closure. There is no way to add a
  visualization by hand, so if the closure drops one there is no recovery in the UI.

- **U2: the closure keeps only assets whose HOME workspace is the one you selected.** The preview
  panel ("The template will include the following assets") lists the dashboard and every
  visualization it uses, wherever they live. On Select the toast says success and the resource
  list contains only the same-home assets. A dashboard in workspace B that uses visualizations
  created in workspace A (attached to B, which the product allows and which works fine for
  viewing) templatizes as workspace plus dashboard, with every visualization silently gone.
  Same visualizations, selected through their own home workspace, all persist. **Check the
  resource count after every Select**; it must match the preview.

- **U3: the closure never includes the semantic model.** It is not in the preview and it is not
  added. Add it yourself: Add Resources, filter `Semantic Model`, pick the model. Without it the
  first visualization task fails on execute with
  `Error processing expression "${App.SemanticModels.<Name>.Name}". Variable part [SemanticModels]
  not found in context map`, and the dashboard task never runs. The model does not have to live
  in the templatized workspace; it only has to be in the template.

- **U4: one app per asset, and deleted apps keep their claim.** Adding a workspace whose model is
  already owned by an app fails with
  `SemanticModel [...] is already part of a different app [1zA...]`. The owning app can be one
  that no longer exists: an `1zA` id absent from the Apps list still held its claim, which locks
  that model out of every future template. The app page has a **Decouple** action; use it before
  Delete. Build each template test on freshly created assets, and coordinate in a shared org,
  because two people templatizing the same model will collide on this.

- **U5: Table and Radial charts, and any chart carrying `stylesheet` (R11), poison the add.**
  Selecting a workspace whose closure includes them can do nothing at all: the dialog stays open,
  no toast, no error, and the underlying `aura.AppFramework.createAppAsset` call returns HTTP 200
  with the action error swallowed. The same closure added cleanly once, then failed silently on
  retry, so treat a Select that does not close as a rejected add, not a slow one. Keep
  packageable workspaces to Vizql and Map layouts styled through `style.fonts`.

- **U6: the misleading error, decoded.** `DashboardUpsert` failing with
  `403 [[ACCESS_DENIED ... Please add the necessary permissions to access dashboard]]` is not a
  permissions problem. It means the dashboard payload references a visualization that is not in
  the app context. Open the task's **Log View** at Finest and look at the POSTed dashboard JSON:
  the widget sources read `${App.Visualizations.${App.Visualizations[Rules.CurrentNode.name].Name}.Id}`,
  an unresolved placeholder, and the chain's context map shows `Workspaces` only. Every cause in
  U2, U3 and U5 ends here.

- **U7: the Monitor is the truth; the toasts are not.** Setup > App Hub > Monitor > the
  `Create <app>` event > click a task > Log View. The validate phase passes for a task that will
  fail on execute, so a green validate row proves nothing. Deleting a failed app also removes its
  events from the Monitor, so capture the log before cleanup. Every retry mints suffixed copies
  of the created assets (`Sales_Analysis1`, `Sales_Analysis2`), so use a new app name each time
  and expect to clean up.

- **U8: `runAs` was not the fix.** The successful chains ran their workspace, visualization and
  dashboard tasks as `autoproc@...` (Automated Process) and succeeded once the resources were
  complete. The partner-brief tip to set `runAs: Current User` addresses a different failure.

- **Contrast with V4:** a template authored in the UI renders in the Templates page with its full
  resource list; only metadata-deployed templates show as empty there.

The recipe that installs, in order: create a new workspace; create a new, never-templatized
semantic model; create the visualizations inside that workspace on that model, Vizql or Map only,
no UI restyling; create the dashboard in the same workspace from those visualizations; new
template, Add Resources > the workspace, verify the count; Add Resources > Semantic Model > the
model; Create App with a fresh name; read the Monitor. Success is one row per resource across
validate, execute and finish, all green, in about ten seconds.

## Self-check before reporting done

- [ ] No hardcoded `…__dll` / physical name in shipped JSON (R1)
- [ ] CSV dates ISO; datastream `format` matches; column typed `Date` (R2)
- [ ] Datastream source fields camelCase `dataType` (R3)
- [ ] Boolean columns declared `Boolean` on BOTH sourceFields and dataLakeObjectInfo.fields (R4a)
- [ ] Each `DataStreamRun` sources only its own upsert; no barrier (R5)
- [ ] SDM depends on all runs (R6); optional branches fully conditioned (R7)
- [ ] Swept the WHOLE bundle for org-resident names, not just ids and __dll (R1a)
- [ ] No chart carries a `stylesheet` key; every one reads clean at 67.0 (R11)
- [ ] `chainDefinitions[].name` is null (V5)
- [ ] `template-policy.json` present (R9)
- [ ] Deployed whole dir; verified end-to-end in a CLEAN org (R10)
- [ ] UI route: resource count matches the closure preview (U2); semantic model added by hand (U3);
      assets never claimed by an app (U4); Monitor Log View read for every failed task (U6, U7)

## References

| Reference | Path | When to read |
|-----------|------|--------------|
| **Minimal + full menu** | `references/CSV_Example/` | **Read first** — mirror; never edit |
| **Realistic, DLO-only** | `references/superstore_demo_template/` | Multi-CSV, dates-gotcha survivor |
| Case study | `references/superstore-case-study.md` | Ingestion debugging + timing |
| Human on-ramp | `references/csv-data-templates-guide.md` | Understand the pieces |
| Agent playbook | `references/FOR-CODING-AGENTS.md` | Rule-dense build + verify |
| Wrap a viz LWC instead | `wrap-tn-lwc-as-template` (aftest pack, not bundled here) | If packaging a component, not data |
