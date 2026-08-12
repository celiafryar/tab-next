---
name: tbx-dashboard
description: >-
  Read, version, and port Tableau Next dashboards through the Metadata API, which retrieves a
  dashboard's full widget list and grid geometry as a .uadash-meta.xml file. Use when auditing
  dashboard structure, moving a dashboard between orgs, tracing which dashboards use a metric before
  renaming it, or diagnosing widget errors. Note the sObject layer is read-only; the Metadata API is
  the write path and a real create is validated but not yet performed.
---

# tbx-dashboard: read the sObjects, write the metadata

**Status: digest works. Create is VALIDATED but not yet performed.** Corrected 2026-08-12; this skill
previously stated that dashboard create was unsolved. That conclusion came from looking only at the
sObject layer.

## Two layers, two different answers

**The sObject layer is genuinely read-only.** Every dashboard-side sObject is `createable: false`:
```
AnalyticsDashboard          AnalyticsDashboardPage      AnalyticsDashboardWidget
AnalyticsDashboardLayout    AnalyticsDashboardViewDef   AnalyticsDashboardViewSpec
AnalyticsDashPageWidget     AnalyticsMetricWidgetDef    AnalyticsVizWidgetDef
AnalyticsFilterWidgetDef    AnalyticsTextWidgetDef      AnalyticsButtonWidgetDef
AnalyticsContainerWidgetDef AnalyticsParamWidgetDef
```
All are `queryable: true`. The GraphQL Mutation root has a single field (`uiapi`, generic sObject
CRUD), so there is no analytics mutation either.

**The Metadata API is a different story.** `AnalyticsDashboard` is a retrievable and deployable
metadata type, suffix `.uadash`, directory `analyticsDashboards/`. Do not conclude "read-only" from
an sObject describe again; check `sf org list metadata-types` first.

## `digest` over the Metadata API: the whole dashboard in one file
```bash
sf project generate -n dashprobe --template empty
cd dashprobe
sf project retrieve start -m "AnalyticsDashboard:<DeveloperName>" -o <alias>
# or every dashboard in the org:
sf project retrieve start -m "AnalyticsDashboard" -o <alias>
```

The retrieved `.uadash-meta.xml` carries what the sObject queries only give you in pieces:
`analyticsWorkspace`, `customConfig` (HTML-escaped JSON holding query cache settings), and a
`layouts` block with `columnCount`, `maxWidth`, and one `pageWidgets` entry per widget with its
`row`, `column`, `rowspan`, and `colspan`. That is the full grid geometry, which is what you need to
port a dashboard rather than just describe it.

**Verified 2026-08-12** against `orgfarm-2c0399dee5`: all 24 dashboards in the org retrieved cleanly.

## `create` / `port`: validated, not yet performed

A validate-only deploy of a retrieved dashboard under a **new** `DeveloperName` returns
`State: Created`, meaning the Metadata API accepts it as a creatable component:

```bash
# copy the file, rewrite DeveloperName and masterLabel, then:
sf project deploy start -m "AnalyticsDashboard:<NewName>" -o <alias> --dry-run
```

**Be honest about what this proves.** A dry run proves the component validates against the org's
metadata rules. It does not prove a real deploy lands a working, openable dashboard, and it does not
prove the widget references resolve. Before claiming create works:
1. Deploy for real into a throwaway workspace, not a customer's.
2. Open the dashboard in the UI and confirm every widget renders, not just that the deploy went green.
3. Tear it down and record the result here.

Until someone does that, describe this as "validated, untested" to users. Do not sell it as working.

**Still true:** the UI itself creates dashboards through `AnalyticsController` Aura actions. Replaying
those is undocumented and brittle (framework uid and token rotate), and is no longer needed now that
a supported path exists.

## `mock` — design before building

Dashboards are user-led; this skill's job is to make the conversation cheap. Before any viz or
dashboard is built, generate a **simple static HTML mock** of the proposed layout (metric tiles,
charts, filters, rough placement), show it to the user, and iterate until they approve. Keep it
deliberately low-fi: the mock exists to decide WHAT to build, not to look like Tableau. Then
build only the approved items (`tbx-viz` for charts; dashboards assembled in the UI).

Bake the platform limits into the mock so the discussion stays honest:
- A metric tile's title is the metric's label; there is **no per-widget title override**.
- Number formatting lives on the **widget**, not the metric or model.
- Canvas widths differ per dashboard (e.g. 1200px/48col vs 1600px/96col); a label that fits one
  overruns another.
- Metric breakdowns accept only Text, Number, Boolean, Email, PhoneNumber, Url dimensions (no
  geo-roled fields), and must never cross a one-to-many hop.

## `digest` — what you CAN read today
```bash
# every dashboard, and the widgets on it
sf data query -q "SELECT Id, DeveloperName, MasterLabel, AnalyticsWorkspaceId FROM AnalyticsDashboard" --target-org <alias>
sf data query -q "SELECT Id, Label, AnalyticsDashboardPageId FROM AnalyticsDashboardWidget" --target-org <alias>
sf data query -q "SELECT Id, ColumnCount, RowHeight, MaxWidth FROM AnalyticsDashboardLayout" --target-org <alias>

# which dashboards reference a given metric — run BEFORE renaming one
sf data query -q "SELECT Id, Source FROM AnalyticsMetricWidgetDef" --target-org <alias>
```

## Field facts worth knowing (from prior work)
- **`AnalyticsMetricWidgetDef.Source`** holds the metric apiName a widget points at. This is how you
  find every dashboard using a metric before you rename or delete it.
- **`AnalyticsDashboardWidget.Label` is empty on every metric widget** and populated only for
  filters. So a metric tile's title comes from the *metric's* label — there is **no per-widget title
  override**, and one label must serve every dashboard it appears on.
- **`AnalyticsDashboardLayout`** exposes `ColumnCount`, `RowHeight`, `MaxWidth`. Differing canvas
  widths (e.g. 1200px/48col vs 1600px/96col) are why an identical label fits one dashboard and
  overruns another. **Fix the canvas, not the label.** The same values appear in the retrieved
  `.uadash-meta.xml` as `columnCount` and `maxWidth`, alongside each widget's grid position.
- **Number format lives here, not in the model.** A metric has no format property; a tile's decimals
  come from the widget's style settings. Don't deploy model changes hoping to fix formatting.

## The stale-catalog gotcha
A metric created *after* a dashboard exists fails **in that dashboard only**:
`Error when loading invalid metric: <apiName> in dashboard!` from
`analytics_dashboard/metricWidget.js` — while `/validate` says `isValid: true` and the metric
renders fine in its own dialog and in a **new** dashboard. The widget holds a stale metric catalog.
Fix: hard refresh, remove and re-add the widget, or use a new dashboard. Warn customers about this;
the error names nothing useful and looks like a broken metric.

Related: `tbx-viz` (visualizations, which ARE createable), `tbx-workspace`, `tbx-semantic-model`.
