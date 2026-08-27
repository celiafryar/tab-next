# XeoMatrix Sales Insights - Security Reviewer's Guide

**Package**: XeoMatrix Sales Insights (Managed 2GP)
**Namespace**: `xeomatrix`
**Subscriber Package Version ID**: `04tQQ00000FxUsfYAF` (v1.0.0-6, Released)
**Review org**: orgfarm-a08e1b90c8 (Developer Edition, no namespace). Test login supplied in the submission form.
**Review org workspace**: `Sales_Opportunity`
**Date prepared**: 2026-08-27

## 1. What this package is (the 30-second model)

A Tableau Next App Template plus one display-only Lightning Web Component. An admin clicks Create App once; the template loads packaged sample CSVs into Data 360, builds a semantic model, fifteen visualizations, and one dashboard. The component draws the company logo on that dashboard from a packaged PNG.

The component does not query data, does not use the Tableau Next SDK, makes no network calls, and holds no credentials. Everything with data access is a standard platform asset created in the subscriber's own org by the chain, running as the admin who clicked Create App.

### 1.1 Third-party libraries

None.

### 1.2 Property conventions

All eight properties of `xeomatrix:xmDashboardImage` are cosmetic: `staticResourceName` (optional override, blank uses the packaged logo), `imageScale`, `horizontalAlignment`, `verticalAlignment` (enum strings), `imageOpacity` (integer 0 to 100, coerced and clamped), `backgroundColor` (CSS color string used only in a `style` attribute), `altText`. No property names a semantic model, object, field, org, or URL.

## 2. Navigation

1. Log into the review org and open the Tableau Next app.
2. Setup > Tableau Next > Templates shows **Sales Opportunity** (`xeomatrix__Sales_Opportunity_Data`), installed from the package.
3. App Hub shows the app **Sales Opportunity Insights** built from it (SuccessStatus, 93 of 93 tasks).
4. Open workspace **Sales_Opportunity** > dashboard **Sales Insights and Analysis**. The logo in the top-left tile is the packaged component; every other tile is a stock Tableau Next visualization or metric.

Platform note, expected and not a defect: an extension tile can show an error state until a dashboard is saved and the page refreshed after its properties are configured. The packaged dashboard is created already configured, so this does not apply to it.

## 3. Dashboard: Sales Insights and Analysis

### 3.1 `xeomatrix:xmDashboardImage` - XeoMatrix Logo Image
- **Description**: Renders one image in a tile with scale, alignment, and opacity controls.
- **Properties**: see 1.2.
- **Libs**: None.
- **Notes**: The image source is `@salesforce/resourceUrl/APEX_essential_components`, resolved by the platform at build time to the packaged static resource on the org's own domain. If `staticResourceName` is set, the component instead points at `/resource/<name>` on the same origin. Either way the load is same-origin and is a browser image load, not an API callout.

### 3.2 Everything else on the dashboard
Stock Tableau Next widgets (metrics, visualizations, filters, buttons, text, containers) defined in the template's dashboard JSON and created by the platform. No custom code.

## 4. The create chain (what runs at Create App)

`create-chain.json`, 48 nodes: 10 CSVUpsert, 10 DataStreamUpsert, 10 DataStreamRun, 1 WorkspaceUpsert, 1 SemanticModelUpsert, 15 VisualizationUpsert, 1 DashboardUpsert.

- `runAs` is `CurrentUser` on all 48 nodes. No `ProcessUser`.
- `dominoVariant` is `sfdc_internal__UnifiedAnalyticsDominoVariant`, the value emitted by the Tableau Next template tooling that generated the chain. It was not hand-authored and is the same value Salesforce's own Tableau Next templates carry.
- All `file` references are bundle-relative with no `..` segments.
- `variables.json` is empty and there is no `rules.json`. The template takes no user input at Create App, so there is no parameter injection surface.

## 5. Reviewer quick-reference

| Component | Type | Queries data | Network | DOM-string writes | Storage | Writes |
|---|---|---|---|---|---|---|
| xmDashboardImage | LWC | No | None (same-origin image load only) | No | No | No |
| Sales_Opportunity_Data | ATF template | Creates assets via the platform, as the invoking admin | Platform REST, same org | n/a | n/a | Creates streams, model, vizzes, dashboard |
| APEX_essential_components | StaticResource | n/a | n/a | n/a | n/a | n/a |

## 6. Independent verification

See Solution Architecture section 3.4 for the grep set. All commands return zero matches against the packaged source.

## 7. Contact

XeoMatrix, via the listing's support contact.
