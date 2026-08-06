---
name: tbx
description: >-
  Orchestrator for the tbx-* Tableau Next / Data 360 skill family. Routes a request to the right
  specific skill (tbx-dataobject, tbx-semantic-model, tbx-workspace, tbx-viz, tbx-dashboard) and
  owns the end-to-end sequences — build a workspace from raw CSVs, or digest an existing workspace
  and recreate it elsewhere. Start here when the task spans more than one layer.
---

# tbx — Tableau Next end to end

Router for the `tbx-*` family. Load the specific skill you need rather than everything; each is
single-concern so a side-track doesn't cost you the rest.

## Which skill

| You want to… | Skill | Verbs |
|---|---|---|
| Audit CSVs, load them as data streams / DLOs, set the load-time primary key | **`tbx-dataobject`** | `prep` `load` `edit` `delete` |
| Create or change a semantic model, add objects / calcs / metrics / relationships | **`tbx-semantic-model`** | `create` `describe` `add` `deploy` `delete` |
| Create a workspace, attach assets, enumerate what a workspace holds | **`tbx-workspace`** | `create` `attach` `digest` |
| Read or build a visualization | **`tbx-viz`** | `read` `create` `recreate` |
| Read a dashboard (create is unsolved) | **`tbx-dashboard`** | `digest` |
| Formula syntax, metric rules, description authoring, geo roles | `tableau-semantics-dx` and friends | — |

## Sequence A — build from raw files

1. **`tbx-dataobject prep`** — audit every file first. Keys, types, and category are **permanent
   after load**. Ask the user about anything that looks off; do not choose silently.
2. **`tbx-dataobject load`** — one stream per file, then `actions/run`, then reconcile
   `lastProcessedRecords` against `totalRecords`.
3. **`tbx-semantic-model create`** — three fields, then `add` one object per table with
   `shouldIncludeAllFields: true`.
4. Relationships, descriptions, calcs, metrics — `tableau-semantic-relationships`,
   `tableau-semantics-dx`, `tableau-business-preferences`.
5. **`tbx-workspace create` + `attach`** — attach the semantic model *and* the data objects, or the
   workspace looks empty.
6. **`tbx-viz`**, then dashboards in the UI (create is not yet scriptable).

## Sequence B — digest an existing workspace and recreate it elsewhere

1. **`tbx-workspace digest`** — enumerate assets by type via `analytics.browse` on the documented
   GraphQL endpoint, or straight SOQL.
2. **`tbx-semantic-model describe`** — GET the model. **Unescape HTML** before reusing any string.
3. **`tbx-viz read`** — `AnalyticsVisualization` + its `AnalyticsVizField` rows.
4. **`tbx-dashboard digest`** — structure is readable; rebuilding is manual for now.
5. Recreate in dependency order: data objects -> semantic model -> workspace -> viz -> dashboards.
   Repoint `AnalyticsWorkspaceId` and any `SemanticObjectApiName` / `SemanticFieldApiName`.

## Cross-cutting rules
- **Trailing `?` on every REST path**, and **`--body "@file"`** with the `@`, even on DELETE.
- Redirect stdout to a file before parsing JSON; the CLI's update notice corrupts it.
- **Prefer granular writes** (`POST …/data-objects`) over the full-model `PUT`, which is full state
  and deletes anything you omit.
- **The APIs are self-describing.** Unknown fields come back named, missing required params come
  back named, bad enums come back named. Probe rather than guess.
- **Validation passing proves nothing.** Verify numbers against the source or the Data Cloud SQL API.
- Ingest-time decisions (primary key, category, field types) cannot be undone. Confirm them.

## Known gaps
- **Dashboard creation** — no supported path found. Try the Metadata API first.
- **File staging** — `POST /ssot/data-streams` needs a CSV already staged in S3; staging a new file
  still needs the UI. The Bulk Ingestion API is the likely fix.
- **Workspace create/attach are Aura**, not documented REST.
- **Dataspace filters** fail against the `default` dataspace; likely intended for additional ones.

Open ideas and unfinished threads live in `TBX-TODO.md` in the `tab-next` repo.
