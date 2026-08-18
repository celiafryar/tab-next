---
name: tbx-dashboard
description: >-
  Read, version, and port Tableau Next dashboards through the Metadata API, which retrieves a
  dashboard's full widget list and grid geometry as a .uadash-meta.xml file. Use when auditing
  dashboard structure, moving a dashboard between orgs, tracing which dashboards use a metric before
  renaming it, or diagnosing widget errors. Note the sObject layer is read-only. A real create FAILS on the
  Metadata API, REST and MCP, but SUCCEEDS through an App Template Framework DashboardUpsert
  node (verified 2026-08-18). Outside ATF, build dashboards in the UI.
---

# tbx-dashboard: read the sObjects, write the metadata

**Status: digest works. Create fails on Metadata API / REST / MCP, but WORKS through the App
Template Framework, verified 2026-08-18. See the create section.** Corrected 2026-08-12; this skill
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

## `create` / `port`: DOES NOT WORK

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

### ANSWERED 2026-08-14: it was performed, and it does NOT work

Someone did step 1. The dry run's `State: Created` was misleading — a real deploy fails.

```
AnalyticsDashboard  Executive_Insights
An unexpected error occurred. Please include this ErrorId if you contact support:
  1148518231-1386  (-1759713720)
```

Tried and failed identically, same trailing code each time: remapped to the target workspace/model/
fields; the same with stale `<workspace>` elements corrected; the same stripped of `<version>` and
`<workspaceAssetRelationships>`. Then, to eliminate the source file entirely, **a 2.7 KB dashboard
with zero visualization references also failed**. So it is not the content, the widgets, or the port.

**The other write paths fail too:**

| Path | Result |
|---|---|
| Metadata API `.uadash` | opaque ErrorId, even for a minimal empty dashboard |
| `POST /services/data/v67.0/tableau/dashboards?` | `RESOURCE_CREATE_FAILURE`: *"You can't add this dashboard. Your Salesforce admin can help with that."* |
| Tableau Next MCP server | no write capability at all; every tool is `list_*` / `get_*` / `search_assets` / `analyze_data` |
| **App Template Framework `DashboardUpsert`** | **WORKS. Verified 2026-08-18** |

### CORRECTION 2026-08-18: ATF is a fourth path, and it succeeds

A `DashboardUpsert` node inside an App Template create chain **does** create a real dashboard,
42 widgets across 3 pages, in an org that started empty. So "dashboard create fails on every
API" is too strong. It fails on the three paths above; it works through ATF.

ATF also returns **real, specific errors** where the others return opaque ErrorIds. A failing
run named the offending widget outright:

```
RESOURCE_CREATE_FAILURE: You can't add this dashboard.
Cause: [widgetName=image_1, widgetType=image]
       ContentAsset not found with name: apexmotioncomponentsfulllogotranspa
```

**Two things worth carrying from that:**

1. **An image widget references a `ContentAsset` by developer name**, a record that lives in
   the org and not in the bundle. Ship a dashboard to another org without it and the create
   fails. **One unresolvable image fails the ENTIRE dashboard**, not just that widget.
2. That reference is invisible to the usual portability sweeps: it is neither a record id nor
   a `__dll` name, just a lowercase string that looks like a label.

The REST message is permission-shaped, but it was produced by a user holding Tableau Next Admin,
Tableau Next Platform Analyst and Data Cloud Admin, in an org with all six service permission sets
assigned, a valid semantic model, and **nine visualizations deployed successfully into the same
workspace minutes earlier**. So whatever gates dashboard creation is not reachable by an
administrator.

**Tell users plainly: outside of ATF, dashboards must be built by hand in the UI.** A dashboard can be *retrieved* as
metadata but not deployed anywhere, so porting an accelerator between orgs means rebuilding every
dashboard widget by widget.

**What you can still do:** retrieve the source dashboard and print its layout as a build sheet —
grid `columnCount` / `rowHeight`, then per page each widget's `row`/`column`/`colspan`/`rowspan` with
its resolved source. Resolve widget names through the `<widgets>` blocks (`<widgetName>` plus one of
`vizWidgetDefs` / `metricWidgetDefs` / `filterWidgetDefs` / `containerWidgetDefs`), since
`<pageWidgets>` references them only by name via `<analyticsDashboardWidget>`. That turns a rebuild
into transcription rather than guesswork.

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
