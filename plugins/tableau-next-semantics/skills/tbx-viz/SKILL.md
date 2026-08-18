---
name: tbx-viz
description: >-
  Read, version, and port Tableau Next visualizations. The real chart spec is the .uaviz-meta.xml
  file from the Metadata API, whose visualSpecification element is base64-encoded JSON holding marks,
  encodings, axes, and formatting; the AnalyticsVisualization / AnalyticsVizField sObjects are the
  queryable view of the same viz. Verbs: read (digest an existing viz), create, recreate (port a viz
  to another workspace). Use when auditing, versioning, or rebuilding visualizations outside the UI.
---

# tbx-viz: the chart spec is a metadata file, not an sObject column

**Status: read is verified end to end. Create has not been exercised.** Corrected 2026-08-12.

## Read this first: where the spec actually lives

**It is not in `AnalyticsVizViewDef`.** That object has fifteen fields (`Id`, `DeveloperName`,
`MasterLabel`, `VisualizationId`, `IsOriginal`, `Version`, and audit stamps) and **no spec column at
all**. Earlier versions of this skill said its contents were "not yet decoded," which sent people
looking for something that was never there.

The spec comes from the **Metadata API**:

| Type | Suffix | Directory |
|---|---|---|
| `AnalyticsVisualization` | `.uaviz` | `analyticsVisualizations/` |
| `AnalyticsDashboard` | `.uadash` | `analyticsDashboards/` |
| `AnalyticsWorkspace` | `.uawork` | `analyticsWorkspaces/` |

```bash
sf project generate -n vizprobe --template empty
cd vizprobe
sf project retrieve start -m "AnalyticsVisualization:<DeveloperName>" -o <alias>
```

**Bulk retrieve caps at 100 instances per call.** `-m "AnalyticsVisualization"` on an org with more
than that returns a warning and an incomplete set, so name them individually or split the request.

## The three layers inside one `.uaviz-meta.xml`

1. **`<fields>` blocks**, one per shelf entry, plain XML: `fieldKey`, `fieldName`, `objectName`,
   `role`, `type`, `displayCategory`, `function`, `label`. This is the binding into the semantic
   model, and the same content as the `AnalyticsVizField` rows.
2. **`<viewSpecification>`**, HTML-escaped JSON. Filters (with operator, values, `includeNulls`),
   sort orders, header sizing.
3. **`<visualSpecification>`**. **Base64-encoded JSON. This is the chart spec.** Decode it:

```python
import base64, json, re, io
t = io.open(path, encoding='utf-8').read()
spec = json.loads(base64.b64decode(
    re.search(r'<visualSpecification>(.*?)</visualSpecification>', t, re.S).group(1)))
```

## What the visual specification contains

**`layout` decides the shape of the whole document.**

- **`"layout": "Vizql"`** is shelf-based. `rows` and `columns` are arrays of field keys, exactly like
  Tableau Desktop. `marks.panes.type` is the mark (`Bar`, `Circle`, `Text`), with `stack`,
  `encodings`, and a separate `marks.headers` block.
- **`"layout": "Map"`** has no `rows` or `columns` at all. Carries a `locations` block instead, and the
  encodings hang off the marks: `encodings: [{fieldKey: "F2", type: "Size"}, {fieldKey: "F3", type:
  "Color"}]`.

**`style` is the entire formatting panel**, and this is the part worth knowing about:
- `style.encodings.fields.<key>.defaults.format.numberFormatInfo`: `decimalPlaces`, `displayUnits`,
  `prefix`, `suffix`, `includeThousandSeparator`, `negativeValuesFormat`
- `style.axis.fields.<key>`: `range` (`includeZero`), `scale` format, tick behavior, zero line
- `style.fonts`: seven independent slots (`headers`, `actionableHeaders`, `fieldLabels`, `marks`,
  `markLabels`, `legendLabels`, `axisTickLabels`), each with size and color
- `style.shading`, `style.lines`, `style.headers`, `style.fit`

Note that number formatting and map encodings both live here. Prior work concluded those needed the
GUI because the semantic model has no such properties. That is true of the model and not of the viz.

**Verified 2026-08-12** against `orgfarm-2c0399dee5`: six visualizations retrieved and decoded,
covering Bar, Circle, Text, and Map layouts.

## The sObject layer, still useful for querying

The sObjects are the queryable view of the same visualization. Use them to *find* things; use the
metadata file to *read or move* things.

```
AnalyticsVisualization   create ✓  update ✓  delete ✓  query ✓
AnalyticsVizField        create ✓  update ✓  delete ✓  query ✓
AnalyticsVizViewDef      create ✓  update ✓  delete ✓  query ✓   (header record only, no spec)
AnalyticsVizWidgetDef    create ✗   (read-only — the dashboard-side wrapper)
```

## `AnalyticsVisualization` — the container
| Field | Notes |
|---|---|
| `DeveloperName` | **required**, the api name |
| `MasterLabel` | **required**, display name |
| `AnalyticsWorkspaceId` | **required** — this is what scopes a viz to a workspace, and what you change to port it |
| `Description`, `Language`, `NamespacePrefix`, `Version` | |
| `TemplateSource`, `TemplateAssetSourceName` | provenance when created from a template |
| `LastDraftModifiedDate`, `LastPublishedDate` | draft vs published lifecycle |

## `AnalyticsVizField` — one row per field on the shelf
| Field | Notes |
|---|---|
| `VisualizationId` | **required**, parent |
| `FieldKey` | **required** — the key that appears in `F29`-style save errors |
| `SemanticObjectApiName`, `SemanticFieldApiName` | the binding back into the semantic model |
| `Role`, `Function`, `Type`, `DisplayCategory` | picklists: dimension/measure, aggregation, etc. |
| `Label` | shelf label |
| `AdHocCalc` | inline calculation |
| `Positional`, `PositionName`, `UniqueIndex` | placement on rows/columns/marks |
| `HierarchyName` | |

**This is the object behind the viz save errors.** A save failure naming something like `F29` is a
`FieldKey`; translate it via `AnalyticsVizField` rather than guessing. The discrete/continuous half
of those messages is boilerplate and usually not the real cause.

## Reading an existing viz (works today)
```bash
sf data query -q "SELECT Id, DeveloperName, MasterLabel, AnalyticsWorkspaceId, Version \
  FROM AnalyticsVisualization ORDER BY LastModifiedDate DESC" --target-org <alias>

sf data query -q "SELECT FieldKey, Label, Role, Function, Type, DisplayCategory, \
  SemanticObjectApiName, SemanticFieldApiName, Positional, PositionName \
  FROM AnalyticsVizField WHERE VisualizationId = '<id>'" --target-org <alias>
```

## Recreate in another workspace: use the metadata file

Prefer the Metadata API over rebuilding three sets of sObject rows. The retrieved `.uaviz-meta.xml`
already contains the workspace name, the data source, every field, and the full spec, so a port is:

1. Retrieve the viz from the source org.
2. Rewrite `<analyticsWorkspace>` to the target workspace api name and `<dataSource>` to the target
   semantic model.
3. Repoint `<objectName>` and `<fieldName>` in each `<fields>` block if the target model uses
   different api names. The `fieldKey` values (`F2`, `F8`) are internal and can stay as they are, as
   long as the spec's `rows` / `columns` / `encodings` keep referring to the same keys.
4. `sf project deploy start -m "AnalyticsVisualization:<Name>" -o <target> --dry-run` first, then
   deploy for real.

**Untested end to end.** The retrieve half is verified; the deploy half has not been run. Validate
with `--dry-run` and confirm the viz opens in the UI before telling anyone it works.


## Changing a field label: the one easy write (verified 2026-08-18)

**`AnalyticsVizField` is `updateable: true`, and so is its `Label`.** A shelf label changes
with a single record update. No metadata deploy, no base64 round-trip, no opaque ErrorId.

```bash
sf data query -q "SELECT Id, FieldKey, Label, SemanticFieldApiName FROM AnalyticsVizField   WHERE VisualizationId IN (SELECT Id FROM AnalyticsVisualization WHERE DeveloperName='<Name>')"   -r csv -o <org>
sf data update record -s AnalyticsVizField -i <1Hb...> -v "Label='New Label'" -o <org>
```

Given how hostile every other visualization write is, reach for this first when the change is
only a label.

## Font sizing: which key drives what (verified 2026-08-18, cost three passes)

Sizes live in `visualSpecification.style.fonts`, one entry per element, each carrying `color`
and `size`. The names mislead.

| Key | What it actually sizes |
|---|---|
| `marks` | the mark itself |
| `markLabels` | the value label printed **on** a mark |
| `headers` | header cells, **including a lone discrete measure's value** |
| `fieldLabels` | the shelf caption |
| `axisTickLabels`, `legendLabels`, `actionableHeaders` | as named |

**The trap.** On a KPI-style chart, the big number is often NOT a mark. Check the spec:

```
columns: ["F2"]              F2 is a DISCRETE measure
rows:    []
marks.panes.encodings: []    nothing encoded as a mark
```

A discrete measure sitting alone on a shelf with an empty pane renders its value as a
**column header**. So `marks` and `markLabels` do nothing and **`headers` sizes the number**,
while `fieldLabels` sizes the caption above it. Read `rows` / `columns` /
`marks.panes.encodings` before changing a size, rather than trusting the key name.

## `style.fonts` vs `stylesheet`: only one is portable

| | Carries | Survives packaging? |
|---|---|---|
| `style.fonts` | color + size | **Yes** |
| `stylesheet` | color + size + **weight** | **No** |

`stylesheet` is what the **UI formatting panel** writes, and its presence pushes a chart past
`assetVersion 67.0`. Such a chart reads as `DOWNGRADE_VERSION_ERROR` and is *silently dropped*
from an App Template. **"Clear Styles" does not undo it**: the rules empty but
`"stylesheet": {"rules": []}` remains, and the bare key still blocks. The Metadata API cannot
repair it either, in place or as a copy; both attempts return opaque ErrorIds. **The only
recovery is rebuilding the chart from scratch.**

So: style charts by editing `style.fonts` in the JSON, never through the formatting panel.
The cost is that **bold is unreachable**, since only `stylesheet` carries `weight`.

Check any chart before shipping it:
```bash
sf api request rest "/services/data/v67.0/tableau/visualizations/<Name>?" -o <org>
# DOWNGRADE_VERSION_ERROR  ->  it carries a stylesheet and will be dropped
```

## `sourceVersion` is a build stamp, not a capability level

Each viz carries `sourceVersion {major, minor}` (`<version>67.13</version>` in the metadata
file). It records **the platform build at last save**, not anything about the chart. In one
workspace every chart saved before a cutover read 67.12 and everything after read 67.13,
with chart type predicting nothing. A blocked chart and a dozen working ones were all 67.13,
so **do not diagnose from the version number**; use the read check above.

## Deploying a modified viz

`AnalyticsVisualization` deploy **does** work, verified repeatedly 2026-08-18, for any asset
that reads clean at 67.0. Retrieve, edit the base64 `visualSpecification`, deploy the folder.
Use `--ignore-conflicts`, since a retrieve-then-edit always looks like a conflict. Earlier
reports that viz deploy is broken came from assets carrying a `stylesheet`; that is the
version ceiling, not a general defect.

## Known hazard (from prior work)
A viz spec can get into a corrupted state that survives a revert, producing save error
`-1665391842`. Save often, and abandon a poisoned sheet rather than fighting it.

Related: `tbx-workspace`, `tbx-dashboard`, `tbx-semantic-model`.
