# XeoMatrix Sales Insights - Sample API Callouts

**Package**: XeoMatrix Sales Insights (Managed 2GP), namespace `xeomatrix`, `04tQQ00000FxUsfYAF`

## Summary

This package makes zero API callouts. No component in it contacts any external host, and no component calls a Salesforce or Tableau Next REST API from code.

## 1. What "API callout" means for this review

Any HTTP request initiated by package code to a host other than the org itself, or any direct REST call initiated by package code, including Named Credential or Remote Site Setting usage.

## 2. What the package contains

One ATF template (declarative JSON and CSV), one display-only LWC, one PNG static resource. No Apex, no Named Credentials, no Remote Site Settings, no External Services, no DataActionTarget or webhook definitions.

## 3. Network activity that is present, and why it is not a callout

### 3.1 Same-origin image load
`xmDashboardImage` renders `<img src={resolvedSrc}>`. `resolvedSrc` is the value of `@salesforce/resourceUrl/APEX_essential_components`, which the platform compiles to a URL on the org's own domain, or `/resource/<name>` if the admin sets an override. This is the browser loading a packaged static asset from the same origin. Tableau Next's CSP (`connect-src 'self'`) would block anything else.

### 3.2 Platform-executed chain
At Create App, the Tableau Next chain engine calls its own internal REST endpoints to create streams, the semantic model, visualizations, and the dashboard. Those calls are made by the platform, in the invoking admin's session, to the same org. The package supplies only the declarative definitions.

## 4. Independent verification

```
grep -rnE "fetch\(|XMLHttpRequest|WebSocket|EventSource|SharedWorker" force-app/main/default/lwc   # 0
grep -rn "resourceUrl" force-app/main/default/lwc   # 1: the import in xmDashboardImage.js
grep -rlE "NamedCredential|RemoteSiteSetting|ExternalService|DataActionTarget" force-app   # 0
```

`package.xml` of the MDAPI conversion lists exactly AppFrameworkTemplateBundle, LightningComponentBundle, StaticResource.

## 5. Sample request / response / headers

Not applicable. There are no callouts to sample.

## 6. Cross-references

Solution Architecture sections 3, 5. Security Reviewer's Guide section 3.1.

## 7. Contact

XeoMatrix, via the listing's support contact.
