---
name: tbx-dashboard
description: >-
  Read and (eventually) recreate Tableau Next dashboards. Dashboards are currently READ-ONLY to
  supported APIs — every AnalyticsDashboard* sObject is createable:false — so this skill can digest
  a dashboard fully but cannot yet rebuild one. Use when auditing dashboard structure, tracing which
  dashboards use a metric before renaming it, or diagnosing widget errors.
---

# tbx-dashboard — dashboards can be read, not yet written

**Status: digest works, create is UNSOLVED.** This is the one gap in the digest-and-recreate story.
See `TBX-TODO.md`.

## The blocker, stated plainly
Every dashboard-side sObject is **`createable: false`**:
```
AnalyticsDashboard          AnalyticsDashboardPage      AnalyticsDashboardWidget
AnalyticsDashboardLayout    AnalyticsDashboardViewDef   AnalyticsDashboardViewSpec
AnalyticsDashPageWidget     AnalyticsMetricWidgetDef    AnalyticsVizWidgetDef
AnalyticsFilterWidgetDef    AnalyticsTextWidgetDef      AnalyticsButtonWidgetDef
AnalyticsContainerWidgetDef AnalyticsParamWidgetDef
```
All are `queryable: true`. The GraphQL Mutation root has a single field (`uiapi`, generic sObject
CRUD), so there is no analytics mutation either. The UI creates dashboards through
`AnalyticsController` Aura actions.

**Unexplored options, in order of promise:**
1. **Metadata API** — check `sf org list metadata-types` for a dashboard type. This would be a
   supported path and is the first thing to try.
2. Capture and replay the `AnalyticsController` Aura create. Works, but undocumented and brittle
   (framework uid and token rotate).
3. Build dashboards in the UI as a deliberate final manual step, and script everything up to them.

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
  overruns another. **Fix the canvas, not the label.**
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
