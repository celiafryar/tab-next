---
name: tbx-semantic-model
description: >-
  Create, read, modify, and delete Tableau Next semantic models entirely over REST, using GRANULAR
  per-item endpoints instead of the dangerous full-model PUT. Verbs: create (a new model from
  nothing), describe (read the live model), add/edit/remove (single objects, calcs, metrics,
  relationships), deploy, delete. Use whenever building or changing a semantic model against a
  Data 360 org. Owns the mechanics; tableau-semantics-dx owns the authoring rules (formula syntax,
  metric shape, description style).
---

# tbx-semantic-model — model lifecycle over REST, one item at a time

**No VS Code extension is needed at any step.** Create, read, write, validate, and delete all work
from `sf api request rest`. Verified 2026-08-06.

**Trailing `?` on every path.** `--body "@file"` — the `@` is mandatory. Redirect stdout to a file
before parsing, or the CLI's update notice corrupts the JSON.

---

## THE HEADLINE: granular endpoints exist. Stop using the full-model PUT.

A full-model `PUT` is **full state**: any item missing from the payload is **deleted on the org**.
Deploying from a stale read silently destroys whatever anyone else changed since your GET. That
hazard is now avoidable — every collection has its own sub-resource that accepts single-item writes:

```bash
POST   /ssot/semantic/models/<model>/data-objects?              # add ONE object
GET    /ssot/semantic/models/<model>/data-objects/<apiName>?    # read ONE
POST   /ssot/semantic/models/<model>/relationships?
POST   /ssot/semantic/models/<model>/calculated-dimensions?
POST   /ssot/semantic/models/<model>/calculated-measurements?
GET    /ssot/semantic/models/<model>/metrics?  |  /metrics/<apiName>?
       …also /groupings, /parameters
```
Each model in `GET /ssot/semantic/models` advertises these as `semantic*Url` properties.

**Use these for every incremental change.** Reserve the full PUT for bulk rewrites where you have
just re-GET'd and diffed. When you must PUT: re-GET immediately before, and diff.

---

## `create` — a model needs exactly three fields

```bash
POST /services/data/v66.0/ssot/semantic/models?
```
```json
{ "dataspace": "default", "apiName": "Bluebikes_Model", "label": "Bluebikes Model" }
```
Omit `dataspace` -> *"missing a mandatory dataspace value"*. Omit `label` -> *"Label of
SemanticModel is required"*. Everything else defaults (`agentEnabled: true`, empty collections).

## `add` a data object — and let the platform fill in the fields

```bash
POST /ssot/semantic/models/<model>/data-objects?
```
```json
{ "apiName": "Bluebike_Stations",
  "label": "Bluebike Stations",
  "dataObjectName": "Bluebike_Stations__dll",
  "dataObjectType": "Dlo",
  "shouldIncludeAllFields": true,
  "tableType": "Standard" }
```
**`shouldIncludeAllFields: true` means you never enumerate fields.** Three POSTs like this produced
34 dimensions and 7 measurements without listing one. Fields land under `semanticDimensions` /
`semanticMeasurements` on each object — **not** a single `fields` array.

`dataObjectType` is `Dlo` (`*__dll`) or **`Dmo`** (`*__dlm`). A model can mix both, which is how you
consume a DMO that unions several sibling DLOs.

Object-level properties worth knowing: `label` (safe to rename — `apiName` is the immutable
identity), `description`, `primaryNameField` (the readable display name), `filters`,
`shouldIncludeAllFields`, `tableType`.

## `describe` — read the live model without asking anyone to retrieve

```bash
GET /ssot/semantic/models/<model>?            > model.json
GET /ssot/semantic/models/<model>/validate?   # {"isValid": true, ...}
GET /ssot/semantic/models?                    # all models + their sub-resource URLs
```
Top-level keys: `semanticDataObjects`, `semanticCalculatedDimensions`,
`semanticCalculatedMeasurements`, `semanticMetrics`, `semanticRelationships`, `businessPreferences`,
`cacheKey`.

**The GET HTML-escapes strings.** `>` returns `&gt;`, `"` `&quot;`, `'` `&#39;`, across
`expression`, `description`, and `businessPreferences`. PUT it back verbatim and you get
`Syntax Error - token recognition error at: '&'`. Unescape recursively first:
```python
import html
def unesc(o):
    if isinstance(o, dict):  return {k: unesc(v) for k, v in o.items()}
    if isinstance(o, list):  return [unesc(v) for v in o]
    return html.unescape(o) if isinstance(o, str) else o
```
This trap does **not** apply to granular POSTs of new items — one more reason to prefer them.

## `deploy` / `delete`

Deploys are **atomic**: one bad property rejects the entire payload and nothing changes, which is
why a rejected full PUT looks exactly like "nothing happened". `lastModifiedDate` is the only proof
a write landed. Diff before and after.

Deletion by omission from a full PUT works but is exactly the dangerous behavior above; prefer an
explicit `DELETE` on the item path.

**The validator lies, twice.** Real errors nest under `subResources` *below* a "0 validation errors"
line, and `isValid: true` coexists with metrics that render a dash. Read the JSON, and trust the
UI's yellow triangle. **Validation passing proves nothing** — verify numbers against the source or
the Data Cloud SQL API (`POST /ssot/queryv2?`, DLO names + `__c` columns).

## Probing: the schema is a self-describing oracle
Unknown property -> `Unrecognized field "x"`. Missing required param -> named outright. Bad enum ->
`Invalid value for <Enum>: <value>`. Probe with a throwaway `PATCH {"candidate": null}` rather than
guessing. No known-properties dump, so it is yes/no per name.

## Sequence for a model from scratch
1. `tbx-dataobject prep` + `load` the source files (keys and types are permanent — get them right).
2. `POST /ssot/semantic/models` — three fields.
3. `POST …/data-objects` per table with `shouldIncludeAllFields: true`.
4. `POST …/relationships` per join. Graph must be **acyclic**; `ManyToOne` needs a load-time primary
   key on the parent. See `tableau-semantic-relationships`.
5. Descriptions, calcs, metrics — see `tableau-semantics-dx` for syntax and the 255-char cap.
6. `GET …/validate?`, then verify actual numbers.
7. Attach to a workspace — see `tbx-workspace`.

Related: `tbx-dataobject`, `tbx-workspace`, `tableau-semantics-dx` (authoring rules),
`tableau-semantic-relationships`, `tableau-business-preferences`, `tableau-semantic-geo-roles`,
`semantic-descriptions-from-spreadsheet`.
