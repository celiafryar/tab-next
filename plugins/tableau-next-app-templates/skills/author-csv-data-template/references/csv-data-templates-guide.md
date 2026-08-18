# Getting Started with Tableau Next CSV Data Templates

You know analytics. You've loaded data, modeled it, and built dashboards on top. This
guide is about packaging that whole stack — **the data, the model, and the
visualizations** — as a template so that **anyone in a Tableau Next org can click Create
and get a working app that loads its own data from scratch**.

You do **not** need to be a Salesforce developer to follow this. Where Data Cloud, ATF, or
Salesforce plumbing shows up, we explain it in plain terms and point at a working example
you can copy. If you're using a coding agent (Claude Code, Cursor, etc.) to help — and we
assume most of you are — read this to understand the shape of the thing, then hand your
agent the companion doc: **[FOR-CODING-AGENTS.md](./FOR-CODING-AGENTS.md)**.

> **Sibling to the Extension guide.** If you want to package a *custom visualization LWC*
> as a configurable wizard, that's a different (and complementary) track — see
> [`docs/gettingStartedWithExtensionTemplates/`](../gettingStartedWithExtensionTemplates/README.md).
> This guide is about packaging *data + model + native vizzes* as an installable app.

---

## What is a "CSV Data Template", and why would I make one?

A **CSV Data Template** is an App Template Framework (ATF) template that, on Create, builds
an entire analytics app **bottom-up, from raw CSV files it ships with itself**:

```
CSV file(s)  →  Data Stream  →  Data Lake Object (DLO)  →  [Data Model Object + mapping]
             →  [Calculated Insight]  →  Semantic Model  →  Visualizations  →  Dashboard
```

The person installing it doesn't upload anything or wire anything up. They click Create,
and the platform:

1. **Uploads the CSVs** the template carries,
2. **Ingests them** through Data Streams into Data Lake Objects,
3. Optionally builds **Data Model Objects** + mappings and **Calculated Insights**,
4. Builds the **Semantic Model** on top,
5. Creates the **Visualizations** and a **Dashboard** that read it.

**Why bother?** Because "download this CSV, upload it here, then build a model, then…" is a
dozen manual steps that don't travel between orgs. A CSV Data Template turns a whole
analytics app into a *product* someone can self-install in one click — reproducibly, in any
Tableau Next org, with no pre-existing data.

**Two portability properties make this work** (memorize these — they're the whole game):

1. **The template produces its own data.** Nothing pre-exists in the target org. The DLO is
   *created* by the chain at Create time from the CSV the template ships.
2. **Every cross-asset reference is a token, never a hardcoded name.** The Semantic Model
   points at its data object via `${App.DataLakeObjects.<Node>.Name}` (or
   `${App.DataModelObjects.<Node>.Name}` for the DMO path); vizzes and the dashboard point
   at the model via `${App.SemanticModels.<Node>.Name/.Id}`. Because names are tokens, the
   template binds correctly no matter what physical names the org assigns.

---

## The two references in this pack

Everything below cites two real, working templates:

| Template | What it teaches |
|---|---|
| **`CSV_Example/`** | The **canonical, minimal** version. One small CSV (100 rows) → the *full* chain including the optional **DMO + mapping + Calculated Insight** path. Start here. |
| **`superstore_demo_template/`** | The **realistic** version. Three CSVs → three streams → a model with relationships → two native vizzes + a dashboard. Uses **DLOs directly (no DMO path)**. Shows what "complete" looks like on real data, plus a hard-won lesson about dates (below). |

Open both folders alongside this guide. `CSV_Example` shows the complete menu of node
types; `superstore_demo_template` shows a production-shaped app that omits the parts it
doesn't need. Together they cover the decision "which nodes do I actually need?"

> **`CSV_Example` is the reference — don't modify it.** Treat it as read-only truth. When
> you build your own, copy its shapes into a new folder.

---

## Anatomy of the template folder

A CSV Data Template is a folder of JSON plus the data and assets it ships. Here's
`CSV_Example`, annotated:

```
CSV_Example/
├── template-info.json      ← the template's identity card (label, description, preview)
├── variables.json          ← the QUESTIONS the wizard asks (sample size, what to build)
├── layout.json             ← how those questions lay out into a page
├── create-chain.json       ← the RECIPE: every step run on "Create", in dependency order
├── template-policy.json    ← visibility policy (without it, the template may not surface)
├── csvs/                    ← the raw data the template SHIPS and uploads
│   └── customers-100.csv
├── datastreams/            ← how each CSV is ingested into a Data Lake Object
│   └── csv_ingestion.json
├── dmos/                    ← (optional) Data Model Object + field mapping
│   ├── dmo.json
│   └── mappings.json
├── cis/                     ← (optional) Calculated Insight definition
│   └── calc_insights.json
├── sdms/                    ← the Semantic Model built on the data
│   └── sdm.json
├── workspaces/             ← the workspace the assets live in
│   └── workspace.json
├── visualizations/         ← native viz definitions
│   ├── viz1.json
│   └── viz2.json
├── dashboards/             ← the dashboard that lays out the vizzes
│   └── dashboard.json
└── images/                  ← background / preview imagery (cosmetic)
    └── background.png
```

The framework files (`template-info`, `variables`, `layout`, `create-chain`,
`template-policy`) are the same five you'd find in any ATF template. Everything else is
*payload* — the data and assets the chain assembles. Let's walk the ones that matter.

---

## 1. `create-chain.json` — the recipe (this is the heart of it)

The chain is a **directed graph of nodes**. Each node does one thing (upload a CSV, create
a stream, build the model…) and declares its `sources` — the nodes that must finish first.
The platform runs them in dependency order.

`CSV_Example`'s chain, in order:

```
update_csv           (CSVUpsert)            ← upload csvs/customers-100.csv
  └─ upsert_data_stream1 (DataStreamUpsert) ← create the stream + its DLO ("CustomersDLO")
       └─ run_data_stream1 (DataStreamRun)  ← ingest the rows
            └─ upsert_dmo   (DataModelObjectUpsert)  [condition: CreateDMO]
                 └─ dmo_mapping (Mapping)             [condition: CreateDMO]
                      └─ upsert_ci (CalculatedInsightUpsert) [condition: CreateCalculatedInsight]
                           └─ run_ci (CalculatedInsightRun)   [condition: CreateCalculatedInsight]
                                └─ upsert_workspace1 (WorkspaceUpsert)
                                     └─ upsert_sdm (SemanticModelUpsert)
                                          ├─ upsert_visualization1 (VisualizationUpsert)
                                          ├─ upsert_visualization2 (VisualizationUpsert)
                                          └─ upsert_dashboard1 (DashboardUpsert)
```

The node types you'll use, roughly in build order:

| Node type | What it does | Notes |
|---|---|---|
| `CSVUpsert` | Uploads a CSV the template ships | `parameters.file` points at `csvs/…` |
| `DataStreamUpsert` | Creates a Data Stream + its **DLO** | `parameters.dataLakeObject.name` **names the DLO** — remember this name |
| `DataStreamRun` | Ingests the rows | The slow node (fixed ~5 min latency per stream — see §"How long does Create take?") |
| `DataModelObjectUpsert` | (optional) Creates a **DMO** over the DLO | Only if you need DMO semantics |
| `Mapping` | (optional) Maps DLO → DMO fields | Pairs with the DMO node |
| `CalculatedInsightUpsert` / `…Run` | (optional) Builds + runs a Calculated Insight | |
| `WorkspaceUpsert` | Creates the workspace | Declares which assets it references |
| `SemanticModelUpsert` | Builds the Semantic Model | Its data-object refs must be **tokens** (see §3) |
| `VisualizationUpsert` | Creates a native viz | References the SDM by token |
| `DashboardUpsert` | Creates the dashboard | `sources` = the viz nodes it lays out |

**The key idea: `sources` encodes "wait for."** A node runs only after every node in its
`sources` list has completed. That's how "don't build the model until the data is loaded"
is expressed — `upsert_sdm.sources` transitively depends on the `DataStreamRun`.

**Conditions make nodes optional.** Each node can carry
`"condition": "${Variables.CreateDMO}"`. When the variable is false, the node (and thus its
branch) is skipped. That's how `CSV_Example`'s DMO and Calculated Insight become opt-in
without a separate template.

> **DLO path vs DMO path.** `CSV_Example` ships the *full menu* including the optional DMO +
> mapping + Calculated Insight nodes. `superstore_demo_template` **skips them entirely** —
> its Semantic Model sits directly on the DLOs. If you don't need DMO-level semantics,
> don't add the nodes. Fewer nodes = faster, simpler, less to break.

---

## 2. `variables.json` + `layout.json` — the wizard

Same two-file contract as any ATF template: `variables.json` says *what* to ask,
`layout.json` says *how it's arranged* (and the platform draws the left-nav automatically).

`CSV_Example` asks two kinds of question:

**A. What to build** — one `BooleanType` per optional branch, wired to the chain conditions:

```json
"CreateDMO": {
  "label": "Create DMO",
  "description": "Conditionally create and map DMO",
  "defaultValue": true,
  "required": true,
  "variableType": { "type": "BooleanType" }
}
```

Each of these maps 1:1 to a `"condition": "${Variables.CreateDMO}"` on the relevant chain
nodes. This is what makes the template a *teaching menu*: the installer can toggle branches
on and off and watch the chain change shape.

**B. How much data** — a `StringType` dropdown driving sample size:

```json
"SampleSize": {
  "label": "Sample Size",
  "required": true,
  "variableType": {
    "type": "StringType",
    "enums": ["100", "1000", "10000", "100000"],
    "enumsLabels": ["One Hundred (17 KB)", "One Thousand (170 KB)",
                    "Ten Thousand (1.7 MB)", "One Hundred Thousand (17 MB)"]
  }
}
```

Plus a free-text `LabelSuffix` so multiple installs don't collide on asset names.

> **Sizing decision (a real one you'll face).** `CSV_Example` offers a `SampleSize` variable
> because it's a demo of the *mechanism*. `superstore_demo_template` **ships the full data
> set** (~10k Orders rows) with no sampling variable, because it's a canonical dataset meant
> to look real. Both are valid — pick based on whether your point is "look how it works" or
> "look at this data."

`layout.json` is a single `Configuration` page with a two-column layout: the `Create*`
toggles down the left, `LabelSuffix` on the right, a background image, and a header line.
Nothing fancy — for a data template the wizard's job is just to gather a few switches.

---

## 3. The subtle part: tokenize every cross-asset reference

This is the one thing that separates "works in my org" from "works in *any* org," and it's
where snapshots-of-an-org go wrong. **Read this section twice.**

When you build a Semantic Model in the UI and then export it as a template, the SDM's data
objects point at **physical, org-specific DLO names** with hashes in them — e.g.
`Superstore_Orders26132319529__dll`. Those names exist *only in the org you exported from*.
In a fresh org, the chain creates DLOs with *different* physical names, and the hardcoded
reference binds to nothing. Everything downstream breaks.

**The fix:** replace every hardcoded name with a token that resolves to the asset the chain
creates. The token namespace mirrors the node that made the asset:

| You're referencing… | Use the token | Where `<Node>` is… |
|---|---|---|
| A DLO created by `DataStreamUpsert` | `${App.DataLakeObjects.<Node>.Name}` | the `dataLakeObject.name` on that node |
| A DMO created by `DataModelObjectUpsert` | `${App.DataModelObjects.<Node>.Name}` | the DMO node's `parameters.name` |
| A Semantic Model | `${App.SemanticModels.<Node>.Name}` / `.Id` | the SDM node's `parameters.name` |
| A Workspace | `${App.Workspaces.<Node>.Name}` | the workspace node's `parameters.name` |
| A Visualization | `${App.Visualizations.<Node>.Name}` / `.Id` | the viz node's `parameters.name` |

Concretely, `superstore_demo_template` binds its SDM's three data objects to:

```
${App.DataLakeObjects.Superstore_Orders_DLO.Name}
${App.DataLakeObjects.Superstore_People_DLO.Name}
${App.DataLakeObjects.Superstore_Returns_DLO.Name}
```

…where `Superstore_Orders_DLO` etc. are exactly the `dataLakeObject.name` values declared
in that template's `DataStreamUpsert` nodes.

> **Why tokens beat names, proven live:** on one build the Orders DLO physically resolved to
> `Superstore_Orders_DLO4__dll` (Data Cloud appended a suffix to dodge a collision with a
> prior failed run). The `${App.DataLakeObjects.Superstore_Orders_DLO.Name}` token still
> resolved to that suffixed name and everything bound correctly. A hardcoded name would have
> broken. **This is the entire reason we never hardcode resolved names.**

---

## 4. The dates gotcha (the single biggest time-sink — read before shipping any CSV)

Data Cloud's CSV ingestion parses date columns with an **ISO (`yyyy-MM-dd`) parser by
default**, and — critically — the datastream's `format` hint (e.g. `"M/d/yyyy"`) **does not
reliably take effect** through the template's `DataStreamUpsert`. If your CSV has US-style
dates like `11/8/2016`, every row fails to parse and the **entire stream is rejected fast
(~120 s, 0 rows)** with an error that only surfaces in Data Cloud's Refresh History UX — not
in any API you can query.

`superstore_demo_template` hit exactly this. The Orders stream failed on every attempt with
0 rows while `CSV_Example` (whose dates were already ISO) sailed through. The proof was a
controlled experiment: retyping the date columns as `Text` made ingestion succeed with the
*only* change being the type — confirming the dates were the culprit.

**The fix (and the rule for your CSVs):**

1. **Store dates in your shipped CSV as ISO `yyyy-MM-dd`.** Reformat before you ship.
2. Set the datastream `format` to `"yyyy-MM-dd"` to match.
3. Keep the column typed `Date` (not `Text`) so time-series analysis still works.

With that, Superstore's Orders DLO loads all 9,994 rows with real `Date` values ordered
`2014-01-03 → 2017-12-30`. `CSV_Example` never hit this because its dates were ISO from the
start.

> The full diagnosis (including every dead-end that was *ruled out* — size, line endings,
> column names, data quality) lives in
> [`docs/appTemplates/SUPERSTORE_DEMO_COMPLETENESS.md`](../appTemplates/SUPERSTORE_DEMO_COMPLETENESS.md).
> If you're debugging a stuck ingestion, read §6.1 there before guessing.

---

## 5. `template-info.json` + `template-policy.json` — identity and visibility

`template-info.json` is the identity card — `templateType: "App"`, a `label` and
`description` for the gallery, and pointers to the other files:

```json
{
  "label": "CSV Example Template",
  "description": "This template imports a CSV and creates downstream assets",
  "templateType": "App",
  "assetVersion": 66.0,
  "variableDefinition": "variables.json",
  "layoutDefinition": "layout.json",
  "chainDefinitions": [ { "type": "Create", "file": "create-chain.json" } ]
}
```

`template-policy.json` carries the visibility policy (an `AccessCheck` /
`hasTemplateAccess` rule). **Without a policy the template may not surface in the gallery
at all** — a common "I deployed it but can't find it" cause. Copy `CSV_Example`'s.

---

## How long does Create take? (set expectations)

Data-template Creates are **minutes, not seconds** — dominated by ingestion, not by your
chain's cleverness. Measured on real builds:

- A single `DataStreamRun` node runs **~330–340 s** whether it's loading 100 rows or 10,000
  — ingestion is **fixed-latency-dominated** at these sizes, not throughput-bound.
- What scales total wall time is the **number of streams**, run **serially**:
  `superstore_demo_template`'s three streams → SDM → 2 vizzes → dashboard totals **~875 s
  (~15 min)**.
- **Don't try to parallelize the streams** to speed this up. It was tried (a `sources`
  barrier firing all three runs at once); it didn't shrink wall time (Data Cloud aligns the
  jobs on its own scheduler tick regardless) **and** it broke the SDM node with a
  `[dataType] field is missing` race — the DLO schema hadn't fully materialized when the SDM
  tried to read it. **Serial ordering is protective.** Keep each `DataStreamRun` sourcing
  only its own `DataStreamUpsert`.

---

## Trying it end to end

You need a Tableau Next–enabled org (with Data Cloud) and the `sf` CLI authenticated
against it. Then:

```bash
# 1. Deploy the whole template folder.
sf project deploy start \
  --source-dir force-app/main/default/appTemplates/CSV_Example \
  --target-org <your-org-alias>

# 2. In the Tableau Next app, open the template gallery, find "CSV Example Template",
#    run the create wizard (pick a sample size, leave the Create* toggles on), Create.

# 3. Wait a few minutes. Open the resulting dashboard — it's reading data the
#    template loaded from scratch.
```

Prefer to drive it without the UI? You can POST a create directly to the platform's
`app-framework/apps` endpoint — that's exactly how these templates were verified. The
companion agent doc shows the `sf api request` recipe and how to read back what was built.

---

## Where to go next

- **Building with a coding agent** — hand it [FOR-CODING-AGENTS.md](./FOR-CODING-AGENTS.md).
- **The full Superstore case study** — every gap, decision, and dead-end that turned a
  one-org snapshot into a portable template:
  [`SUPERSTORE_DEMO_COMPLETENESS.md`](../appTemplates/SUPERSTORE_DEMO_COMPLETENESS.md).
- **Packaging a custom viz LWC as a wizard instead** — the complementary
  [Extension Templates](../gettingStartedWithExtensionTemplates/README.md) track.

---

## One-page glossary

| Term | Plain meaning |
|---|---|
| **ATF** | App Template Framework — Salesforce's way of turning assets into installable, configurable templates. |
| **CSV Data Template** | An ATF template (`templateType: App`) that ships CSVs and builds a full analytics app from them on Create. |
| **Chain** | The recipe run on "Create" — a dependency graph of nodes. |
| **Node** | One step in the chain (upload a CSV, run a stream, build the model…). |
| **`sources`** | A node's list of prerequisite nodes; encodes "wait for these to finish." |
| **Condition** | `${Variables.X}` on a node — skips the node (and its branch) when false. |
| **Data Stream** | Data Cloud's ingestion pipeline from a source (here, a CSV) into a DLO. |
| **DLO** | Data Lake Object — the raw ingested table the stream produces. |
| **DMO** | Data Model Object — a modeled layer over one or more DLOs (optional). |
| **Calculated Insight** | A precomputed metric built in Data Cloud (optional). |
| **SDM / Semantic Model** | Tableau Next's modeled view (tables, fields, relationships) the vizzes query. |
| **Token** | `${App.…}` reference that resolves to an asset the chain created — never a hardcoded name. |
| **`sf` CLI** | Salesforce's command-line tool for deploying and querying orgs. |
