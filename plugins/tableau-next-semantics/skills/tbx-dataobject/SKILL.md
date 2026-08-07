---
name: tbx-dataobject
description: >-
  Load CSV files into Salesforce Data 360 / Data Cloud as data streams and Data Lake Objects
  over REST — including the load-time Primary Key that Many-to-One relationships depend
  on. Verbs: prep (audit files before loading), load (stage + create + ingest a new file), verify
  (prove rows landed, not just HTTP 200), edit/rebuild (delete + recreate against the staged
  file), delete (teardown). Use when adding source data for Tableau Next, when a DLO has the
  wrong field types or key, or when auditing CSVs before ingest. Companion to tbx-semantic-model.
---

# tbx-dataobject — get files into Data 360 as Data Lake Objects

Everything after staging is the documented **Data 360 Connect REST API** — no VS Code extension
at any step. Staging the file itself still needs a Lightning session (see `load`). Verified end
to end 2026-08-06 on a Boston Bluebikes dataset.

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

**The list endpoint pages at 10 by default** and returns `totalSize` + `nextPageUrl`. A digest
that trusts page one silently drops streams. Follow the pages (or pass `?limit=200`) and assert
the count you collected equals `totalSize`.

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

**Prerequisite: the file must already be staged in Data Cloud's S3 upload area.** The presigned
credential call (`SfDriveController/ACTION$generateSFDrivePresignedCredentials`) is Aura-only, so
staging needs a live Lightning session one way or another:

- **The UI wizard** (or a browser agent driving it). The file is staged the moment the wizard's
  file picker fires, before Deploy — so a wizard run that is cancelled at Deploy still staged the
  file. Reliable, fine for a handful of files.
- **In-page staging** (presign + presigned PUT executed inside the Lightning page) is PROVEN live
  (2026-08-06: 7 files, zero wizard) but deliberately NOT packaged as this skill's path: the
  working recipe required a localhost file server plus a CSP Trusted URL in org security settings,
  which no user of this skill should be asked to run.
- **The Bulk Ingestion API** is the eventual CLI-only path. It is NOT reachable via
  `sf api request rest` (it lives on `<tenant>.c360a.salesforce.com` behind a Data Cloud token
  exchange) and needs a connected app plus an Ingestion API connector in the org. Until that is
  stood up and verified, never claim CLI-only ingest.

**A load of a NEW file must use a FRESH `importDirectory` staged for that file.** Reusing an
`importDirectory` harvested from an existing or deleted stream is the `rebuild` operation under
`edit` below: a legitimate repair, never proof that ingest works.

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

## `verify` — a load is rows landed, not an HTTP code

Run this after every load, and print the result. A "loaded" claim without it is worthless: a 200
on a staging PUT proves S3 accepted an object; `success: true` on run proves the job was queued.
Neither proves the data arrived.

Pass criteria, all of them:
1. `lastRunStatus == SUCCESS`.
2. `totalRecords` equals the source file's row count. Count the file locally; do not trust memory
   or a truncated smoke payload — if the transport cannot carry the whole file, that is a
   transport failure, not a passing test.
3. `lastProcessedRecords == totalRecords`. A shortfall means the primary key deduplicated rows,
   and this is the ONLY signal; the run still reports SUCCESS.
4. When the numbers matter, spot-check a value from the file's last row via the SQL API
   (`POST /ssot/queryv2?`, DLO name, `__c` columns) to prove content landed, not just counts.

Keep a **provenance ledger**, one row per file, and print it when reporting a multi-file load:

```
{file, bytes, rows, importDirectory, method: wizard | in-page | rebuild,
 streamName, lastRunStatus, totalRecords, lastProcessedRecords}
```

The `method` column is what keeps a demo honest: it shows which loads exercised the full
fresh-file path and which rode a previously staged file.

**Fresh-file test discipline:** to prove the load path, use a file the org has never seen. Rotate
real datasets, or rename a known-good small CSV AND change its row count, so silently reusing an
old staged copy cannot pass criterion 2.

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
**So fixing types or the key means `rebuild`: delete + recreate.** That is cheap: deleting a
stream does NOT remove the staged S3 file, so you can rebuild against the same `importDirectory`
with corrected types and never re-upload. This is the standard repair loop. Label these loads
`rebuild` in the ledger: they prove the corrected stream definition, not the staging path, and
must never be presented as a fresh-ingest demo.

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
