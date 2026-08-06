---
name: tbx-datatransform
description: >-
  Combine, reshape, filter, and aggregate Data 360 Data Lake Objects using Batch Data Transforms —
  including UNION, which Data Cloud calls APPEND. Covers the STL definition format, the REST
  lifecycle (create/run/cancel/retry/status), and the field-alignment rules that decide whether a
  union produces real rows or silent nulls. Use when several source files must present as one table,
  or when a DLO needs cleaning or reshaping after ingest.
---

# tbx-datatransform — union and reshape Data Lake Objects

**A union in Data Cloud is called APPEND.** That is the single most useful thing in this file; it is
not called union anywhere in the UI or the definition format.

Verified 2026-08-06 by building one end to end over two Bluebikes trip tables.

## When you need this
A **File Upload data stream always creates its own new DLO** — the wizard's Data Lake Object picker
is disabled, so sibling files (one per year, one per region) cannot land in a shared table at ingest.
A Batch Data Transform with an Append node is how you combine them afterward.

The alternative is mapping several DLOs onto one **DMO** in the Data Model layer, which avoids
duplicating storage. Use a transform when you also need to clean, filter, or reshape; use DMO
mapping when a plain union is all you want. (DMO mapping is not yet documented here — see
`TBX-TODO.md`.)

## THE PREREQUISITE, and it is not optional
Append maps **by column name**, and the dialog states the consequence plainly:

> *"Appended rows show null values for batch data transform columns that aren't mapped."*

So a name or type mismatch does not error. It silently fills that column with nulls for every row
from the mismatched source. **Align the sources before you build the transform.** If two DLOs
disagree, rebuild the offending stream (`tbx-dataobject edit` — delete and recreate against the same
staged file, no re-upload needed). When both sides match, all columns auto-map with green checks and
you touch nothing.

## The three UI choices, and the two that are permanent
1. **Batch** (visual editor, on demand or scheduled) vs **Streaming** (SQL, near real time) vs
   from a Data Kit. For static files, Batch.
2. **Data Lake Objects** vs **Data Model Objects** as the source. The dialog explains it: DLO sources
   apply the transform **across all data spaces**; DMO sources **restrict it to one**.
3. The **Output node creates a brand new DLO**, so it asks the same permanent questions as ingest:
   Object Name, API Name, **Category** (defaults to `Profile` — reference data wants **`Other`**),
   and **Primary Key**. Same checklist as `tbx-dataobject prep`.

**Name every node.** Nodes default to `Append 0` / `Output 0`, and those defaults land in the saved
definition and in the graph, where they are useless to the next reader. Rename via the pencil beside
the node title, and use the description field.

## REST lifecycle

```bash
GET  /services/data/v66.0/ssot/data-transforms?                                  # list
GET  /services/data/v66.0/ssot/data-transforms/<name>?                           # one, with definition
POST /services/data/v66.0/ssot/data-transforms?                                  # create
POST /services/data/v66.0/ssot/data-transforms/<name>/actions/run?               # -> {"success": true}
POST /services/data/v66.0/ssot/data-transforms/<name>/actions/cancel?
POST /services/data/v66.0/ssot/data-transforms/<name>/actions/retry?
GET  /services/data/v66.0/ssot/data-transforms/<name>/actions/refresh-status?
```
Every record carries an `actionUrls` block listing exactly these, so read it rather than guessing.
Same conventions as the rest of the family: trailing `?`, `--body "@file"` with the `@`.

## The definition format is STL, and it is fully declarative

Top level: `{ name, label, type: "BATCH", definitions: [ … ] }`.
Each definition:

```jsonc
{ "name": "Bluebike_Trips_Union", "label": "Bluebike_Trips_Union",
  "type": "STL",              // <-- the polymorphic discriminator on `definition`
  "version": "56.0",
  "nodes": {
    "LOAD_DATASET0": { "action": "load",
                       "parameters": { "dataset": { "name": "Bluebike_Trips__dll",
                                                    "type": "dataLakeObject" },
                                       "fields": ["trip_id__c", …] } },
    "LOAD_DATASET2": { "action": "load",
                       "parameters": { "dataset": { "name": "Bluebike_Trips_2018__dll",
                                                    "type": "dataLakeObject" }, "fields": [ … ] } },
    "APPEND0":       { "action": "appendV2",   "parameters": { … } },   // <-- the union
    "OUTPUT0":       { "action": "outputD360", "parameters": { … } }
  },
  "outputDataObjects": [ { "category": "Other", "fields": [ … ] } ],
  "ui": { "nodes": { "LOAD_DATASET0": { "label": "Bluebike Trips", "type": "LOAD_DATASET",
                                        "top": 112, "left": 112, … } } } }
```

**Node actions seen:** `load`, `appendV2`, `outputD360`. The editor also offers Transform, Filter,
Aggregate, AI Functions, Join, and Update, so expect corresponding action names.

**`nodes` is logic, `ui` is layout.** They are keyed by the same node ids, so canvas position is
cosmetic and separable — good for generating a definition in code.

**Node fields carry the `__c` suffix** (`trip_id__c`), unlike the DLO create payload which uses bare
names. Easy to get wrong.

The editor also has **import and export buttons** in its toolbar, which is the natural round-trip for
version-controlling a transform. Not yet exercised.

**`convertStlToDcSql` exists as an Aura action**, meaning the visual pipeline compiles down to Data
Cloud SQL. Worth pulling on if you ever need to see or hand-write the generated SQL.

## Gotchas
- **Adding an Append creates its own second source node**, orphaning the one already on the canvas.
  Delete the orphan or the graph carries a dangling input.
- The **Save dialog wants both a Name and a Definition Name**, and neither auto-fills from the other.
- Creating over REST blind is painful: `definition` is polymorphic and the error only says
  *"missing property 'type' that is to contain type id"* without listing valid ids. Build one in the
  UI, `GET` it, and use that as your template. That is how `STL` was found.

Related: `tbx-dataobject` (get the files in, and fix mismatched types), `tbx-semantic-model`
(consume the unioned DLO), `tbx`.
