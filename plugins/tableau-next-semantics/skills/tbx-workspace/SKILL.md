---
name: tbx-workspace
description: >-
  Create Tableau Next workspaces, attach data/semantic-model/viz assets to them, and DIGEST an
  existing workspace (enumerate every asset it contains) so it can be recreated elsewhere. Verbs:
  create, attach, digest. Use when standing up a new Tableau Next workspace, wiring assets into
  one, or auditing/porting what an existing workspace holds.
---

# tbx-workspace — create, attach, and digest Tableau Next workspaces

**Status: all three verbs verified live 2026-08-07** (create and attach through the UI flow, digest
over SOQL). One digest nuance learned: the GraphQL `browse(where: {AssetApiName: {eq: "<ws>"}})`
query returns the workspace record itself, not its contents; enumerate contents with SOQL on
`AnalyticsWorkspaceAsset` filtered by `AnalyticsWorkspaceId` (below).

A workspace is a **container of references**, not copies. That is the key fact for
recreate-in-a-new-workspace: you re-point at existing assets, you don't rebuild them.

---

## `create`

```jsonc
aura://AnalyticsController/ACTION$createWorkspace
{ "workspace": { "label": "Boston Bluebikes", "description": "…" } }
```
Two fields. The API name is derived server-side from the label (`Boston Bluebikes` ->
`Boston_Bluebikes`) and becomes the URL: `/tableau/workspace/Boston_Bluebikes`.

**Caveat: this is Aura, not a documented API.** Treat it as evidence of what the UI does. There is no
REST equivalent, and `AnalyticsWorkspace` is `createable: false` on the sObject API.

**But there is a supported path worth trying first (added 2026-08-12).** `AnalyticsWorkspace` is a
Metadata API type, suffix `.uawork`, directory `analyticsWorkspaces/`. Retrieve is verified, with 19
workspaces coming back cleanly from `orgfarm-2c0399dee5`, which means a workspace can at minimum be
versioned and diffed as a file. Deploy has **not** been tested. Same lesson as `tbx-viz` and
`tbx-dashboard`: an sObject describe saying `createable: false` says nothing about the Metadata API,
so check `sf org list metadata-types` before concluding a thing cannot be written.

```bash
sf project retrieve start -m "AnalyticsWorkspace:<ApiName>" -o <alias>
```

## `attach`

```jsonc
aura://AnalyticsController/ACTION$batchCreateWorkspaceAsset
{ "workspaceIdOrApiName": "Boston_Bluebikes",       // id OR api name
  "isBulk": true,
  "workspaceAssets": { "workspaceAssets": [
    { "assetId": "0gONS000002sDVN2A2",
      "assetType": "MktDataLakeObject",
      "assetUsageType": "Referenced" }
  ]}}
```
Bulk-native — one call attaches many assets. `assetUsageType: "Referenced"` confirms the
pointer-not-copy model.

## `digest` — enumerate a workspace over the DOCUMENTED GraphQL endpoint

Unlike create/attach, reading is fully supported:
```bash
POST /services/data/v66.0/graphql?
{"query":"query { analytics { browse(first: 100, where: {AssetApiName: {eq: \"Boston_Bluebikes\"}}) { totalCount edges { node { id: Id type: ApiName } } } } }"}
```
- The Query root exposes exactly three fields: `analytics`, `managed_content`, `uiapi`.
- `Analytics__Analytics` has exactly **one** field, `browse`, with args
  `where, assetTypes, orderBy, first, orgId, after`. It is **read-only** — there are no analytics
  mutations (the Mutation root has one field, `uiapi`, the generic sObject CRUD namespace).
- **Introspection is enabled**, so the schema can describe itself:
  `{ __type(name: "Analytics__Analytics") { fields { name args { name } } } }`.

**Asset type enum** (from the UI's own browse query):
`ANALYTICS_WORKSPACE`, `ANALYTICS_DASHBOARD`, `ANALYTICS_VISUALIZATION`, `SEMANTIC_MODEL`,
`MKT_DATA_LAKE_OBJECT`, `MKT_DATA_MODEL_OBJECT`.

Assets are also directly SOQL-readable (`AnalyticsWorkspace`, `AnalyticsWorkspaceAsset`,
`AnalyticsDashboard`, `AnalyticsVisualization`, …), which is often simpler than GraphQL for a digest.

## Asset taxonomy a workspace can hold
An empty workspace offers exactly five things to create: **Data**, **Data Transform**,
**Semantic Model**, **Visualization**, **Dashboard**. A complete digest-and-recreate has to cover
all five.

## Recreate: what is and isn't supported

| Asset | Create path | Supported? |
|---|---|---|
| Data streams / DLOs | `POST /ssot/data-streams` | documented REST ✓ (`tbx-dataobject`) |
| Semantic model | `POST /ssot/semantic/models` + sub-resources | documented REST ✓ (`tbx-semantic-model`) |
| Workspace + asset links | `AnalyticsController` Aura for create/attach; `.uawork` metadata retrieves | **undocumented for create**, retrieve supported |
| Visualization | `.uaviz` metadata, or the `AnalyticsVisualization` sObject | documented ✓ (`tbx-viz`) |
| Dashboard | `.uadash` metadata | validated, not yet performed (`tbx-dashboard`) |

Related: `tbx-dataobject`, `tbx-semantic-model`, `tbx-viz`, `tbx-dashboard`.
