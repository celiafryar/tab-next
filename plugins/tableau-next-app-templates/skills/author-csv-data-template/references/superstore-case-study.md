> **Bundled reference copy.** This file ships inside the `author-csv-data-template` skill.
> Paths have been retargeted to the skill's own `references/` folder. Sections pointing at the
> wider aftest project (Extension Templates, `tools/`, backup files) are noted inline as not
> included here. Original: the Salesforce aftest template pack.

# Superstore Demo Template — Completeness Analysis

**Goal:** bring `superstore_demo_template` up to the same "complete, self-contained app
template" bar as `CSV_Example` — a template that, from a clean org, uploads its own data,
builds the data layer, and lands all downstream analytics assets.

**Scope note (from the user):** `CSV_Example` is working and must **not** be modified — it
is the reference. **No DMOs were used** for the Superstore app (its SDM sits directly on
DLOs), so the DMO + mapping + DMO-based CI portion of the CSV_Example chain does **not**
apply here.

Analyzed 2026-08-06 against org `headless`. Both templates deploy under
`references/`.

---

## 1. What "complete" means — the CSV_Example reference

`CSV_Example` ships a full create-chain that builds everything from scratch, in order:

```
CSVUpsert → DataStreamUpsert (→ DLO) → DataStreamRun
          → [DMOUpsert → Mapping]              (DMO path — N/A for Superstore)
          → [CalculatedInsightUpsert → Run]    (CI path)
          → WorkspaceUpsert → SemanticModelUpsert
          → VisualizationUpsert ×2 → DashboardUpsert
```

Files backing it (13 assets + policy):

| Area | CSV_Example files |
|------|-------------------|
| **Data in** | `csvs/customers-100.csv`, `datastreams/csv_ingestion.json` |
| Data model (opt.) | `dmos/dmo.json`, `dmos/mappings.json` |
| Insight (opt.) | `cis/calc_insights.json` |
| Semantic | `sdms/sdm.json`, `workspaces/workspace.json` |
| Presentation | `visualizations/viz1.json`, `viz2.json`, `dashboards/dashboard.json` |
| Framework | `template-info.json`, `variables.json`, `layout.json`, `template-policy.json`, `create-chain.json`, `images/background.png` |

Two portability properties make it re-deployable in any org:
1. **The chain produces its own data.** The DLO is created by `DataStreamUpsert` at
   app-create time; nothing pre-exists in the org.
2. **Every cross-asset reference is a token, never a hardcoded name.** The SDM points at
   its data object via `${App.DataModelObjects.CustomersDMO.Name}`; vizzes/dashboard point
   at the SDM via `${App.SemanticModels.CustomersSemanticModel.Name/.Id}`; the workspace
   ref uses `${App.Workspaces.CustomersWorkspace.Name}`.

---

## 2. What Superstore has today

`superstore_demo_template` was generated **from an existing workspace**, so it captured
only the presentation half of the app:

| Present | Missing |
|---------|---------|
| `template-info.json` | `csvs/` (no source data) |
| `variables.json` (**empty `{}`**) | `datastreams/` (no ingestion) |
| `layout.json` (**empty `{}`**) | `images/` + `icons` (no preview/background) |
| `create-chain.json` (workspace→SDM→viz→viz→dashboard) | `template-policy.json` |
| `sdms/Superstore_Semantic_Model.json` (3 DLO objects, 2 rels, 3 rowCount measures) | — |
| `workspaces/Superstore_Demo_Workspace.json` | — |
| `visualizations/Radial_Viz.json`, `Spoke_Viz.json` | — |
| `dashboards/Demo_Dashboard1.json` | — |

Its create-chain **starts at `WorkspaceUpsert`** — there is no `CSVUpsert`,
`DataStreamUpsert`, or `DataStreamRun`. The SDM's three data objects reference
**hardcoded, org-specific hashed DLO names**:

- `Superstore_Orders26132319529__dll`
- `Superstore_People26132422965__dll`
- `Superstore_Returns26132334367__dll`

These exist in `headless` **only because the CSVs were loaded manually** (verified live:
Orders 9 994 rows, People 4, Returns 296). In a fresh org they won't exist, so the SDM —
and everything downstream — has nothing to bind to. **This is the core completeness gap.**

The good news: the SDM→viz→dashboard→workspace cross-references are **already tokenized**
(`${App.SemanticModels.Superstore_Semantic_Model.Name/.Id}`, `${App.Workspaces...}`,
`${App.Visualizations...}`), so the presentation layer is portable once the data layer
below it exists.

---

## 3. Gap list — what must be added

### 3.1 Source data — `csvs/` (REQUIRED)
Add the three CSVs (available in `~/Downloads/`). Headers → target DLO fields:

| CSV | rows | columns |
|-----|------|---------|
| `Superstore_Orders.csv` | 9 993 | Row ID, Order ID, Order Date, Ship Date, Ship Mode, Customer ID, Customer Name, Segment, Country, City, State, Postal Code, Region, Product ID, Category, Sub-Category, Product Name, Sales, Quantity, Discount, Profit |
| `Superstore_People.csv` | 2 | Person, Region |
| `Superstore_Returns.csv` | 295 | Returned, Order ID |

> **Sizing decision:** CSV_Example ships one small file (100 rows) and offers a `SampleSize`
> variable. Superstore Orders is 2.2 MB / ~10 k rows — fine to ship whole. No sampling
> variable needed unless we want to mirror CSV_Example's UX.

### 3.2 Data streams — `datastreams/` (REQUIRED) — one per object
Author **three** datastream definition files modeled on
`CSV_Example/datastreams/csv_ingestion.json`. Each needs, per that file's shape:
`datastreamType: CONNECTORSFRAMEWORK`, `connectorInfo.connectorDetails.name:
"UploadedFiles"`, a `sourceFields[]` list matching the CSV header, a
`dataLakeObjectInfo` block (name via `${App.DataLakeObjects.<X>DLO.Name}`, `fields[]` with
`name` = underscored column + `isPrimaryKey` on the key), a `mappings[]` source→target
list, `refreshConfig.refreshMode: TOTAL_REPLACE`, and `advancedAttributes` pulling
`${App.CSVs.<X>CSV.*}`.

Field-name/type notes derived from the live DLO schemas (so the SDM keeps binding):
- **Orders** — PK `Row_ID` (Text). Numeric: `Sales`, `Quantity`, `Discount`, `Profit`,
  `Postal_Code`. Dates: `Order_Date`, `Ship_Date` (`format: M/d/yyyy` — CSV uses
  `11/8/2016`, **not** the `yyyy-MM-dd` in CSV_Example). Rest Text.
- **People** — columns `Person`, `Region` (both Text). Pick a PK (`Person`).
- **Returns** — columns `Returned`, `Order_ID` (both Text). PK `Order_ID`.

### 3.3 Create-chain — prepend the data pipeline (REQUIRED)
Insert, **before** `upsert_workspace_...`, for each of the 3 objects, the node trio from
CSV_Example: `CSVUpsert` → `DataStreamUpsert` (with `dataLakeObject.name`) →
`DataStreamRun`. Then make `upsert_sdm_...`'s `sources` depend on the three
`DataStreamRun` nodes so the SDM builds only after all DLOs are populated.
No DMO/Mapping/CI nodes (Superstore uses none — §Scope).

### 3.4 SDM DLO references — de-hardcode (REQUIRED, the subtle one)
Replace the three hardcoded `dataObjectName` hashed values in
`sdms/Superstore_Semantic_Model.json` with tokens that resolve to the DLOs the chain
creates — i.e. `${App.DataLakeObjects.<X>DLO.Name}` (mirroring how CSV_Example's SDM uses
`${App.DataModelObjects.CustomersDMO.Name}`). Without this, the SDM stays bound to
`…26132319529__dll` and breaks in any org that isn't `headless`.
> **Verify:** confirm the ATF token namespace for a DLO created by `DataStreamUpsert` is
> `App.DataLakeObjects.<node>.Name` (CSV_Example proves `DataModelObjects` for a DMO; the
> DLO-name token should be validated against a create run or ATF docs).

### 3.5 Framework files (RECOMMENDED for parity)
- **`variables.json` is empty `{}`** → add `Create*` booleans / `LabelSuffix` if we want
  CSV_Example's conditional-node UX. At minimum it works as-is (all chain conditions are
  hardcoded `"true"`), but then the wizard exposes no choices.
- **`layout.json` is empty `{}`** → add a Configuration page (mirror CSV_Example) so the
  create wizard renders something; pairs with any variables added above.
- **`template-policy.json` is absent** → add the `AccessCheck / hasTemplateAccess: always`
  policy so the template is visible.
- **`icons` / background image** — `template-info.json` has no `icons` block; add a preview
  + `images/background.png` for a finished look (cosmetic).

### 3.6 Consistency nits (LOW)
- `assetVersion` differs (CSV_Example 66.0, Superstore 68.0) — leave at 68.0 unless the
  target org requires otherwise; just noting the divergence.
- Superstore declares **both** a Create and an Update chain pointing at the *same*
  `create-chain.json`; CSV_Example ships Create only. Confirm the Update reuse is intended.
- Chain `condition` values are literal `"true"` strings; if variables are added, switch to
  `${Variables.Create*}` like CSV_Example.

---

## 4. Priority summary

| # | Gap | Priority | Blocks a fresh-org install? |
|---|-----|----------|------------------------------|
| 3.1 | Add 3 CSVs | **Required** | Yes |
| 3.2 | Add 3 datastream defs | **Required** | Yes |
| 3.3 | Prepend CSV→DS→Run nodes; rewire SDM deps | **Required** | Yes |
| 3.4 | Tokenize SDM `dataObjectName` refs | **Required** | Yes (breaks outside `headless`) |
| 3.5 | variables + layout + policy + icons | Recommended | No (wizard is bare / may be hidden) |
| 3.6 | version / Update-chain / condition nits | Low | No |

**Bottom line:** Superstore has a correct, already-tokenized *presentation* layer
(SDM + 2 vizzes + dashboard + workspace) but is **missing its entire data-ingestion
layer** and its SDM is **pinned to org-specific DLO names**. Adding the 3 CSVs + 3
datastream definitions, prepending the CSV→DataStream→Run node trio per object to the
create-chain, and tokenizing the SDM's DLO references converts it from a
"snapshot of one org" into a portable, complete app template on par with CSV_Example. The
DMO/mapping/CI machinery in CSV_Example is intentionally **out of scope** (Superstore uses
DLOs directly). The framework files (variables/layout/policy/icons) are parity polish, not
install blockers — except that without a policy the template may not surface.

## 5. Decisions (resolved with user 2026-08-06)

1. **DLO name token — RESOLVED.** Reference DLOs via `${App.DataLakeObjects.<name>.Name}`,
   where `<name>` is exactly the `dataLakeObject.name` declared in that object's
   `DataStreamUpsert` node. Confirmed by two in-repo examples:
   - `CSV_Example/create-chain.json` node declares `dataLakeObject.name: "CustomersDLO"`.
   - `SObject_Example/create-chain.json` declares `"SObject_DLO"`, and
     `SObject_Example/dmos/mappings.json` references it as
     `${App.DataLakeObjects.SObject_DLO.Name}`.
   No repo SDM references a DLO *directly* (both examples front a DMO), so binding the
   Superstore SDM's `dataObjectName` to this token is **verify-on-first-create-run** — high
   confidence on the token shape, low residual risk it needs a slightly different form.
   Plan: name the three nodes' DLOs `Superstore_Orders_DLO`, `Superstore_People_DLO`,
   `Superstore_Returns_DLO`, and bind the SDM objects to
   `${App.DataLakeObjects.Superstore_Orders_DLO.Name}` etc.
2. **Sampling — RESOLVED: ship the full set.** Superstore is a canonical example; include
   all rows (Orders ~10 k / 2.2 MB, People 2, Returns 295). No `SampleSize` variable.
3. **Wizard UX — RESOLVED: mirror CSV_Example.** Populate `variables.json` + `layout.json`
   with the `Create*` toggles (+ `LabelSuffix`) so a dev/agent can select what to install.
   This template is a **learning sample for other devs and agents**, not a pure admin UX —
   showing the conditional-install pattern is a feature. Switch chain `condition`s from
   literal `"true"` to `${Variables.Create*}`.
4. **Update chain — RESOLVED: keep as-is.** Create + Update sharing one `create-chain.json`
   is a common, well-working pattern; keep it simple (single shared file) for the sample.

## 6. Build log & findings (2026-08-06 → 2026-08-07)

All six build steps were executed. Deploy is clean, all 3 CSVs upload, and — critically —
the **`${App.DataLakeObjects.<node>.Name}` token binding for an SDM data object is CONFIRMED
working**: the chain creates the DLO via `DataStreamUpsert` and the SDM/vizzes bind to it by
token. Two design risks from §5 are now retired:

- **Clean column naming CONFIRMED.** A datastream-created DLO produces
  `<datastream fields[].name>__c` **verbatim** (e.g. `Sales__c`, `Order_Date__c`,
  `Row_ID__c`, `Sub_Category__c`) plus fixed system columns (`cdp_sys_SourceVersion__c`,
  `DataSource__c`, `DataSourceObject__c`, `InternalOrganization__c`, `KQ_<PK>__c`). The
  original SDM's positional names (`Sales_r__c`, `OrderDate_c__c`) and `uuid_temp` dims were
  **manual-upload-wizard artifacts**, not what the datastream path produces — correctly dropped.
- **Name-collision resolution CONFIRMED benign.** On the 3rd run the DLO resolved to
  `Superstore_Orders_DLO1__dll` (Data Cloud appended `1` to avoid collision with a prior
  failed DLO). The `${App.DataLakeObjects.Superstore_Orders_DLO.Name}` token still resolved
  to the suffixed physical name — exactly why we never hardcode resolved names.

### 6.1 ROOT CAUSE FOUND & FIXED — non-ISO date parsing (was: Orders ingestion fails, 0 rows)

**Root cause (proven by controlled test):** the Orders datastream declared its two date
columns as `Date` with `format: "M/d/yyyy"` against source data like `11/8/2016`. Through the
template's `DataStreamUpsert`, that `format` hint does **not** take effect — Data Cloud parses
the values with its default (ISO) date parser, every date fails, and the whole stream is
rejected fast (~120–135 s, 0 rows). Decisive experiment: retyping both date columns as `Text`
made `run_orders_stream` **succeed** (`CompleteStatus`, 327 s, **9 994 rows loaded**) — the
*only* change. `CSV_Example` never hit this because its dates are already ISO `yyyy-MM-dd`.

**Fix (reference-aligned, keeps real Date semantics):** reformat the two date columns in
`csvs/Superstore_Orders.csv` from `M/d/yyyy` to ISO `yyyy-MM-dd` (transparent to the SDM — the
DLO still stores a `Date`), and set the datastream `format` to `"yyyy-MM-dd"` to match
`CSV_Example`. Kept the columns typed `Date` (not `Text`) so time-series analysis in the
SDM/vizzes works. Verified the CSV round-tripped cleanly (9 994 rows, 21 cols, quoted
product-name fields intact, LF endings).

> **Dead ends checked along the way (kept for future agents):**
> - The runtime *read* API serialises source fields with lowercase `datatype` and the working
>   manual stream shows `datatype`, but the **template deploy schema requires camelCase
>   `dataType`** (`DataStreamSourceFieldInputRepresentation`); lowercase fails deploy with
>   "Unrecognized field [datatype]". Casing was a red herring.
> - CRLF→LF + trailing-newline normalisation did not fix it (though LF is still preferable to
>   match the reference); the accented/smart-quote characters in product names are fine.

**Historical detail (pre-fix diagnosis):**

The **Orders** `DataStreamRun` node fails fast (~120–135 s) with 0 rows on every attempt;
People/Returns never run because Orders blocks first. `statusMessage` only says *"Check Data
Streams → Refresh History"*; **all API-exposed error fields are `null`**
(`ExternalStreamErrorCode`, `LastDataChangeStatusErrorCode`, `ProblemRecordsDataLakeObject`),
and the domino log just shows `kicked off … jobId null` → `FailTerminalStatus`. The actual
ingestion error lives **only in Data Cloud's Refresh History**, which is not queryable via
`/ssot/data-streams/{name}/refresh-history` (NOT_FOUND) nor via `DataStreamRefreshHistory`/
`MktDataStreamRefresh` sObjects (not supported). It **is** visible in the Data Cloud UX.

**Ruled out by controlled tests (see timing table):**
- **Not size.** A 200-row subset fails identically to the full 9 994 rows.
- **Not the mechanism / not a 120 s cap.** `CSV_Example` run through the *same* app-create
  path SUCCEEDS end-to-end (its `DataStreamRun` node alone runs 331 s and completes).
- **Not line endings / trailing newline.** Normalising Orders from CRLF→LF + adding a
  trailing newline (to match CSV_Example's proven-good byte format) did **not** fix it.
- **Not the definition shape.** The failed `Superstore_Orders_DLO` stream def is byte-identical
  (sourceFields, DLO field types, `UploadedFiles` connector, S3 parent dir) to the manually
  uploaded `Superstore_Orders` stream, **which loads all 9 994 rows fine**.
- **Not column names / spaces.** CSV_Example uses space-labelled headers (`Customer Id`,
  `First Name`) and succeeds; the manual Superstore upload uses the same style and succeeds.
- **Not data quality.** Strict scan of all 9 994 rows: every row has 21 columns, 0 non-numeric
  values in Number columns, 0 blanks, 0 malformed dates. Only non-ASCII content is legitimate
  (smart quotes + accented product-name chars), which the manual upload also had and accepted.

**Confirmed by the fix run (2026-08-07):** the ISO-date rebuild completed **end-to-end**
(`requestStatus: SuccessStatus`) — every node `CompleteStatus`: all 3 `DataStreamRun`s, the
SDM, both vizzes, and the dashboard. The resolved Orders DLO (`Superstore_Orders_DLO4__dll`)
holds **9 994 rows** with **real `Date` values** ordered `2014-01-03 → 2017-12-30`. Compare the
`Text`-typed control DLOs, which also hold 9 994 rows but whose "dates" sort lexicographically
(`1/1/2017 … 9/9/2017`) — proof the ISO fix preserves true date semantics, not just row loading.
People = 4 rows, Returns = 296 rows, as expected. **Blocker RESOLVED.**

> **Debug level (user asked "can you set it to 'finest'?"):** No. The app-create request only
> exposes a coarse `configuration.loggingLevel` (`InfoLevel`) on the domino runtime — there is
> no client-settable Apex/`finest` trace for the *server-side Data Cloud ingestion*. The only
> place the per-row ingestion error surfaces is Data Cloud's **Refresh History** UX, which the
> REST/sObject APIs do not expose. So diagnosis had to proceed by controlled experiment
> (Text-vs-Date, ISO-vs-`M/d/yyyy`, size, line endings) rather than by reading a verbose log.

### 6.2 App-create timing (for the size/row-count correlation the user asked about)

| Run | Template | Rows (Orders) | Bytes | Line ends | Result | Total wall | `DataStreamRun` node |
|-----|----------|---------------|-------|-----------|--------|-----------|----------------------|
| 1 | Superstore | 9 994 | 2.2 MB | CRLF | **FAIL** | 141 s | 120 s |
| 2 | Superstore | 200 | 46 KB | CRLF | **FAIL** | 176 s | 135 s |
| 3 | Superstore | 9 994 | 2.2 MB | LF | **FAIL** | 166 s | 125 s |
| 4 | CSV_Example | 100 (Customers) | 17 KB | LF | **SUCCESS** | 417 s | 331 s |
| 5 | Superstore (Text-date control) | 9 994 | 2.2 MB | LF | **SUCCESS** (Orders only) | — | 327 s (orders) |
| 6 | **Superstore (ISO-date fix)** | 9 994 | 2.2 MB | LF | **SUCCESS (full chain)** | **~875 s** | 340 s (orders) |

Run 6 is the definitive fixed build: 3 streams ingest **serially**
(Orders 340 s → People → Returns), then SDM + 2 vizzes + dashboard, for a **~875 s** total
wall time.

**Correlation read (final).** The **failing** Orders runs cluster at a ~120–135 s node duration
regardless of row count (200 vs 9 994) — a *fast rejection*, not throughput-bound work. The
**successful** ingestions all land ~327–340 s in-node — CSV_Example's 100 rows (331 s) and
Superstore's 9 994 rows (340 s) differ by only ~3 %, so ingestion is **fixed-latency-dominated**:
row count is **not** the driver at these sizes. What *does* scale the app-create total is the
**number of streams** (Superstore's 3 serial `DataStreamRun`s ≈ 3× the single-stream latency),
plus a modest tail for the SDM/viz/dashboard nodes.

### 6.3 Parallel-ingestion experiment — DOESN'T help, and breaks the SDM (2026-08-07)

**Hypothesis.** The three ingestions run ~6 min apart and the whole app takes ~20 min. Since
the three CSV→DataStream→Run branches are independent in the DAG, each `run_*_stream` fires as
soon as *its own* upsert finishes, so they land in different scheduler windows. Force them into
one window with a **barrier**: set all three `run_*_stream` nodes' `sources` to *all three*
upserts, so no run starts until the last upsert is done and all three kick off together.

**What happened.** The barrier worked mechanically — all three streams *refreshed at the same
time* — but the run **did not complete any faster**, and the app-create then **failed on the SDM
node**:

> `Failed to Create SDM … Creation of semantic entities ([Superstore_Orders1, Superstore_People1,
> Superstore_Returns1]) failed … The [dataType] field is missing.`

**Two conclusions:**

1. **The ~5-min spacing is Data Cloud's server-side ingestion scheduler tick, not a
   chain-ordering artifact.** Kicking all three runs off together didn't shrink wall time —
   Data Cloud serializes/aligns the batch-ingestion jobs on its own orchestrator regardless of
   when the chain enqueues them. **No `create-chain` topology can beat this**; the lever (if any)
   would be Data Cloud config, not the template. Parallelizing via `sources` adds complexity for
   zero time benefit.
2. **The barrier introduced an SDM metadata race.** A `DataStreamRun` reporting `CompleteStatus`
   means *rows loaded*, but the DLO's **field schema (with `dataType`s) can lag** that signal.
   The *serial* chain's natural ~6-min gaps let each DLO's schema fully materialize before
   `upsert_sdm` read it; compressing all three into one window made `upsert_sdm` read DLO field
   metadata before `dataType` had propagated → *"[dataType] field is missing."* The identical
   serial chain (Run 6) succeeds through this exact node — the **serial ordering is protective,
   not accidental**.

**Decision: reverted to serial** (`docs/appTemplates/backups/superstore_create-chain.serial.bak.json` (source project only, not bundled)
holds the barrier variant if ever needed; the shipped `create-chain.json` is serial —
each `run_*_stream` sources only its own upsert). Redeployed and confirmed clean.

> **Rainy-day follow-up (not tested):** re-run the timing with **larger CSVs** (e.g. 100k–1M
> Orders rows) to see whether ingestion stays fixed-latency-dominated or crosses into
> throughput-bound. If per-stream time stays ~flat with size, the ~5-min tick is a hard floor
> and the only way to cut total wall time is **fewer streams** (e.g. combining objects) — not
> parallelism. Worth confirming before anyone else reaches for the `sources` barrier again.

### Build order (once approved)
1. `csvs/` — copy the 3 full CSVs from `~/Downloads/`.
2. `datastreams/` — author 3 datastream defs (Orders/People/Returns) with correct field
   names/types (Orders dates `M/d/yyyy`; numerics Sales/Quantity/Discount/Profit/Postal_Code).
3. `create-chain.json` — prepend CSVUpsert→DataStreamUpsert→DataStreamRun per object;
   point `upsert_sdm` `sources` at the 3 `DataStreamRun` nodes; wrap nodes in `Create*`
   conditions.
4. `sdms/Superstore_Semantic_Model.json` — replace the 3 hardcoded `…__dll` names with
   `${App.DataLakeObjects.*_DLO.Name}` tokens.
5. `variables.json` + `layout.json` + `template-policy.json` (+ optional icons/background).
6. Deploy to `headless`, run app-create, and **verify the DLO token resolved** (the one
   residual unknown) + all downstream assets build.
