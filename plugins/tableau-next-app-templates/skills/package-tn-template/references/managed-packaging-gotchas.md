# Managed packaging gotchas for Tableau Next templates

Everything here was hit for real while shipping XeoMatrix Sales Insights (2026-08-24 to 27).
Shared by package-tn-template and tn-security-review.

## Names inside template JSON are never rewritten

The packager and the installer namespace-prefix real metadata (LWC becomes `ns__comp`,
StaticResource becomes `ns__res`) but never touch strings inside an
AppFrameworkTemplateBundle's JSON. Consequences:

- A native `image` widget with `"source": {"name": "Logo"}` looks for a ContentAsset named
  `Logo`; the package installed it as `ns__Logo`; Create App fails at DashboardUpsert with
  `ContentAsset not found`. Salesforce's own 97 templates avoid this by never referencing a
  packaged component by name. Fix: an LWC extension widget that loads the image through
  `@salesforce/resourceUrl`, which the LWC compiler namespaces for you.
- An extension widget written as `c:comp` is accepted at Create App (the chain resolves it
  against the package) but stored verbatim; the viewer then loads `c:comp`, which does not
  exist in a subscriber, and the tile shows Something Went Wrong. `ns__comp` fails at
  create. Only `ns:comp` in both `source.name` and `parameters.fullyQualifiedName` works at
  create and render. Proven with five probe templates.
- There is no expression-language token for the package namespace. `${Org.Namespace}` is
  the subscriber's namespace (blank for real customers); `${Template.Namespace}` does not
  exist ("Variable part [Namespace] not found in context map"). Bake the namespace in.

## Authoring rules that only bite after packaging

- `chainDefinitions[].name` must be null in template-info.json.
- Set `parameters.minorVersion` (`"13"` for API 67.0) on every chain node, not just the
  viz and dashboard nodes.
- `runAs: CurrentUser` on every node. Reviewers grep for it.
- All `file` refs bundle-relative, no `..`. Template Builder emits some without a leading
  slash (`csvs/X.csv`); that works.
- `variables.json` `{}` and no `rules.json` means no parameter injection surface, which the
  reviewers like. If you add variables, keep them typed.
- `template-policy.json` from the Template Builder is
  `{"type":"AccessCheck","parameters":{"hasTemplateAccess":"always"}}`. Ship it as is unless
  Salesforce asks for something tighter.

## Org rules

- Test in a non-namespaced org. A subscriber org that has its own namespace registered
  breaks the semantic model node (`CDP_DATA_OBJECT_FIELDS_NOT_FOUND`, BUG 4).
- A permanent Developer Edition org for the review, not a scratch org (30-day expiry) and
  not an Enterprise trial.
- One org cannot hold a source-deployed template and the managed copy with the same name.
  The source copy's chains fail to register and Create App returns CHAINNOTFOUND.
- Before testing, delete any bare copy of a packaged component (LWC, static resource,
  ContentAsset) from the test org. A `c:` reference resolves to the stray copy and gives a
  false pass. This trap was avoided twice and would have hidden the real bug.
- A package cannot install into the org that built it (1GP). 2GP built on the Dev Hub can
  install into any other org, including a Dev Ed that once hosted a 1GP.

## CLI traps

- `sf project delete source --metadata X` deletes the LOCAL source files too. Two package
  builds shipped without the LWC because of this. Retrieve or restore before building.
- Beta 2GP versions cannot be upgraded in place: `Cannot upgrade beta package`. Uninstall,
  then install. Released versions upgrade normally.
- `sf package version create` needs `--installation-key-bypass` (or a key) and
  `--code-coverage` for a promotable build; `--code-coverage` needs
  `config/project-scratch-def.json`.
- After a version is Released, the next build needs a higher `versionNumber`.
- 1GP packages cannot be uninstalled by CLI; use Setup > Installed Packages.
- `sf api request rest` needs a trailing `?` on app-framework paths and `--body @empty.json`
  on DELETE. App DELETE returns 204 and works, but the list endpoint lags for minutes.
- Managed LWC bundles take a few minutes after install before the chain engine can resolve
  them.
- The Node version matters: `PATH=$HOME/.nvm/versions/node/v22.23.1/bin:$PATH` or the CLI
  throws `Invalid regular expression flags`.
- Use `sf org open --url-only --path <page> --json` for a fresh frontdoor URL when a browser
  session expires.

## Timing

- Ten CSV streams ingest in series at about six minutes each: budget 60 to 70 minutes per
  Create App. Run the monitor detached with `nohup`.
- Package version build: about five minutes. Install: under a minute.
- The Tableau Next dashboard viewer takes 10 to 20 seconds to render a full dashboard;
  screenshot after the skeleton is gone.
