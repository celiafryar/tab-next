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

## Known hazard (from prior work)
A viz spec can get into a corrupted state that survives a revert, producing save error
`-1665391842`. Save often, and abandon a poisoned sheet rather than fighting it.

Related: `tbx-workspace`, `tbx-dashboard`, `tbx-semantic-model`.
