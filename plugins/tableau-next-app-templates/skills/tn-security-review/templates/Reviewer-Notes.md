# {{PACKAGE}} - Reviewer Notes

Package `{{VERSION_ID}}`, v{{VERSION_LABEL}}, managed, namespace `{{NAMESPACE}}`.

1. **Scans.** Salesforce Code Analyzer (AppExchange + Recommended:Security): 0 violations. Checkmarx: submitted as the MDAPI zip `{{SLUG}}-Managed-{{VERSION_LABEL}}-mdapi.zip`; results attached when available. No suppressions anywhere.

2. **One engine disabled.** The Code Analyzer flow engine is disabled because the package has no Flow metadata. Details in the Code Analyzer notes.

3. **No false positives to document.** Zero findings.

4. **Architecture in one line.** A declarative Tableau Next template plus a display-only LWC that shows a packaged PNG. No Apex, no callouts, no data access from code, no browser storage, no HTML injection. All chain nodes run as the invoking admin (`runAs: CurrentUser`).

5. **`dominoVariant`.** The chain carries `sfdc_internal__UnifiedAnalyticsDominoVariant`. This value is emitted by the Tableau Next Template Builder that generated the chain and matches Salesforce's own Tableau Next templates. We did not author it and do not depend on any internal capability.

6. **Data Cloud metadata.** The template creates data streams and a semantic model in the subscriber org from packaged synthetic CSVs at Create App time. The package itself ships no Data Cloud metadata types (no DMO, segment, activation, or calculated insight definitions); the platform creates those assets as ordinary org-owned objects when the admin runs the template.

7. **Review org.** Developer Edition org `{{REVIEW_ORG}}`, package installed from the public install URL, one app created (Sales Opportunity Insights, 93 of 93 tasks), dashboard renders. Test credentials in the submission form.

8. **Uninstall.** Created apps survive uninstall; only the logo tile shows an unavailable state afterward.
