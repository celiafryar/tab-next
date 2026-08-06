# TBX TODO — open threads and future ideas

Running list of things worth exploring for the `tbx-*` skill family. Started 2026-08-06 during
the Bluebikes ingest-and-create session.

## Skill family (planned)

| Skill | Verbs | Status |
|---|---|---|
| `tbx-dataobject` | `prep` / `load` / `edit` / `delete` | ingest mechanics proven, skill not written |
| `tbx-semantic-model` | `create` / `retrieve` / `deploy` / `describe` | create + granular add proven |
| `tbx-workspace` | `create` / `attach` / `digest` | create + attach captured |
| `tbx-viz` | `create` / `read` / `recreate` | objects identified, not exercised |
| `tbx-dashboard` | TBD | **create path unsolved** |
| `tbx` | orchestrator, routes to the above | not started |

Design principles agreed:
- **Small, single-concern skills** over one large one, so a side-track doesn't partially unload it.
- **Verb-style invocation** (`/tbx-dataobject load`).
- **Accept an optional schema** for finer control; otherwise **ask questions when something looks
  off** rather than silently choosing. See the pre-load checklist below.

## Pre-load checklist for `tbx-dataobject prep`

Every one of these was catchable before load and permanent afterward. Ask, don't assume:
- **Primary key uniqueness.** The wizard *requires* a PK but does not check uniqueness. Bluebikes
  stations had 3 rows with the literal string `NULL` in `id`; they silently collapsed to one
  record (339 processed, 337 stored). Check distinct count + blanks/NULL sentinels per candidate.
- **Is the PK the actual join key?** `number` was unique and useless — the trip files join on `id`.
  Verify against the files that reference it, not just uniqueness.
- **Category.** UI defaults to `PROFILE`. Reference/lookup data wants `OTHER`. Immutable after save,
  affects billing.
- **Field types across sibling files.** 2018 inferred `start_station_id`/`end_station_id`/
  `user_birth_year` differently from 2017. Immutable after load; breaks DMO union and join keys.
- **Join key type match** with the table being joined to (Text vs Number).
- **Header typos / encoding.** `longtitude` was baked into a DLO. Also a mangled dash in a station
  name suggests an encoding mismatch worth checking.
- **Surrogate key needed?** Fact tables often have no natural key. Generate one, prefixed per file
  so it stays unique across sibling loads (`T17…` / `T18…`).
- **Row count reconciliation after load.** `lastProcessedRecords` vs `totalRecords` disagreeing is
  the only signal that the PK deduplicated rows.

## Unsolved / needs investigation

- **Dashboard creation.** `AnalyticsDashboard` and every `*WidgetDef` are `createable: false` on the
  sObject API. UI uses `AnalyticsController` Aura actions. Check whether the **Metadata API** has a
  dashboard type, which would give a supported path.
- **Dataspace filters.** Shape is known (see the ingest notes) but creating one against the
  `default` dataspace fails with `Unable to create data space member`, via both UI and REST, and
  `dataLakeObjectInfo` cannot be PATCHed for Uploaded Files streams. Hypothesis: filters are meant
  for **non-default** dataspaces. Test by creating a second dataspace.
- **File staging automation.** `POST /ssot/data-streams` works, but `advancedAttributes` points at a
  CSV already staged in S3. Staging currently requires the UI, because
  `SfDriveController/ACTION$generateSFDrivePresignedCredentials` is Aura-only. Either construct the
  S3 path from the captured pattern, or switch to the **Bulk Ingestion API** (documented, up to 100
  files per job) which would make ingest fully scriptable.
- **DMO mapping.** Two DLOs onto one DMO is the intended union for sibling year files. Not yet
  captured. Needed so 2017 + 2018 present as one Trips table. Confirmed the semantic layer accepts
  DMOs (`dataObjectType: "Dmo"`, `*__dlm`) and can mix Dmo + Dlo in one model.
- **Can a data stream ever attach to an existing DLO?** The File Upload wizard's DLO picker is
  disabled even though the lookup returns 116 DLOs including valid targets. Possibly enabled for
  other connector types.

## Data cleanup owed on the Bluebikes set

- 3 stations with `id = "NULL"` (decommissioned test sites per Bluebike) collapse into one junk
  record. Filter or remove at source.
- `user_gender` is numeric 0/1/2 and needs decoding; confirm what `0` means (~5% of rows).
- ~0.28% of trip endpoints reference station ids absent from the stations file (station 88 is the
  big one). Decide whether to add a catch-all row.
- `user_birth_year` is Text, so rider-age math needs a cast.
- 2019 not loaded (208 MB, fine under the real 2 GB limit).

## Corrections worth remembering

- **File upload limit is 2 GB**, not 150 MB. A search result said 150 MB and was wrong; the UI
  states 2 GB and 1,050 columns, and warns that files over 100 MB take longer.
- **`isPrimaryKey` is writable at ingest** via `dataLakeObjectInfo.fields[]`, and reads back
  truthfully from `/ssot/data-streams`. It is only inert in the *semantic model* layer.
- **The semantic model sub-resources accept POST**, so single items can be created without a
  full-model PUT. This removes the "deploy from a stale read destroys someone else's work" hazard
  that motivated the whole investigation.
