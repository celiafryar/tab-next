# Tab Next

A Claude Code **plugin marketplace** of pro-code skills for building **Tableau Next / Salesforce Data 360** analytics as code. Load CSVs into Data Cloud with the right keys and types, build and deploy semantic models, define relationships and cardinality, assign geographic roles, wire up workspaces, and teach the agent your business language. Everything is version-controlled in Git and tuned for **Tableau Pulse** and **Agentforce**.

> A marketplace is simply a Git repo that Claude Code can install plugins from. You add this repo once, install the plugin below, and its skills load automatically. They trigger on their own when you work on Tableau Next assets, or you can call one by name (for example, `/tableau-semantics-dx` or `/tbx-dataobject load`).

---

## What you get

This marketplace ships **two plugins**, split by what you are trying to do:

| Plugin | Install it to | Skills |
|---|---|---|
| **`tableau-next-semantics`** | **Build the model.** Load data, author and deploy semantic models, relationships, geo roles, metrics, and Business Preferences. | 13 |
| **`tableau-next-app-templates`** | **Ship the app.** Package a finished app as an installable template that carries its own CSV data and rebuilds itself in any org. | 1 |

They chain: build with the first, distribute with the second. Install either alone or both.

Installing **`tableau-next-semantics`** adds **thirteen skills** in two families. Both families share one philosophy: retrieve real state, change it deliberately, verify the change landed, and commit only verified states.

### The semantic authoring family

The original six field-tested skills. They ride on the Salesforce CLI plus the **Salesforce Tableau Semantics** VS Code extension, and carry the platform knowledge that otherwise costs a day of trial and error each.

| Skill | The value it delivers | It kicks in when you |
|---|---|---|
| **tableau-semantics-dx** | The core pro-code loop: retrieve a model as JSON, edit, validate, deploy. Carries the platform know-how from the 255-character description cap to what actually controls join cardinality. | edit a retrieved `Semantic Models/...` folder, author calculated fields or descriptions, deploy, or debug a deploy error. |
| **semantic-descriptions-from-spreadsheet** | Turns a metadata workbook into agent-ready descriptions for hundreds of fields at once and writes them into the model. The highest-leverage thing you can do for Tableau Agent and Pulse answer quality, and unbearable by hand. | have a data dictionary and want conversational analytics to map questions to the right fields. |
| **tableau-semantic-relationships** | Authors joins and cardinality directly in `relationships.json`, outside the model canvas. Knows why Many-to-One gets refused, and checks the graph is acyclic before you spend a deploy finding out. | build or fix relationships from a cardinality spec, or hit `CYCLIC_RELATIONSHIP_ERROR` or a cardinality rejection. |
| **tableau-semantic-geo-roles** | Assigns geographic roles so place-name fields map and the agent can answer geography questions. Gets the two-property mechanism right, and knows which look-geographic-but-aren't fields to leave alone. | have city, state, country or coordinate columns, or maps and geography questions are not working. |
| **tableau-business-preferences** | Authors and tests the instruction file that teaches the agent business language, intent and safe defaults. Carries what live testing proved about which instructions the agent actually obeys, which is not what the documentation implies. | the agent misreads a word, returns a right number that answers the wrong question, or ignores an instruction. |
| **snowflake-dbt-to-semantic-metadata** | The front end for migrations: pulls existing descriptions, types and keys out of Snowflake or a dbt project and normalizes them into the workbook the other skills consume. Stops you retyping metadata the customer already wrote. | migrate an existing Snowflake or dbt semantic layer into Tableau Next. |

### The `tbx-*` lifecycle family

Seven newer skills that run the full asset lifecycle **entirely over REST**. No VS Code extension is required for anything in this family; the Salesforce CLI alone does it all. Start with `/tbx` and it routes to the right specific skill.

| Skill | What it does | Status |
|---|---|---|
| **tbx** | Orchestrator. Owns the end-to-end sequences: build a workspace from raw CSVs, or digest an existing workspace and recreate it elsewhere. | routes to the family |
| **tbx-dataobject** | Loads CSV files as data streams and Data Lake Objects over the documented Connect REST API, including the load-time primary key that Many-to-One cardinality depends on. Its `prep` verb is a pre-load audit of keys, types, category, and headers, all of which are permanent after load. | verified live |
| **tbx-semantic-model** | Creates, reads, modifies, and deletes semantic models through granular per-item endpoints instead of the dangerous full-model PUT. Create is three fields; objects, calcs, metrics, and relationships are one POST each. | verified live |
| **tbx-datatransform** | Combines and reshapes Data Lake Objects with Batch Data Transforms, including UNION, which Data Cloud calls APPEND. Covers the STL definition format and the field-alignment rules that decide whether a union produces real rows or silent nulls. | verified live; STL export/import round-trip not yet exercised |
| **tbx-workspace** | Creates workspaces, attaches assets to them, and digests what an existing workspace holds. Create and attach ride on Aura actions the UI uses, since no documented REST path exists yet. | partial: create and attach verified, digest designed but not yet exercised |
| **tbx-viz** | Reads, versions, and ports visualizations. The real chart spec is the Metadata API's `.uaviz-meta.xml`, whose `visualSpecification` is base64-encoded JSON holding marks, encodings, axes, and all formatting. | partial: reading verified live, create not yet exercised |
| **tbx-dashboard** | Digests dashboard structure: pages, widgets, layouts, grid geometry, and which dashboards use a metric before you rename it. Retrieves the whole dashboard as a `.uadash-meta.xml`. | partial: retrieve verified live, create validated but not yet performed |

The status column is honest by design. "Verified live" means exercised against a live org with the result checked; "partial" and "unsolved" mean exactly that. Open threads live in `TBX-TODO.md` at the repo root.

### The app packaging plugin

Installing **`tableau-next-app-templates`** adds **one skill**. It answers a different question from everything above: not "how do I build this model" but "how does someone else get this whole app, data included, in their own org."

| Skill | The value it delivers | It kicks in when you |
|---|---|---|
| **author-csv-data-template** | Turns a finished analytics app into an **App Template Framework** template that ships its own CSVs. On Create it assembles the entire stack bottom-up in any org: CSV to Data Stream to Data Lake Object to Semantic Model to visualizations to dashboard, with nothing pre-existing. Carries the two rules that decide whether a template travels: every cross-asset reference must be a `${App....}` token rather than a physical `__dll` name, and shipped CSV dates must be ISO `yyyy-MM-dd` or the whole stream is rejected with zero rows and an error visible only in Data Cloud's Refresh History. | want to package a dataset and dashboard as a one-click installable app, or you have a template that only works in the org it was exported from. |
| **package-tn-template** | Takes a template that runs clean when source-deployed and turns it into a **released managed 2GP** with proof: preflight for the traps a managed install springs (ContentAsset names, `c:` extension references, null chain names, `minorVersion`, `runAs`), build on the Dev Hub, install into a clean non-namespaced org, run Create App with a detached monitor, verify the dashboard resolved the packaged component, promote. Ships the scripts and a gotchas file with the evidence behind every rule. | you need an install link, a managed package, or a template that works in the dev org but fails after install. |
| **tn-security-review** | Prepares a released version for the AppExchange security review: Code Analyzer with the AppExchange rule sets, the Checkmarx MDAPI zip, a chain and LWC audit for what reviewers grep for, and the five reviewer documents (Solution Architecture, Reviewer's Guide, Code Analyzer notes, API callouts, notes) generated from templates and rendered to PDF. Includes the review-org setup and the Partner Console hand-off list. | you have a promoted 04t and someone asked for the review documents. |

It bundles the `CSV_Example` and `superstore_demo_template` reference implementations plus the Superstore case study under `references/`, so the file shapes are on disk rather than described. The **proven path** is documented separately: `references/proven-path.md` in the skill is the verified build-package-install-verify recipe (1GP unmanaged package, installation URL, the three install errors and their fixes), and `docs/Sales-Opportunity-Insights-Proven-Path.html` at the repo root is the evidence walkthrough with the primary-source payloads behind every step. It also covers the no-code route, Tableau Next's Templates page and Create App, whose silent failures (cross-workspace visualizations dropped from the closure, the semantic model never included, one-app-per-asset claims that survive app deletion) all surface as one misleading `ACCESS_DENIED` on the dashboard; the skill decodes it and gives the recipe that installs. **Origin:** the Salesforce `aftest` template pack, redistributed here rather than XeoMatrix-authored; see `references/PROVENANCE.md` in the skill.

**The families chain.** Extract metadata with the Snowflake/dbt skill or start from a workbook. Load the files with `tbx-dataobject`, getting keys and types right the one time that matters. Build the model with `tbx-semantic-model` or the VS Code loop. Describe, relate, and geo-role it. Wire it into a workspace. Then teach the agent how the business speaks with Business Preferences, and test it against a precomputed answer key. Each step hands the next a known shape.

---

## Prerequisites

For everything:

- **Salesforce CLI** (`sf`), installed and authorized to your org.
- A Salesforce org with **Data 360 and Tableau Next** provisioned.
- **Git**, for versioning the model.

Additionally, for the authoring family's retrieve/deploy loop:

- **VS Code** (or Cursor) with the **Salesforce Extension Pack** and the **Salesforce Tableau Semantics** extension. The extension has nineteen commands, including Create and Deploy New Semantic Model, Clone and Retrieve Remote Model, ERD visualize and compare, and Test Model; the quick start below uses three of them.

The `tbx-*` family needs none of the VS Code tooling.

Tip for org login: `sf org login web` against the generic login page can time out. Target your org's own domain instead:
`sf org login web --instance-url https://YOUR-DOMAIN.my.salesforce.com --alias my-org --set-default -b chrome`.

---

## Install

```text
/plugin marketplace add celiafryar/tab-next
/plugin install tableau-next-semantics@tab-next
/plugin install tableau-next-app-templates@tab-next
/reload-plugins
```

Install either plugin on its own. Take `tableau-next-semantics` to build models, and add `tableau-next-app-templates` when you are ready to hand the finished app to someone else.

This repo is **private**, so you need read access to it (you will authenticate with your GitHub account or `gh`). See **Access** below.

## Manage and update

Use the `/plugin` menu to add, update, disable, or remove marketplaces and plugins, then run `/reload-plugins` to apply. When this repo publishes a new version, update the marketplace and reinstall the plugin to pull the change.

---

## How it works

### Path A: author and deploy with the VS Code loop

1. **Retrieve** the target model in VS Code: right-click the `Semantic Models` folder, then **Tableau Semantic: Retrieve Model to Folder**. This writes a folder of JSON files. Commit it as your baseline.
2. **Provide the input** the skill asks for: a metadata workbook for descriptions, a cardinality spec for relationships. Each skill prompts and confirms what it found before changing anything.
3. **Let the skill edit the JSON** (`dataObjects.json`, `relationships.json`, `calculatedDimensions.json`, and so on), resolving your model by field and table labels.
4. **Validate and deploy** from the extension: right-click `model.json`, then **Validate Model**, then **Deploy Model**.
5. **Retrieve again, then commit.** The retrieve is what proves the change landed and captures the IDs the server assigns. Commit only verified states.

### Path B: build from raw CSVs over REST

1. **`/tbx-dataobject prep`** audits every file first. Primary key, field types, and category are permanent after load, so the skill asks about anything that looks off rather than choosing silently.
2. **`/tbx-dataobject load`** creates one data stream per file with the primary key set at load time, runs the ingest, and reconciles processed row counts against the source.
3. **`/tbx-semantic-model create`** makes the model (three fields), then adds one data object per table with `shouldIncludeAllFields: true`, then relationships one POST each.
4. Descriptions, calculated fields, metrics, and preferences follow through the authoring family.
5. **`/tbx-workspace create` and `attach`** wire the model and its data objects into a workspace. Attach both, or the workspace looks empty.

A blank intake template for the description workflow (tables, fields, roles, primary keys, relationships, business synonyms) can be produced by the `semantic-descriptions-from-spreadsheet` skill on request.

---

## Capabilities and hard-won rules

The skills already encode these. They are worth knowing anyway, because most are not documented anywhere else. Every one traces to a live incident, not a hunch.

### Ingest and Data Lake Objects

- **Ingest-time decisions are permanent.** Category, primary key, and field types cannot be changed after the stream is created. The `prep` checklist exists because every one of these is catchable before load.
- **The load-time primary key is the real Many-to-One mechanism.** Assign it while loading (`dataLakeObjectInfo.fields[].isPrimaryKey: true` over REST, or the wizard's Primary Key picker) and `cardinality: "ManyToOne"` simply works. Skip it and Data Cloud mints a `uuid_temp` row ID that can never be reassigned.
- **The wizard requires a primary key but never checks uniqueness.** Duplicate keys silently merge rows and the run still reports `SUCCESS`. The only signal is `lastProcessedRecords` disagreeing with `totalRecords`. Watch for the literal string `NULL` used as a sentinel.
- **Category defaults to `PROFILE`; reference data wants `OTHER`.** Immutable after save, with billing implications.
- **File upload accepts 2 GB and 1,050 columns.** A widely cited 150 MB figure is wrong; files over 100 MB just take longer.
- **Deleting a stream does not delete its staged file.** So fixing wrong types or keys is cheap: delete the stream, recreate it against the same staged file with corrected types, and never re-upload.
- **`mappings` renames a column at create time without re-uploading.** A misspelled header (`longtitude`) becomes a clean DLO column by mapping `sourceFieldLabel` to `targetFieldName`; only the lineage side keeps the typo.
- **"Loaded" means rows, not HTTP codes.** A 200 on a staging upload proves S3 accepted an object, nothing more. A load is proven when `lastRunStatus` is `SUCCESS`, `totalRecords` equals the source row count, and `lastProcessedRecords` equals `totalRecords`. When the number matters, spot-check a value through the SQL API too.
- **A union is called APPEND**, and it maps by column name: any name or type mismatch silently fills that column with nulls instead of erroring. Align sibling sources before building the transform.
- **Strip the `.csv` suffix from object labels.** File-upload tables arrive labeled with the filename, and it leaks into the object list, agent answers and any generated documentation. It cannot be fixed at ingest, only in the model.
- **One file, one DLO, three names.** `Product.csv` becomes DLO `Productcsv__dll` and semantic apiName `Product_csv`. All three differ; SQL wants the DLO name, model payloads want the apiName. Record the mapping.

### Building and deploying models

- **Match by label, not API name.** Data Cloud makes field API names globally unique per org, so `Sales` becomes `Sales2` and `Account.csv` becomes `Account_csv1`. Resolve by label, then use the real API name.
- **A full-model PUT is full state.** Any item missing from the payload is deleted on the org, so deploying from a stale read silently destroys whatever anyone else changed since your GET. Re-GET immediately before every PUT, and diff.
- **Granular endpoints remove most of that hazard.** Every collection under `/ssot/semantic/models/<model>/` (data-objects, relationships, calculated-dimensions, calculated-measurements, metrics, groupings, parameters) accepts single-item POSTs, so incremental changes never need the full PUT.
- **Granular endpoints cover collections, not field properties.** Descriptions, visibility, geo roles, and the primary name field live on fields inside the object payload, and `shouldIncludeAllFields: true` creates fields at platform defaults. A full migration therefore still ends with one careful PUT, built from a fresh GET of the target with source properties overlaid.
- **Resolve field API names per object, never through a global map.** The same label on two tables mints suffixed names non-deterministically (`NetRevenue` on one table, `NetRevenue1` on the other), and a first-match lookup once silently pointed 16 calculated fields and 4 metrics at the wrong table.
- **Descriptions cap at 255 characters**, field and table alike. Validate passes even when one is too long; only Deploy catches it. Enforce the cap when generating.
- **`isPrimaryKey` lies in the semantic layer.** It is read-only there, and reads `false` even on a field that genuinely is the primary key. Never conclude a model has no keys from that flag. (At ingest time, in the data stream payload, the same flag is writable and truthful. Two layers, same name, opposite behavior.)
- **A deploy can run, send a correct payload, and change absolutely nothing.** Deploys are atomic, so one bad property anywhere rejects the whole model, and the extension logs the request but never the response. Check whether the model's last-modified date actually moved, then replay the logged payload to see the real error.
- **Validate can report "0 validation errors" directly above real errors.** The top-level array is empty while the actual problems sit nested under `subResources`. If there is a warning triangle, read the JSON.
- **Deploying cleanly is not evidence that a formula evaluates.** Syntax can parse, validate, and deploy and still return nothing useful. Put the measure on a worksheet and check it against a number you computed independently before recording anything as confirmed.
- **Hide system and lineage fields** with `isVisible: false`: `cdp_sys_*`, `KQ_*`, `Data_Source*`, `Internal_Organization*`, `uuid_temp*`. Five or six per file-upload table, and they otherwise clutter every field list the agent reads.
- **Cross-org porting is essentially one clone operation.** Cloning a model into another org preserved all 184 field apiNames byte for byte, including the old collision suffixes, so nothing needed rewriting. Two gotchas: `agentEnabled` arrives `false`, and the extension's clone mints a permanent `_copy` apiName; creating clean over REST avoids the suffix.

### Relationships

- **The relationship graph must be acyclic.** Two fact tables sharing several dimensions is a cycle; make one fact the hub.
- **You can change an existing relationship's cardinality but not its left (child) side**, so re-orienting one means delete and recreate.
- **Many-to-One comes from the load-time primary key**, not from anything in the semantic layer. `primaryNameField` is the fallback for models loaded without a key; otherwise leave it for its real job, the record's display name.

### Metrics

- **A metric's API name is minted from its label at creation and never updates.** Rename a metric and the API name keeps the old word forever. To rename meaningfully, delete and recreate. Metrics also have no visibility flag, so deletion is the only way to remove one.
- **A metric's aggregation must equal its calculation's,** or the metric silently shows nothing, while both objects validate individually. The calculation still works on a worksheet, so "the calc is fine" doesn't clear the calc.
- **A metric cannot slice below its measure's grain.** An opportunity-level measure broken down by product counts each deal once per product family it contains; one real model returned $1.06B against a true $393.87M. The fix is a second measure at the finest grain. The self-check worth teaching the agent: a breakdown must add up to the same total as the whole.
- **Never allow a metric dimension reached through a one-to-many hop.** It multiplies the measure. A contact attribute on an opportunity-grain metric can inflate it by nearly 2x.
- **Metrics can build on your calculated measures** via `measurementReference.calculatedFieldApiName`, or point straight at a raw column via `tableFieldReference`. Polarity lives at `insightsSettings.sentiment`, and there is no display-format property at all; a tile's number format lives on the dashboard widget.
- **The "lower is better" sentiment enum is `SentimentTypeUpIsBad`,** not the `DownIsGood` you would guess. A wrong enum fails the entire atomic deploy.
- **"Error when loading invalid metric" usually means a stale dashboard, not a broken metric.** A metric created after a dashboard exists fails only in that dashboard while validating clean everywhere else. Hard refresh, re-add the widget, or use a new dashboard.

### Geography

- **A geographic role is two properties**, not one. `dataType` must become `"Geo"` and `semanticDataType` must hold the role, while `storageDataType` stays as it was. Setting only the second is the usual mistake.
- **A geo-roled field cannot be a metric dimension.** Metrics accept only Text, Number, Boolean, Email, PhoneNumber or Url. Governed metrics therefore break down by region and territory; direct questions about state still work fine.

### The agent and Business Preferences

- **Business Preferences govern method, not prose.** Which field, filter, population, scope and sort are obeyed reliably. Instructions about the wording of the narrative are largely ignored, because the platform owns the response structure.
- **Never prohibit without substituting.** "Do not call it revenue" fails, because the agent still has to answer something. Say what to use instead.
- **The narrative is the summary; the Sources panel is the receipt.** Sources carries Fields Used and Filters Applied and is the only precise part of an answer. Teach every user to open it.
- **Duplicate field labels cause silent wrong-field selection.** One real model had 19 of 109 labels appearing on more than one table, and Fields Used names a field without its table. No preference can disambiguate what the agent cannot distinguish.
- **Test the agent, not the model.** Validation passing proves nothing; every real defect surfaced by asking the agent live questions and checking the numbers against a precomputed answer key.

### REST and CLI mechanics

- **You can read and write the deployed model without the extension.** `sf api request rest "/services/data/v66.0/ssot/semantic/models/<apiName>?"` returns the whole thing including live Business Preferences, and `/validate?` answers whether the server considers the model valid.
- **Trailing `?` on every REST path.** Without it, some CLI versions return `NOT_FOUND` on perfectly valid paths.
- **`--body "@file"` needs the `@`, even on DELETE.** And redirect stdout to a file before parsing; the CLI's update notice corrupts JSON.
- **GET HTML-escapes strings** (`>` comes back `&gt;`) across expressions, descriptions, and preferences. PUT it back verbatim and the parser chokes on the `&`. Unescape recursively first. Granular POSTs of new items are unaffected.
- **The APIs are self-describing.** Unknown properties, missing required parameters, and bad enum values all come back named. Probe with a throwaway PATCH rather than guessing.
- **Listings paginate at 10 by default.** `/ssot/data-streams` returns `totalSize` and `nextPageUrl`, and a digest that trusts page one silently drops tables. Follow the pages and assert the count you collected equals `totalSize`.
- **A 401 "Session expired" from the extension is not dead auth.** The CLI's refresh token is almost always still valid: run any `sf` command to refresh, then retry.

---

## Known gaps

Stated plainly because pretending otherwise costs more later. Details and hypotheses live in `TBX-TODO.md`.

- **Dashboard creation is validated but unproven.** Every dashboard sObject is `createable: false`, which is why this was long recorded as unsolved. That was the wrong layer: `AnalyticsDashboard` is a Metadata API type (`.uadash`), all 24 dashboards in a test org retrieved cleanly on 2026-08-12, and a validate-only deploy under a new developer name returned `State: Created`. Nobody has deployed one for real or opened the result, so treat create as untested until someone does.
- **Staging a new CSV still requires a live browser session.** The REST stream create points at a file already staged in S3, and the presigned-credential call is Aura-only, so a Lightning session must move the bytes: the UI wizard today, with an in-page staging route proven live but not yet packaged into the skills. The Bulk Ingestion API would make ingest truly CLI-only, but it lives on a different host behind a Data Cloud token exchange and needs a connected app plus an Ingestion API connector the org does not have yet.
- **A REST-built model once refused to open in the model editor** (`markup://aura:noAccess`) while validating clean; the condition cleared unexplained, and a 2026-08-07 re-test with a fresh REST-built model opened cleanly. Kept on the verification checklist ("the model opens in the editor") rather than treated as a live bug; history in `TBX-TODO.md`.
- **Workspace create and attach ride on undocumented Aura actions.** They work, but treat them as evidence of what the UI does rather than a contract.
- **Dataspace filters fail against the `default` dataspace** via both UI and REST; they are likely intended for additional dataspaces.
- **DMO mapping (several DLOs presenting as one table) is not yet captured**, though the semantic layer demonstrably consumes DMOs.

---

## Repo structure

```text
tab-next/
  .claude-plugin/
    marketplace.json                 # the marketplace definition
  plugins/
    tableau-next-semantics/          # one plugin, thirteen skills
      .claude-plugin/
        plugin.json                  # the plugin manifest
      skills/
        tableau-semantics-dx/
        semantic-descriptions-from-spreadsheet/
        tableau-semantic-relationships/
        tableau-semantic-geo-roles/
        tableau-business-preferences/
        snowflake-dbt-to-semantic-metadata/
        tbx/
        tbx-dataobject/
        tbx-semantic-model/
        tbx-datatransform/
        tbx-workspace/
        tbx-viz/
        tbx-dashboard/
    tableau-next-app-templates/      # one plugin, one skill
      .claude-plugin/
        plugin.json                  # the plugin manifest
      skills/
        author-csv-data-template/
          SKILL.md
          references/                # CSV_Example + superstore_demo_template + case study
  README.md
  TBX-TODO.md                        # open threads and future ideas
```

The two plugins are split by purpose: **build the model** versus **ship the app**. The `plugins/` layout leaves room to add more Tableau Next plugins to this same marketplace later. Skill families beyond Tableau Next will live in their own marketplace repos.

---

## Org placeholders in the docs

The worked examples, runbooks, and captured API payloads in this repo were run
against real orgs. Every org identifier in them has been replaced with a
placeholder. Substitute your own values before running any command you copy from
these pages:

| Placeholder | Supply your own | Where to find it |
| --- | --- | --- |
| `{{YOUR_ORG_USERNAME}}` | Org login username | `sf org list` |
| `{{YOUR_ORG_ID}}` | 15-character Org ID | `sf org display` |
| `{{YOUR_USER_ID}}` | 15-character User ID | `sf org display --verbose` |
| `{{YOUR_USER_ID_18}}` | 18-character User ID | Setup > Users, from the record URL |
| `{{YOUR_ORG_DOMAIN}}` | My Domain host prefix | `sf org display` instance URL |
| `{{YOUR_TENANT_ID}}` | Data 360 tenant ID | the `parentDirectory` on any data stream |
| `{{YOUR_PUBLISHER_ORG}}` | Org alias that hosts the 2GP package | `sf org list` |
| `{{YOUR_DEV_ORG}}` | Org alias you develop against | `sf org list` |
| `{{YOUR_PROOF_ORG}}` | Org alias you install and prove into | `sf org list` |
| `{{YOUR_REFERENCE_ORG}}` | Org alias of a known-good reference run | `sf org list` |
| `{{YOUR_MIGRATION_ORG}}` | Org alias of the migration target | `sf org list` |

A payload showing `"UserName": "{{YOUR_ORG_USERNAME}}"` is captured output, not a
value to paste back. It shows the shape of the response you should expect from
your own org.

---

## Access

The repo is private. Anyone who adds this marketplace needs read access. To open it to everyone, make the repo public:

```text
gh repo edit celiafryar/tab-next --visibility public
```

---

## Maintaining this marketplace

Each skill's source of truth lives in `~/.claude/skills/`. This repo holds the distributed copies. When a skill changes:

1. Update the copy here, under `plugins/tableau-next-semantics/skills/` or `plugins/tableau-next-app-templates/skills/`, whichever plugin owns it.
2. Bump `version` in `.claude-plugin/marketplace.json` **and** in the owning plugin's `.claude-plugin/plugin.json`. The marketplace version covers the repo as a whole; each plugin versions independently.
3. Commit and push. Installers pick up the update through `/plugin`.

There is a third copy to keep in step: the backup in `celia-claude-sync/claude-skills/`, whose own README lists the skills. A skill change touches `~/.claude/skills/`, that backup, and this repo.

**Keep the claims true.** These skills are valuable because what they assert has actually been verified. When something turns out to be wrong, correct it everywhere rather than bolting on a caveat, and give any known-bug note an explicit re-test date so it gets deleted once the platform fixes it. A stale warning misleads as much as a wrong rule.

---

## Roadmap

- Automate file staging so ingest is truly CLI-only. The Bulk Ingestion API is the supported route; standing it up takes a connected app, a Data Cloud token exchange to the tenant's `c360a` host, and an Ingestion API connector in the org.
- Investigate the Metadata API as a supported dashboard-creation path.
- Capture DMO mapping, so sibling files can present as one table without duplicating storage.
- Exercise the Batch Data Transform export/import round-trip, and creating a transform over REST from scratch.
- Validate the Snowflake and dbt extraction skill against a live source and promote it from templates to confirmed.
- A controlled test of whether large Business Preferences files genuinely degrade latency, or whether the real variable is contradictory rules. The 30,000 character cap is far above any file we have built.

---

## About

Built by Cecilia Fryar, XeoMatrix. For team and partner use.
