---
name: tbx-viz
description: >-
  Read and create Tableau Next visualizations programmatically via the AnalyticsVisualization,
  AnalyticsVizField, and AnalyticsVizViewDef sObjects — the closest thing to a "visualization.json".
  Verbs: read (digest an existing viz), create, recreate (port a viz to another workspace). Use when
  auditing, versioning, or rebuilding Tableau Next visualizations outside the UI.
---

# tbx-viz — visualizations as records

**Status: partial.** The objects, their CRUD capability, and their field shape are verified. An
actual create has **not** yet been exercised, and the contents of `AnalyticsVizViewDef` (the chart
spec proper) have not been decoded. See `TBX-TODO.md`.

**The important finding: visualizations ARE createable through a documented API, and dashboards are
not.** So a viz can be versioned and rebuilt in code; a dashboard currently cannot.

```
AnalyticsVisualization   create ✓  update ✓  delete ✓  query ✓
AnalyticsVizField        create ✓  update ✓  delete ✓  query ✓
AnalyticsVizViewDef      create ✓  update ✓  delete ✓  query ✓
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

## Recreate in another workspace — the theory
Because `AnalyticsWorkspaceId` is just a reference, porting a viz should be: read the
`AnalyticsVisualization` + its `AnalyticsVizField` rows + its `AnalyticsVizViewDef`, then re-create
them against the new workspace id, with `SemanticObjectApiName` / `SemanticFieldApiName` repointed
if the target model uses different api names. **Untested — verify before relying on it.**

## Known hazard (from prior work)
A viz spec can get into a corrupted state that survives a revert, producing save error
`-1665391842`. Save often, and abandon a poisoned sheet rather than fighting it.

Related: `tbx-workspace`, `tbx-dashboard`, `tbx-semantic-model`.
