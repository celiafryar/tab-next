---
name: tbx-dataobject
description: >-
  Load CSV files into Salesforce Data 360 / Data Cloud as data streams and Data Lake Objects
  entirely over REST — including the load-time Primary Key that Many-to-One relationships depend
  on. Verbs: prep (audit files before loading), load (create + ingest), edit (what is actually
  mutable), delete (teardown). Use when adding source data for Tableau Next, when a DLO has the
  wrong field types or key, or when auditing CSVs before ingest. Companion to tbx-semantic-model.
---

# tbx-dataobject — get files into Data 360 as Data Lake Objects

The whole lifecycle is the documented **Data 360 Connect REST API**. No wizard, no Aura, no
VS Code extension. Verified end to end 2026-08-06 on a Boston Bluebikes dataset.

```bash
POST   /services/data/v66.0/ssot/data-streams?                      # create stream + DLO + PK
GET    /services/data/v66.0/ssot/data-streams?                      # list (paged, totalSize)
GET    /services/data/v66.0/ssot/data-streams/<name>?               # one stream, full config
PATCH  /services/data/v66.0/ssot/data-streams/<name>?               # update (heavily restricted)
POST   /services/data/v66.0/ssot/data-streams/<name>/actions/run?   # trigger ingest
DELETE /services/data/v66.0/ssot/data-streams/<name>?shouldDeleteDataLakeObject=true
GET    /services/data/v66.0/ssot/data-lake-objects?
GET    /services/data/v66.0/ssot/data-spaces?
```
`<name>` accepts the **developer name OR the 18-char record ID**.

**Two CLI mechanics that will waste your time otherwise:**
- **Trailing `?` on every path.** Without it this CLI generation returns `NOT_FOUND` on valid paths.
- **`--body "@file"` — the `@` is required**, and is required even on DELETE. Omit it and you get
  `No 'mode' found in 'body' entry` or a misleading `JSON_PARSER_ERROR`.
- Redirect stdout to a file before parsing; the CLI's update notice corrupts JSON.

---

## `prep` — audit the file BEFORE loading

**Ingest-time decisions are permanent.** Category, primary key, and field types cannot be changed
after the stream is created. Run this checklist and **ask the user about anything that looks off**
rather than picking silently.

1. **Primary key: is it unique, and is it the join key?**
   The wizard *requires* a PK but never checks uniqueness, and a duplicate key silently merges rows.
   ```python
   vals = [r[col] for r in rows]
   dupes  = {k:v for k,v in Counter(vals).items() if v > 1}
   blanks = sum(1 for v in vals if v.strip() in ('', 'NULL', 'null', 'NA'))
   ```
   Watch for the **literal string `NULL`** as a sentinel — real case: 3 station rows carried
   `id = "NULL"`, collapsed into one record, and 2 real stations vanished with a `SUCCESS` status.
   Then confirm the key is what other files actually reference. A column can be perfectly unique and
   still be the wrong key: `number` was unique, but the trip files joined on `id`.

2. **No natural key? Generate a surrogate**, and prefix it per source file so it stays unique across
   sibling loads (`T17…`, `T18…`). Fact tables don't *need* a key architecturally — they're the
   "many" side — but the UI demands one, and a scripted load should set one anyway.

3. **Field types must match across sibling files.** Two years of the same export inferred
   differently (`start_station_id` Text vs Number, `user_birth_year` Text vs Number). That breaks
   both the join and any later DMO union, and is unfixable after load.

4. **Join key type must match the table being joined to** (Text vs Text, not Text vs Number).

5. **Category.** The UI defaults to `PROFILE`. Reference/lookup data (stations, products, calendars)
   wants **`OTHER`**. `PROFILE` is for identity-resolved entities, `ENGAGEMENT` for timestamped
   events. Immutable after save, and it has billing implications.

6. **Header typos and encoding.** A misspelled header becomes a permanent DLO column name. Check for
   mangled characters too (a `?` mid-name usually means an encoding mismatch).

7. **Size.** The uploader accepts **2 GB and 1,050 columns**; files over 100 MB just take longer.
   (A widely-cited 150 MB figure is wrong.) Stripping unnecessary quotes and normalizing
   float-formatted integers (`1992.0` -> `1992`) can shrink a file more than a surrogate key adds.

8. **After load, reconcile the counts.** `lastProcessedRecords` vs `totalRecords` disagreeing is the
   *only* signal that the primary key deduplicated rows. The run still reports `SUCCESS`.

---

## `load` — create the stream, DLO, and primary key

**Prerequisite, and the one real gap:** `advancedAttributes` points at a CSV **already staged** in
Data Cloud's S3 upload area. Staging a *new* file still requires the UI, because the presigned
credential call (`SfDriveController/ACTION$generateSFDrivePresignedCredentials`) is Aura-only.
Once a file is staged, everything below is scriptable and repeatable — including rebuilding the
same stream with different types, with no re-upload.

Grab `advancedAttributes` from any stream that used the file, or from a UI-created stream.

```jsonc
POST /services/data/v66.0/ssot/data-streams?
{
  "name": "Bluebike_Trips_2018", "label": "Bluebike Trips 2018",
  "datastreamType": "CONNECTORSFRAMEWORK",
  "connectorInfo": { "connectorType": "DataConnector",
                     "connectorDetails": { "name": "UploadedFiles" } },

  // the FILE's headers and types, typos included
  "sourceFields": [ { "name": "trip_id", "dataType": "Text" },
                    { "name": "start_time", "dataType": "DateTime" } ],

  "dataLakeObjectInfo": {
    "name": "Bluebike_Trips_2018__dll",
    "label": "Bluebike Trips 2018",
    "category": "OTHER",
    "dataspaceInfo": [ { "name": "default" } ],
    "fields": [
      { "name": "trip_id",    "label": "trip_id",    "dataType": "TEXT",     "isPrimaryKey": true },
      { "name": "start_time", "label": "start_time", "dataType": "DATETIME", "isPrimaryKey": false }
    ]
  },

  // source header -> DLO column. Renames a misspelled header WITHOUT re-uploading the file.
  "mappings": [ { "sourceFieldLabel": "longtitude", "targetFieldName": "longitude" } ],

  "refreshConfig": { "refreshMode": "TOTAL_REPLACE",
                     "frequency": { "frequencyType": "None" } },
  "advancedAttributes": {
    "parentDirectory": "s3://…/flup-fileUploads/dc_file_upload",
    "importDirectory": "<userId>/<ISO timestamp>",
    "fileName": "x.csv", "delimiter": ",", "fileType": "CSV" }
}
```

Then `POST …/<name>/actions/run?` with `--body "@empty.json"` -> `{"errors":[],"success":true}`.
Ingest is async: `lastRunStatus` goes `PENDING` then `SUCCESS`.

### THE POINT: `isPrimaryKey` is writable here and nowhere else
`dataLakeObjectInfo.fields[].isPrimaryKey: true` sets the **load-time Primary Key Field** — the
thing Many-to-One cardinality depends on. It round-trips truthfully on GET, and the UI shows
*Field Used As: Primary Key*. Skip it and Data Cloud mints a `uuid_temp` you can never reassign.

This flag is **inert in the semantic model layer** (`dataObjects.json`), which is why it was long
believed unreachable to code. Two different layers, same field name, opposite behavior.

### Two casing conventions in one payload (easy to get wrong)
| Where | Convention | Values seen |
|---|---|---|
| `sourceFields[].dataType` | TitleCase | `Text`, `Number`, `DateTime` |
| `dataLakeObjectInfo.fields[].dataType` | SCREAMING | `TEXT`, `NUMBER`, `DATETIME` |

`DATE_TIME` and `TIMESTAMP` are **rejected** — the enum is `DataCloudFieldTypeEnum` and the value is
`DATETIME`. Primary keys must be **TEXT**; a numeric-looking column can still infer as TEXT, which
is what makes it eligible.

---

## `edit` — assume nothing is mutable

`PATCH` exists but is heavily restricted. For Uploaded Files streams:
```
Unable to update the data-stream -
DataLakeObject Info cannot be patched for data streams created using Uploaded Files connection
```
**So fixing types or the key means delete + recreate.** That is cheap: deleting a stream does NOT
remove the staged S3 file, so you can rebuild against the same `importDirectory` with corrected
types and never re-upload. This is the standard repair loop.

**Dataspace filters are create-time only and currently unusable on `default`.** Shape is known:
```jsonc
"dataspaceInfo": [{ "name": "default", "filter": {
  "conjunctiveOperator": "OR",
  "conditions": { "conditions": [
    { "tableName": "<DLO>__dll", "fieldName": "id__c",
      "operator": "IS_NOT_NULL", "filterValue": "" }]}}}]
```
Creating one against `default` fails identically via UI **and** REST with
`Unable to create data space member`. Hypothesis: filters are for **non-default** dataspaces.
Untested — see `TBX-TODO.md`.

---

## `delete` — three gotchas

```bash
DELETE /services/data/v66.0/ssot/data-streams/<name>?shouldDeleteDataLakeObject=true
```
- **`shouldDeleteDataLakeObject` is REQUIRED.** `false` keeps the DLO and its data while dropping
  the pipeline; `true` drops both.
- The CLI still needs `--body "@empty.json"`.
- **Async.** Empty body, then `DELETING`, then `ITEM_NOT_FOUND`. Poll before recreating the same
  name, or the create fails on a collision.

Bulk teardown from the UI path uses two Aura calls on `DataStreamDeploymentController`, both taking
`{"ids":[...]}` arrays: `getDataStreamsThatCanBeDeleted` (an **eligibility precheck** — Data Cloud
refuses to drop streams with downstream dependents; run it first) then `deleteMassDataStream`.

---

## The schema is a self-describing oracle — use it instead of guessing
- Unknown property -> `Unrecognized field "x"`
- Missing required param -> named outright (`Required request parameter missing:
  shouldDeleteDataLakeObject`)
- Bad enum value -> `Invalid value for DataCloudFieldTypeEnum: DATE_TIME`

So probe with a throwaway `PATCH {"candidate": null}` and read the reply. It does **not** dump a
known-properties list, so it is a yes/no oracle per name. This is how `shouldDeleteDataLakeObject`
and the `DATETIME` enum were found.

## Multiple files into one table
A File Upload stream **always creates its own new DLO** — the wizard's Data Lake Object picker is
disabled even though the lookup returns valid targets. To present sibling files (e.g. one per year)
as a single table, map the DLOs onto one **DMO** in the Data Model layer. The semantic layer
consumes DMOs fine (`dataObjectType: "Dmo"`, `*__dlm`) and can mix Dmo and Dlo in one model.
DMO mapping is not yet captured — see `TBX-TODO.md`.

Related: `tbx-semantic-model` (build the model over these objects), `tableau-semantics-dx`
(authoring rules for calcs, metrics, descriptions).
