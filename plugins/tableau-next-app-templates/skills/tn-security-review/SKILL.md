---
name: tn-security-review
description: >-
  Prepare a released Tableau Next managed package (template + LWC + static
  resources) for the AppExchange / AgentExchange security review: run Salesforce
  Code Analyzer with the AppExchange rule sets, build the Checkmarx MDAPI zip,
  audit the create chain and any LWC for what reviewers grep for, generate the
  five reviewer documents (Solution Architecture, Security Reviewer's Guide,
  Code Analyzer notes, Sample API Callouts, Reviewer Notes) as markdown and PDF,
  and set up the permanent review org. Use when the user mentions security
  review, Checkmarx, Code Analyzer, AppExchange submission, Partner Console,
  reviewer documents, or a released package that needs to be reviewed.
---

# tn-security-review

Input: a **promoted** 2GP version (04t) and its exact source tree. Output: a folder the
publisher uploads on the listing's Upload Documentation page, plus a review org with the
package installed and one built app. Format follows Salesforce Labs' own review kit (Bump
Chart, Essentials Pack), which is what the reviewers are used to reading.

Read `../package-tn-template/references/managed-packaging-gotchas.md` for the platform
facts the documents cite.

## What the review actually requires

Per the Salesforce Labs kit (Trust Review intake, 2026-08):

| Artifact | Required |
|---|---|
| Solution Architecture & Usage | Yes |
| Checkmarx results, or a "no Apex" statement (the LWC still gets scanned) | Yes |
| Code Analyzer report (AppExchange + Recommended:Security) | Yes |
| False-positive documentation | Only if there are findings |
| Sample API callouts | State "none" with verification if none |
| Security Reviewer's Guide, Reviewer Notes | Expected in practice |
| Review org with the package installed from the public link, plus a test login | Yes |
| SBOM, Agent Evaluation Suite, ECA/OAuth attestation | N/A for template + display LWC |

Plan on a 6 to 8 week queue. Edits to the listing after submission trigger another review,
so finish the listing copy first.

## Step 1: scan and zip

```
bash scripts/scan.sh <project dir>
```

Runs Code Analyzer (`--rule-selector AppExchange --rule-selector Recommended:Security`,
flow engine disabled via `code-analyzer.yml` because there is no Flow metadata), writes
`docs/security-review/CodeAnalyzerReport.{html,json}`, converts the source to MDAPI, checks
`package.xml` lists every expected type, and zips it with the folder as the top-level entry
(`<Pkg>-Managed-<ver>-mdapi.zip`). Target is 0 violations; anything left needs a
False-Positive Report in the kit's format (file, line, rule, why, snippet).

The zip is a build artifact: keep it out of git, hand it over directly.

## Step 2: audit what reviewers check

```
python3 scripts/audit.py <force-app dir> --namespace <ns>
```

Reports, for the documents: `runAs` per node (must be all `CurrentUser`), `dominoVariant`
(tooling emits `sfdc_internal__UnifiedAnalyticsDominoVariant`; say so, do not hide it),
path traversal, `chainDefinitions[].name`, `template-policy.json` contents, variables and
rules presence, metadata type inventory and file count, and the LWC grep set (fetch/XHR/
WebSocket, innerHTML/document.write, storage, dynamic import, eval, eslint-disable). Every
grep must return zero for the "what the package never does" claims to be true.

## Step 3: generate the documents

```
python3 scripts/render-docs.py --package "<Name>" --namespace <ns> --version <04t> \
  --version-label 1.0.0-6 --review-org <org domain> --workspace <ws> \
  --out docs/security-review
```

Fills `templates/*.md` with the package facts and renders PDFs with headless Chrome
(no pandoc needed). Then **edit the prose**: the templates describe the reference package
(one App template, one display-only image LWC, one PNG). Anything your package does
differently (SDK queries, more components, variables, Apex) must be written in, section by
section. Section numbering is the kit's; keep it.

Style: short sentences, no em dashes, plain claims backed by a grep or an ID. Reviewers
verify, they do not trust.

## Step 4: the review org

- Permanent Developer Edition, no namespace, Tableau Next and Data 360 provisioned. Not a
  scratch org (expires) and not an Enterprise trial (expires).
- Install with the public link `https://login.salesforce.com/packaging/installPackage.apexp?p0=<04t>`,
  admins only, accept the "not yet on AppExchange" acknowledgement.
- Run Create App once (`../package-tn-template/scripts/create-app.sh`), verify the
  dashboard renders, leave the app in place. Record app id, workspace, dashboard id in the
  Reviewer's Guide section 2.
- A reviewer login is a human step: Setup > Users > New User, System Administrator, reset
  the password, put the credentials in the submission form. Never type passwords for the
  user.

## Step 5: hand-off list for the publisher

The Partner Console steps are the publisher's (they need the partner login):
1. Publishing > Listings > open or create the listing; Technology section: select the
   released version.
2. Upload Documentation: the five PDFs and the Code Analyzer HTML.
3. Submit the MDAPI zip for the Checkmarx scan (Partner Community request).
4. Add the review org test credentials.
5. Request the security review; send back the case number.

## Files

- `scripts/scan.sh`: Code Analyzer + MDAPI zip.
- `scripts/audit.py`: chain and LWC audit, prints the facts the documents need.
- `scripts/render-docs.py`: fills templates, renders PDFs.
- `templates/`: the five documents with `{{placeholders}}`, written for a template + display
  LWC package. Reference filled-in set: `templates/sales-opportunity-template/docs/security-review/`
  in this repo (XeoMatrix Sales Insights 1.0.0.6, 2026-08-27).
