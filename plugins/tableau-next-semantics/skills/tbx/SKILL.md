---
name: tbx
description: >-
  Orchestrator for the tbx-* Tableau Next / Data 360 skill family. Routes a request to the right
  specific skill (tbx-dataobject, tbx-semantic-model, tbx-workspace, tbx-viz, tbx-dashboard) and
  owns the end-to-end sequences — build a workspace from raw CSVs, or digest an existing workspace
  and recreate it elsewhere. Start here when the task spans more than one layer.
---

# tbx — Tableau Next end to end

Router for the `tbx-*` family. Load the specific skill you need rather than everything; each is
single-concern so a side-track doesn't cost you the rest.

## Which skill

| You want to… | Skill | Verbs |
|---|---|---|
| Audit CSVs, load them as data streams / DLOs, set the load-time primary key | **`tbx-dataobject`** | `prep` `load` `edit` `delete` |
| Create or change a semantic model, add objects / calcs / metrics / relationships | **`tbx-semantic-model`** | `create` `describe` `add` `deploy` `delete` |
| Create a workspace, attach assets, enumerate what a workspace holds | **`tbx-workspace`** | `create` `attach` `digest` |
| Read or build a visualization | **`tbx-viz`** | `read` `create` `recreate` |
| Read a dashboard (create is unsolved) | **`tbx-dashboard`** | `digest` |
| Formula syntax, metric rules, description authoring, geo roles | `tableau-semantics-dx` and friends | — |

## Sequence A — build from raw files

1. **`tbx-dataobject prep`** — audit every file first. Keys, types, and category are **permanent
   after load**. Ask the user about anything that looks off; do not choose silently.
2. **`tbx-dataobject load`** — one stream per file, then `actions/run`, then **`verify`**: rows
   landed equals rows sent, `lastProcessedRecords` equals `totalRecords`, provenance ledger
   printed. An HTTP 200 is not a load.
3. **`tbx-semantic-model create`** — three fields, then `add` one object per table with
   `shouldIncludeAllFields: true`.
4. Relationships, descriptions, calcs, metrics — `tableau-semantic-relationships`,
   `tableau-semantics-dx`, `tableau-business-preferences`.
5. **`tbx-workspace create` + `attach`** — attach the semantic model *and* the data objects, or the
   workspace looks empty.
6. **Mock first, then build only what the user approves.** Generate a simple static HTML mock of
   the proposed visualizations and dashboard layout, discuss it with the user, and iterate; keep
   it low-fi. Then `tbx-viz` for the approved charts, and dashboards in the UI (create is not yet
   scriptable). This family's job is everything BEFORE this point: once the semantic model is
   loaded with its definitions, visualization and dashboard design is user-led, not automated.

## Sequence B — digest an existing workspace and recreate it elsewhere

1. **`tbx-workspace digest`** — enumerate assets by type via `analytics.browse` on the documented
   GraphQL endpoint, or straight SOQL.
2. **`tbx-semantic-model describe`** — GET the model. **Unescape HTML** before reusing any string.
3. **`tbx-viz read`** — `AnalyticsVisualization` + its `AnalyticsVizField` rows.
4. **`tbx-dashboard digest`** — structure is readable; rebuilding is manual for now.
5. Recreate in dependency order: data objects -> semantic model -> workspace -> viz -> dashboards.
   Repoint `AnalyticsWorkspaceId` and any `SemanticObjectApiName` / `SemanticFieldApiName`.

## Cross-cutting rules
- **Trailing `?` on every REST path**, and **`--body "@file"`** with the `@`, even on DELETE.
- Redirect stdout to a file before parsing JSON; the CLI's update notice corrupts it.
- **Prefer granular writes** (`POST …/data-objects`) over the full-model `PUT`, which is full state
  and deletes anything you omit.
- **The APIs are self-describing.** Unknown fields come back named, missing required params come
  back named, bad enums come back named. Probe rather than guess.
- **Validation passing proves nothing.** Verify numbers against the source or the Data Cloud SQL API.
- Ingest-time decisions (primary key, category, field types) cannot be undone. Confirm them.

## FIRST: the permissions preflight. Run this before building anything.

Three orgs in a row (2026-08-12 to 2026-08-14) came up with Tableau Next half-provisioned. The
symptoms look like defects in whatever you happen to be doing, so check this **before** you spend a
day debugging a model. Two independent layers fail differently:

### Layer 1 — the human user's license

```sql
SELECT PermissionSetLicense.MasterLabel FROM PermissionSetLicenseAssign
WHERE Assignee.Username = '<user>'
```

**`Customer Data Platform` must be present.** Without it every Data Cloud call returns
`FUNCTIONALITY_NOT_ENABLED: "This feature is not currently enabled for this user"`, and data streams
and semantic models both read as **zero even when the tables are loaded**. Check seat availability
too: `SELECT MasterLabel, TotalLicenses, UsedLicenses FROM PermissionSetLicense`. A scratch org may
ship exactly one seat, already consumed by another user, in which case nothing can be assigned until
it is freed.

### Layer 2 — the SERVICE context (this is the one that causes render failures)

```sql
SELECT Name, (SELECT Id FROM Assignments) FROM PermissionSet
WHERE Name IN ('HyperionCASCPermSet','C2CAnalyticsStoragePermSet',
               'SemanticAnalyticsAgentPermSet','ActorCASCPermSet',
               'C2CMcpServicePermSet','ConnectivityServiceCASCPermSet')
```

Six Salesforce-authored permission sets, namespace `force`, created at org creation. They belong to a
**hidden Platform Integration User** (`cloud@<orgid>`), which is the identity Tableau Next's server
side runs as. **Provisioning frequently creates them and stalls before assigning them.**

**Anything less than 6 means Tableau Next is broken**, in ways that never name the real cause:

- "We hit a snag! Event fired" dialogs, from the telemetry beacon being access-refused
  (`markup://aura:noAccess`)
- The semantic model editor never boots. Network capture shows it never even requests the model
- The workspace page renders "Not Found / Can't display assets" for a workspace that is fine
- `AnalyticsVisualization` deploys fail with **opaque ErrorIds** rather than real messages

**⚠️ Count from the `PermissionSet` side.** Filtering `PermissionSetAssignment` on
`PermissionSet.Name` silently returns zero rows for these sets, making a healthy org look broken. The
same traversal trap hides ordinary permission sets on a user — count with
`SELECT COUNT(Id) FROM PermissionSetAssignment WHERE AssigneeId = '<id>'` instead.

### The fix, which Setup cannot do

Setup's Add Assignment picker dead-ends: these require the `Cloud Integration User` license, which
backs only hidden platform users, so it cannot render an eligible-user list. **The API accepts the
insert anyway:**

```bash
U=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE 'cloud@%'" -o ORG --json | ...)
sf data create record -s PermissionSetAssignment \
  -v "AssigneeId=$U PermissionSetId=<perm set Id>" -o ORG
```

Six inserts, about ten seconds. Verified 2026-08-14: the editor then opened, visualizations deployed,
and deploy failures started returning **real error messages** instead of ErrorIds.

Do not confuse this with the user's own permission sets. `Tableau Next Admin`, `Data Cloud Admin` and
friends go to the human; these six go to `cloud@<orgid>`. Holding every admin permission set does not
help if the service context has none.

### What this does NOT fix

- **Namespaced orgs** still fail semantic model validation with `CDP_DATA_OBJECT_FIELDS_NOT_FOUND`.
  That is a separate, genuinely namespace-specific defect. A managed package requires a namespace, so
  this remains a hard blocker for packaging.
- **Dashboard creation** still fails through every API (see `tbx-dashboard`).

## Connecting the MCP server to test the model

The only proof a model works is asking it live questions, and the Tableau Next MCP server is how you
do that from here. Setting it up in a fresh org:

1. **Deploy the External Client App as metadata** rather than rebuilding it in Setup. Retrieve the
   three components from a working org and strip the identity fields so the new org mints its own:
   `<orgScopedExternalApp>` from the `.eca-meta.xml`, `<consumerKey>` from the
   `.ecaGlblOauth-meta.xml`, `<oauthLink>` from the `.ecaOauth-meta.xml`. Scopes `RefreshToken, MCP`.
2. **Read the new consumer key back** with a retrieve, then
   `claude mcp add --transport http --scope user --client-id "<key>" --callback-port 38000 <name> <url>`.
   Scratch and sandbox orgs use the `/sandbox/` path segment; production omits it.
3. **Tick Enable MCP Service (Beta) by hand** at Setup -> Quick Find "User Interface". It is **not**
   in the `UserInterface` settings metadata, so it cannot be read or set from the CLI. Without it the
   `MCP` scope is inert.
4. **RESTART Claude Code before looking for the server in `/mcp`.** The picker is built from the
   servers loaded at session start, so a server added mid-session appears in `claude mcp list` but
   **not** in the `/mcp` list. Do not tell the user to look again, and do not re-register it — both
   waste their time. Restart, then it is there.

Gotchas that cost a session each:
- **`http://127.0.0.1` is rejected outright.** Salesforce grants the plaintext-HTTP exception only to
  the literal hostname `localhost`. There is no way to register a `127.0.0.1` callback.
- **`redirect_uri_mismatch` usually means the wrong server was picked**, not a bad callback URL. Two
  registrations can share a URL and differ only by which org you log into. Decode `client_id` and
  `resource` from the authorize URL in the browser address bar to see which entry actually fired, and
  delete stale registrations (`claude mcp remove <name> --scope user`) so there is nothing to misclick.
- "Allow access to External Client App consumer secrets via REST API" is **not** needed; PKCE with an
  optional secret is what authenticates.

## Known gaps
- **Dashboard creation** — no supported path found. Try the Metadata API first.
- **File staging** — `POST /ssot/data-streams` needs a CSV already staged in S3, and staging needs
  a live Lightning session (wizard, or the proven-but-unpackaged in-page route). CLI-only ingest
  waits on the Bulk Ingestion API: connected app, Data Cloud token exchange to the tenant's
  `c360a` host, and an Ingestion API connector, none of which exist yet in the test orgs.
- **Workspace create/attach are Aura**, not documented REST.
- **Dataspace filters** fail against the `default` dataspace; likely intended for additional ones.

Open ideas and unfinished threads live in `TBX-TODO.md` in the `tab-next` repo.
