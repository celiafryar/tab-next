---
name: package-tn-template
description: >-
  Package a working Tableau Next App Template (AppFrameworkTemplateBundle, plus
  any LWC and static resources it needs) as a managed 2GP package, install it
  into a clean test org, prove Create App end to end, and promote it. Use when
  the user asks to package a template, build a managed or 2GP package, create
  an install link, promote a version, test an install in another org, or fix a
  template that works when source-deployed but fails after a managed install
  (namespace prefix, ContentAsset not found, CHAINNOTFOUND, extension widget
  errors). Pair with tn-security-review for the AppExchange submission.
---

# package-tn-template

Turn a template that already runs clean when source-deployed into a released managed
package with proof. Proven end to end on XeoMatrix Sales Insights 1.0.0.6
(`04tQQ00000FxUsfYAF`), 2026-08-26 to 27. The full evidence trail is in
`templates/sales-opportunity-template/RUNBOOK.md` in this repo.

Read `references/managed-packaging-gotchas.md` first. Every item in it cost real hours.

## The three orgs

| Role | What it must be | Why |
|---|---|---|
| Dev Hub | The Partner Business Org (or any Dev Hub with the namespace registered and Package2 enabled) | Only place `sf package version create` works. Not a scratch org. |
| Test org | A permanent Developer Edition org with **no namespace**, Tableau Next and Data 360 provisioned, never held the source-deployed template | The honest subscriber. A namespaced org breaks the semantic model (BUG 4). A scratch org expires in 30 days. |
| Publisher | none needed | The package is hosted by Salesforce under the Dev Hub. |

Never test in the org that built the source, and never keep a source-deployed copy and
the managed copy of the same template in one org (CHAINNOTFOUND).

## Step 1: preflight the bundle

```
python3 scripts/preflight.py <path-to-force-app> --namespace <ns>
```

Fails loudly on the things a managed install silently breaks:

- `contentassets/` present or any `"type": "image"` widget with a `source.name` (ContentAsset
  lookups are not namespace-rewritten; replace with an LWC image widget, see gotchas).
- Extension widgets whose `source.name` / `parameters.fullyQualifiedName` are not
  `<ns>:<component>` in both fields.
- `chainDefinitions[].name` not null.
- Nodes missing `parameters.minorVersion` when `assetVersion` is 67.0.
- Any `runAs` other than `CurrentUser`.
- Any `..` in a bundle path.
- `.forceignore` missing `code-analyzer.yml` / `CodeAnalyzerReport.*`.

Fix everything it reports before building. The same script is what tn-security-review
runs again on the released source.

## Step 2: project config

`sfdx-project.json` on the packaging branch:

```json
{
  "packageDirectories": [{ "path": "force-app", "default": true,
    "package": "<Package Name>", "versionName": "ver 1.0", "versionNumber": "1.0.0.NEXT" }],
  "namespace": "<ns>", "sourceApiVersion": "67.0",
  "packageAliases": { "<Package Name>": "<0Ho...>" }
}
```

`config/project-scratch-def.json` must exist for `--code-coverage` validation (a minimal
Developer edition def is enough; the build org is ephemeral).

First time only: `sf package create --name "<Package Name>" --package-type Managed --path force-app -v <hub>`.
Running it again with the same name errors; it does not duplicate.

## Step 3: build

```
sf package version create -p "<Package Name>" --code-coverage --installation-key-bypass --wait 40 -v <hub> --json
```

Poll with `sf package version create list -v <hub> --created-last-days 0`. About five
minutes. Once a version is Released, the next build needs a higher `versionNumber`.

Confirm the version really contains what you think:
`sf project convert source --root-dir force-app --output-dir /tmp/x && cat /tmp/x/package.xml`
must list every type you expect (AppFrameworkTemplateBundle, LightningComponentBundle,
StaticResource). Builds 1.0.0.3 and 1.0.0.4 of the reference package shipped without the
LWC because `sf project delete source` had removed the local files. Check before you build.

## Step 4: install into the test org

Before installing, clear false-pass traps in the test org:

```
sf data query -t -q "SELECT DeveloperName, NamespacePrefix FROM LightningComponentBundle" -o <test>
sf data query -q "SELECT Name, NamespacePrefix FROM StaticResource" -o <test>
sf data query -q "SELECT DeveloperName, NamespacePrefix FROM ContentAsset" -o <test>
sf api request rest "/services/data/v67.0/app-framework/templates?" -o <test>
```

Any bare (namespace null) copy of a packaged component, or a same-named source template,
must be removed first, or a `c:` reference will resolve to the stray copy and pass for the
wrong reason.

A beta version cannot be upgraded in place. Uninstall the previous beta, then install:

```
sf package uninstall -p <old 04t> -o <test> --wait 15
sf package install -p <04t> -o <test> --wait 20 --no-prompt
```

For the final proof use the public link instead, since that is what customers use:
`https://login.salesforce.com/packaging/installPackage.apexp?p0=<04t>`.

After install, confirm the LWC landed (`<ns>__<component>` in the query above) and the
template has both chains: `.../app-framework/templates/<1zD>/chains?`. Wait a few minutes
before Create App; managed LWC bundles are not resolvable immediately after install.

## Step 5: Create App and monitor

```
bash scripts/create-app.sh <test-org> <template 1zD> <AppName>
```

Posts the create request and polls every 60 s until SuccessStatus or FailedStatus, then
prints the dashboard node result and any failed node message. A ten-CSV template takes
about an hour; each stream ingests in roughly six minutes. Run it detached with `nohup`.

Then verify the dashboard actually references the packaged component:

```
bash scripts/verify-dashboard.sh <test-org> <DashboardApiName>
```

Expect `status Ok`, `source.name <ns>:<component>`, and `source.id` equal to the
`<ns>__` bundle's Id. Open the dashboard in a browser and look at the tile. The chain can
report success while the viewer fails (that was the `c:` bug), so the screenshot is part of
the proof.

## Step 6: promote

Only after Step 5 passes in a clean org:

```
sf package version promote -p <04t> -v <hub> --no-prompt
```

Promoted versions are immutable and component API names are frozen forever. Decide the
template API name and LWC name before this point. Labels can still change in a later
version.

## Step 7: record it

Append to the project's RUNBOOK: version id, test org, app id, task summary, dashboard id,
what changed. Commit `sfdx-project.json` with the new alias. Hand off to tn-security-review.

## Failure signatures

| Message | Cause | Fix |
|---|---|---|
| `ContentAsset not found with name: X` at DashboardUpsert | Native image widget; asset installed as `ns__X` | Replace with LWC image widget + static resource |
| `We couldn't find LightningComponentBundle with name: c:X` | LWC not in the package, or written as `c:` | Check package.xml; write `ns:X` |
| Dashboard created but tile shows Something Went Wrong | Reference stored as `c:X`; viewer loads by FQN | Write `ns:X` in both fields |
| `CHAINNOTFOUND` on Create App | Same-named source + managed template in one org, or `chainDefinitions[].name` not null | Remove the duplicate; set name null |
| `Cannot upgrade beta package` on install | Beta in place | Uninstall first |
| Create App fails at SemanticModelUpsert with `CDP_DATA_OBJECT_FIELDS_NOT_FOUND` | Subscriber org itself has a namespace (BUG 4) | Test in a non-namespaced org |
| Chain stalls after first ingestion, no error | BUG 3 (org-specific, not seen since 2026-08-27) | Try another org |
| Apps still listed after DELETE returned 204 | List endpoint lag | GET the app id; trust the 204 |
