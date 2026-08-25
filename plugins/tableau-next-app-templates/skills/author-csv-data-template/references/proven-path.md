# The proven path: build, package, install, verify (Sales Opportunity Insights v1.0)

The reusable pipeline, verified live 2026-08-24. Source of truth is this repo; the org is
disposable. No namespace anywhere, deliberately: the namespaced-org semantic-model defect
(CDP_DATA_OBJECT_FIELDS_NOT_FOUND) is unfixed, so managed/AgentExchange packaging waits on
Salesforce.

## What ships

`force-app/main/default/appTemplates/Sales_Opportunity_Data/` - the ATF template (48-node
create chain: 10 CSVs -> 10 streams -> 10 runs -> workspace -> semantic model -> 15
visualizations -> dashboard), plus `contentassets/APEX_essential_components` (the dashboard
logo; ship it or one missing image fails the whole dashboard).

## Package (1GP unmanaged, no Dev Hub needed)

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
