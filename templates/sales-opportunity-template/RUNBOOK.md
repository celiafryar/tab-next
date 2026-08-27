# Sales Opportunity Insights: build, package, install, verify

Current state (2026-08-27): shipped as a **2GP managed package**, namespace `xeomatrix`,
built on the XeoMatrix PBO Dev Hub. Version 1.0.0.6 = `04tQQ00000FxUsfYAF`, Released.
Install link: https://login.salesforce.com/packaging/installPackage.apexp?p0=04tQQ00000FxUsfYAF
Full managed story is in the "Managed 2GP result" section at the bottom. The 1GP unmanaged
section below is the earlier proven path (2026-08-24) and is kept as history.

The namespaced-org semantic-model defect (BUG 4, CDP_DATA_OBJECT_FIELDS_NOT_FOUND) only
affects subscriber orgs that themselves have a namespace registered. Normal customer orgs
are unaffected; the managed package installs and runs clean in them.

## What ships

`force-app/main/default/appTemplates/Sales_Opportunity_Data/` - the ATF template (48-node
create chain: 10 CSVs -> 10 streams -> 10 runs -> workspace -> semantic model -> 15
visualizations -> dashboard), `lwc/xmDashboardImage` (the logo widget) and
`staticresources/APEX_essential_components` (the logo image). No ContentAsset.

## Package, 1GP unmanaged (historical, superseded by the managed 2GP build)

2GP (`sf package version create`) is preferred when `Package2` exists in the packaging org.
In orgs where 2GP provisioning never materializes (observed: orgfarm-a08e1b90c8, 40+ min
after enabling the toggle), the classic path works:

1. Setup > Package Manager > New (unmanaged). Name it.
2. Add > Component Type **"App Template"** (that is the picker's name for
   AppFrameworkTemplateBundle) > check the bundle > Add to Package.
3. Add > Component Type **"Asset File"** > check APEX_essential_components > Add.
4. Upload > version name > Upload. The resulting page shows the
   **Installation URL**: `https://login.salesforce.com/packaging/installPackage.apexp?p0=<04t>`
   (use test.salesforce.com for scratch/sandbox targets).

v1.0 = `04tjV0000000msf`. **End-to-end verified 2026-08-24**: installed into a second org via the URL, Create App ran the 48-node chain to SuccessStatus in ~72 min, 10/10 streams with exact row counts.

## Install rules (each verified by hitting the failure)

- A package cannot install into the org that built it ("namespace collision").
- Fresh uploads take a few minutes to propagate; premature installs fail with
  "No record found for SELECT AppExchange..." - retry, don't diagnose.
- An org that already contains a same-name ContentAsset fails with "Duplicate Name".
  Delete the org's copy first; the package restores it under the identical developer name
  and existing dashboards re-bind. Only affects our own dev orgs, never a clean customer org.
- CLI equivalent of the URL: `sf package install --package <04t> -o <org> --wait 10 --no-prompt`.

## Verify (never claim done without it)

1. Template appears: `GET /services/data/v67.0/app-framework/templates?`.
2. Create App: `POST /app-framework/apps?` with `{"templateSourceId":"<1zD>","label":...,"name":...,"templateValues":{}}`; read `app.id` (nested under `app`).
3. Watch `applicationStatus` on the app and `lastRunStatus` across the 10 streams.
   Healthy pace: first stream SUCCESS ~6 min, ~6 min per stream serial, full chain ~60 min
   (verified 3705 s in data-enterprise-6013).
4. **Engine-stall failure mode:** if no new task schedules within ~2 min of an ingestion
   completing, the org's chain engine is broken (observed twice in orgfarm-a08e1b90c8,
   UI- and API-launched; the same chain completed 48/48 elsewhere). Nothing resumes it.
   Change orgs; report the org id to Salesforce.

## Cleanup in test orgs

Decouple before Delete on apps (delete alone leaves ghost asset claims). Template delete
works via `DELETE /app-framework/templates/<id>?` with an `@empty.json` body. Every failed
Create retry mints suffixed asset copies; use fresh app names.

## Logo fix: LWC extension widget (2026-08-26)

Why: a managed install renames the ContentAsset to xeomatrix__APEX_essential_components but the dashboard JSON keeps the bare name. Celia's managed test in 3917 (app NS_Managed_Test, 2026-08-26 20:20) failed at upsert_dashboard_Sales_Insights_and_Analysis with:

    Cause: [widgetName=image_logo, widgetType=image] ContentAsset not found with name: APEX_essential_components

The other 64 nodes passed, including the semantic model, so BUG 4 does not affect normal subscriber orgs.

Fix (commit 6cf415d): the native image widget is replaced by lwc/xmDashboardImage, which loads the logo through @salesforce/resourceUrl, so the namespace is compiled in. The ContentAsset is gone; the logo ships as staticresources/APEX_essential_components.

Proof, unmanaged path, 3917:
- template SO_LWC_Logo_Test (1zDdi0000000CpBEAU), app SO_LWC_Logo_E2E2 (1zAdi00000008wrEAA)
- SuccessStatus, 93/93 nodes, 3616 s
- created dashboard 0Trdi0000000LcLCAU, widget logo_extension status Ok, source c:xmDashboardImage
- logo renders in the viewer

Managed path: resolved the same night. Install does not rewrite c: to xeomatrix; the bundle now carries xeomatrix:xmDashboardImage in both fields. See "Managed 2GP result" below.

Gotcha: an org holding the managed xeomatrix__Sales_Opportunity_Data will not register chains for an unmanaged deploy of the same template name (CHAINNOTFOUND). Rename the test copy.

## Managed 2GP result (2026-08-27)

Package XeoMatrix Sales Insights, 0HoQQ000000i4Cn0AI, namespace xeomatrix, PBO Dev Hub.

Finding: managed install does not rewrite extension widget references in template JSON. Create App resolves c:xmDashboardImage but stores it verbatim, and the viewer then cannot load it. The form that works at both create and render is the namespaced one in both fields:

    "source": {"name": "xeomatrix:xmDashboardImage", "namespace": "xeomatrix", "type": "LightningWebComponent"},
    "parameters": {"fullyQualifiedName": "xeomatrix:xmDashboardImage", ...}

Probe matrix (five one-widget templates in 1.0.0.5, run in 3917):
- c: + fqn xeomatrix:   create OK, stored as xeomatrix
- bare name, ns xeomatrix, fqn bare   create OK, stored as c (does not render)
- xeomatrix__xmDashboardImage   create fails, not found
- bare name, ns xeomatrix, fqn xeomatrix:   create OK
- xeomatrix: in both   create OK, renders (this is the shipped form)

Final proof: 1.0.0.6 = 04tQQ00000FxUsfYAF, installed fresh in 3917, app SO_Managed_Final3 (1zAdi00000009OHEAY), SuccessStatus 93/93 in 3638 s, dashboard 0Trdi0000000M3lCAE, logo renders.

Gotchas:
- Beta versions cannot be upgraded in place. Uninstall, then install the new version.
- sf project delete source also deletes the local files. Builds 1.0.0.3 and 1.0.0.4 shipped without the LWC because of this.
- Managed LWC bundles need a few minutes after install before the chain can resolve them.

Promoted to Released 2026-08-27: 04tQQ00000FxUsfYAF (XeoMatrix Sales Insights 1.0.0.6). Install URL: https://login.salesforce.com/packaging/installPackage.apexp?p0=04tQQ00000FxUsfYAF

Review org proof (2026-08-27): c8 orgfarm-a08e1b90c8 (permanent Developer Edition, no namespace). Installed 1.0.0.6 through the public install link, app Sales_Opportunity_Insights (1zAjV00000006lNUAQ) SuccessStatus 93/93 in 4096 s, dashboard 0TrjV0000000RD7SAM, logo renders. BUG 3 (chain stall in c8) did not recur.
