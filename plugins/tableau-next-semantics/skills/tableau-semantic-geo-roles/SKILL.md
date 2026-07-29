---
name: tableau-semantic-geo-roles
description: >-
  Assign geographic roles (City, State, Country, and latitude/longitude) to fields in a Tableau
  Next semantic model in pro-code, by setting dataType + semanticDataType in dataObjects.json.
  Use when a model has place-name or coordinate columns that need to map, when maps or Tableau
  Agent geography questions aren't working, when auditing which fields should be geo-roled, or
  when deciding which look-geographic-but-aren't fields to leave alone. Companion to
  tableau-semantics-dx (retrieve/validate/deploy loop).
---

# Assigning Geographic Roles in a Tableau Next Semantic Model

Geographic roles are what let Tableau Next place a field on a map and let Tableau Agent answer
"which state has the most pipeline". They are set per field in `dataObjects.json` and are fully
pro-code editable. Use `tableau-semantics-dx` for the retrieve / validate / deploy mechanics.

## The mechanism — TWO properties, not one
The role is not a single key. Both of these change together:

```json
{
  "apiName": "City13",
  "label": "City",
  "dataType": "Geo",            // <-- was "Text". THIS is the half people miss.
  "semanticDataType": "City",   // <-- the role itself
  "storageDataType": "Text",    // <-- UNCHANGED. Leave it alone.
  "displayCategory": "Discrete"
}
```
Setting only `semanticDataType` is the classic mistake — `dataType` must become `"Geo"` too.
`storageDataType` reflects the underlying column and must not be touched.

Default state on a freshly retrieved model is `dataType: "Text"`, `semanticDataType: "None"`.

## Confirmed role values
| Role | `semanticDataType` | Confirmed on |
|---|---|---|
| City | `City` | construction-sdx "Construction Insights"; sales-opportunity-sdx |
| State / Province | `State` | construction-sdx "Construction Insights" |
| Country | `Country` | sales-opportunity-sdx (GUI-seeded 2026-07-29) |

**UNVERIFIED — do not guess these, discover them (see below):** latitude, longitude, county,
postal/ZIP code, CBSA/MSA, area code, congressional district. The Tableau Desktop role list is a
reasonable guide to what probably exists, but the exact enum strings are not confirmed here, and a
wrong enum fails the whole atomic deploy.

## Discovering an unknown enum value — two cheap routes
1. **Grep the org's other retrieved models first.** This costs nothing and is how `City`/`State`
   were found without a single deploy:
   ```python
   import json, glob, collections, os
   for fp in glob.glob(r'C:\Users\<u>\source\repos\**\dataObjects.json', recursive=True):
       items = json.load(open(fp, encoding='utf-8'))['items']
       for o in items:
           for k in ('semanticDimensions','semanticMeasurements'):
               for f in o.get(k) or []:
                   if f.get('semanticDataType') not in (None,'None'):
                       print(os.path.dirname(fp), o['label'], f['label'], f['semanticDataType'])
   ```
2. **GUI-seed one field.** Ask the user to set the role on ONE field in the model UI, then retrieve
   and read the exact strings. Ask them to also report *what options the picker offered* — that
   enumerates the whole set in one shot. Tell them not to bother naming/labelling carefully; you
   only want the enum.

## Latitude and longitude
Coordinates are **numeric**, so the pattern almost certainly differs from place-name fields and is
NOT yet confirmed. Expect to have to check:
- They arrive as **measures** (`semanticMeasurements`, `dataType: "Number"`,
  `displayCategory: "Continuous"`, an `aggregationType`), not dimensions.
- So does `dataType` become `"Geo"` while `storageDataType` stays `"Number"`? Does the field have to
  move to `semanticDimensions`? Does `aggregationType` need to become `Average`/`None` instead of
  `Sum`? **Summing latitudes is meaningless**, so whatever the shape, verify the aggregation.
- **Assign them as a pair.** A lat with no long (or vice versa) is useless, and mismatched roles on
  the two halves is a common defect worth checking for explicitly.
- GUI-seed one coordinate field before writing any others.

If a dataset has **no** coordinate columns, say so plainly rather than inventing them. Tableau Next
geocodes from City/State/Country on its own, so coordinates are an optimisation, not a requirement.
Adding them means new source columns and a re-ingest — see the cost warning below.

## Process
1. Retrieve the model. Inventory candidates by scanning `apiName`/`label` for
   `lat|lon|lng|city|state|province|country|county|zip|postal|geo|region|territory`.
2. **Triage the candidates** (see "what NOT to tag"). Report the ones you are deliberately skipping
   and why — a silent skip reads as an oversight.
3. Resolve real (suffixed) apiNames per object by LABEL.
4. Set `dataType: "Geo"` + `semanticDataType: "<Role>"`, leaving `storageDataType` alone.
5. Validate → deploy → retrieve → confirm the roles round-tripped.
6. **Then look at the map / ask a geography question.** Deploying the role is not the same as the
   value resolving; only real data proves that.

### Fields with the same apiName in different objects are SEPARATE instances
Data 360 reuses apiName strings across objects (`Country2` on both Account and CompanyLocation,
`City13`, `StateProvince1`). Setting the role on one does NOT set it on the other. CONFIRMED
2026-07-29: after a role was set on `CompanyLocation.Country2`, `Account.Country2` was still
`Text`/`None`. **Iterate per object, never per apiName.**

### Assign City + State + Country together on the same table
The geocoder disambiguates a city using the state and country alongside it. A lone City role on a
table with 38 international cities will mis-resolve; the same field with State and Country roled
beside it resolves correctly.

## What NOT to tag (triage rules)
- **Custom groupings whose values mix real places with invented names.** A `TerritoryName` holding
  `Great Lakes, Northeast, South Central, West, Canada, Mexico` must stay untagged: the geocoder
  would resolve two of seven and fail the rest, which is worse than no role at all. Same for
  `RegionName`. These are business hierarchies, not geography.
- **Multi-value fields.** A `CoverageSummary` of `"MI, OH, IN, IL, WI"` is a list, not a place. No
  role can resolve it.
- **IDs.** `RegionId`, `TerritoryId`, `LocationId` are keys, not places.
- **Denormalised name copies** used purely for grouping, if the real geography lives elsewhere.

Ask the user before tagging anything ambiguous. Getting this wrong produces a map with silent gaps.

## Data hygiene — check before "cleaning"
- **Accented place names are CORRECT, not corrupt.** `Nuevo León` (U+00F3) and `Querétaro`
  (U+00E9) are the official spellings and are what the geocoder expects. Verify encoding by
  inspecting code points, not by eyeballing terminal output — a console that cannot render UTF-8
  shows `Nuevo Le?n` and makes clean data look broken. (This exact false alarm happened on
  sales-opportunity-sdx.) Do not strip accents "to be safe"; that is as likely to break the match.
- **Non-US states/provinces** (Mexican states, Canadian provinces) are the realistic failure point.
  Deploy, then check which ones resolve.
- **If a value genuinely won't geocode, fix it in the semantic layer, not the source.** A
  calculated dimension can normalise the value with no re-ingest. (Whether a *calculated* dimension
  can itself carry a geo role is UNVERIFIED — test before promising it.)
- **NEVER casually propose adding a cleaned column to the source.** A new source column means
  re-uploading the file, which creates a new DLO with new API names, which forces a full rebuild of
  the model layer: every description, hide, relationship, calculated field and geo role. Quantify
  that cost to the user before suggesting it, and only after confirming the geocoding actually
  fails.

## KNOWN PRODUCT DEFECT — map viz save error after assigning roles (not your fault)
Right after geo roles are working, the first map someone builds may fail to save with:

> `Error: -1665391842 F7, F8, F4, F5 field key in encodings is not valid. encodings can have only
> measure fields.`

**This is a Tableau Next viz-builder bug, NOT a problem with the roles or the semantic model.**
Observed 2026-07-29 on sales-opportunity-sdx while the map itself rendered and geocoded perfectly.

Signature that proves it is state corruption rather than a validation rule:
- A map with only the geo field saves fine. Adding one measure to Color/Size may be fine. Adding a
  second reliably errors.
- **The error then persists even after reverting to a state that previously saved.** A real
  validation rule would clear when the condition is removed. One that sticks means the saved spec is
  accumulating `F<n>` field slots that the UI no longer displays, so removing a pill leaves its entry
  behind. That is why the message names 4 field keys on a sheet showing 1 field.

**Do NOT** start rolling back `dataType: "Geo"` to chase this — the roles are fine. Instead:
1. **Save after every single change.** Geo field on Locations → save. Add Color measure → save. Add
   Size measure → save. Each save commits a clean spec and gives a floor to fall back to.
2. **The moment the error appears, abandon the sheet.** It is unrecoverable; reverting does not clear
   it. Build a new viz.
3. Experiment in a throwaway sheet; build the keeper in one clean pass.
4. If Color+Size breaks but Color alone is stable, prefer single-encoding — usually clearer anyway.

Worth a Salesforce support case. The persuasive detail is the persistence after revert; lead with it.

## Verify
After deploy + retrieve:
```python
geo = [(o['label'], f['label'], f['semanticDataType'])
       for o in json.load(open('dataObjects.json', encoding='utf-8'))['items']
       for k in ('semanticDimensions','semanticMeasurements')
       for f in (o.get(k) or []) if f.get('dataType') == 'Geo']
```
Check: expected count, correct role per field, `storageDataType` still original, and that no
descriptions or `isVisible` flags were disturbed.

## Reference
`sales-opportunity-sdx` (GitHub `celiafryar/sales-opportunity-sdx`) — 8 roles across 4 objects:
City on `Account.City`, `CompanyLocation.City`, `Product.PrimaryPlantCity`; State on
`Account.StateProvince`, `CompanyLocation.StateProvince`; Country on `Account.Country`,
`CompanyLocation.Country`, `BusinessRegion.CountryScope`. Region and Territory deliberately
untagged. See the `sales-opportunity-model` memory.
