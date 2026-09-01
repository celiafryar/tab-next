# {{PACKAGE}} - Solution Architecture and Usage

**Package**: {{PACKAGE}} (Managed 2GP)
**Namespace**: `{{NAMESPACE}}`
**Subscriber Package Version ID**: `{{VERSION_ID}}` (v{{VERSION_LABEL}}, Released)
**Publisher**: {{PUBLISHER}}
**Date prepared**: {{DATE}}

## 1. Solution summary

A Tableau Next App Template. When an admin runs Create App from it, the template builds a complete sales analytics app inside the subscriber org: it loads ten CSV files of sample sales data into Data 360 data streams, creates a workspace, a semantic model, fifteen visualizations, and one dashboard. The dashboard shows a company logo through a small Lightning Web Component included in the package.

The package ships exactly three metadata components:

| Component | Type | Purpose |
|---|---|---|
| `{{NAMESPACE}}__{{TEMPLATE}}` | AppFrameworkTemplateBundle | The template: 10 CSVs, 10 data stream definitions, workspace, semantic model, 15 visualizations, 1 dashboard, 48-node create chain |
| `{{NAMESPACE}}__{{LWC}}` | LightningComponentBundle | Display-only image widget for the dashboard logo |
| `{{NAMESPACE}}__{{STATIC_RESOURCE}}` | StaticResource | The logo, a 256 x 256 PNG |

It ships nothing else. No Apex, no Visualforce, no Aura, no Flow, no custom objects or fields, no permission sets, no Named Credentials, no Remote Site Settings, no external services, no scheduled jobs, no Data Cloud segments, activations, or calculated insight templates.

## 2. Basic usage instructions

### 2.1 Installation

Install with the standard package URL: `https://login.salesforce.com/packaging/installPackage.apexp?p0={{VERSION_ID}}`. Admin-only install is sufficient. The org needs Tableau Next and Data 360 provisioned.

### 2.2 Creating the app

Setup > Tableau Next > Templates (or the Templates page in the Tableau Next app) > Sales Opportunity > Create App. There are no variables to fill in. The chain runs about 60 minutes, most of it CSV ingestion. Progress is visible in App Install History.

### 2.3 Runtime behavior

The created assets are ordinary Tableau Next assets owned by the subscriber org. The dashboard queries the semantic model through the Tableau Next platform in the viewing user's session. The logo widget renders one packaged image and does nothing else.

### 2.4 Uninstalling

Uninstall the package from Setup > Installed Packages. Apps created from the template remain in the org. Their dashboards keep working except the logo tile, which shows an "extension unavailable" state once the component is removed.

## 3. Detailed information flow

### 3.1 The actors

1. The admin who installs the package and runs Create App.
2. The Tableau Next chain engine, which executes the 48 create-chain nodes as that admin (`runAs: CurrentUser` on every node).
3. The Tableau Next dashboard runtime, which instantiates `{{NAMESPACE}}:{{LWC}}` in a sandboxed tile.

### 3.2 Sequence

1. Install copies the three components into the org. Nothing runs at install time.
2. Create App reads the bundle files (all references are bundle-relative, no `..` segments) and executes the chain: CSV upload, data stream create and run, workspace, semantic model, visualizations, dashboard.
3. When the dashboard is viewed, the platform loads the logo component. The component reads its packaged static resource through `@salesforce/resourceUrl`, which the platform resolves to a same-origin URL. The browser loads the image from the org's own domain.

### 3.3 What the package never does

- No outbound network calls of any kind. The component contains no `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, dynamic `import()`, or script tag.
- No reads of the semantic model or any Salesforce data from the component. It has no SDK query and no data properties.
- No writes to Salesforce beyond the assets the chain creates.
- No browser storage: no `localStorage`, `sessionStorage`, `indexedDB`, or cookies.
- No HTML string injection: no `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, or `DOMParser`.

### 3.4 Verification

Run against the packaged source (`force-app/main/default/lwc/{{LWC}}`):

```
grep -rnE "fetch\(|XMLHttpRequest|WebSocket|EventSource|SharedWorker" lwc/{{LWC}}   # 0
grep -rnE "innerHTML|outerHTML|document\.write|insertAdjacentHTML|DOMParser" lwc/{{LWC}}   # 0
grep -rnE "localStorage|sessionStorage|indexedDB|document\.cookie" lwc/{{LWC}}   # 0
grep -rnE "import\(|<script|eval\(" lwc/{{LWC}}   # 0
grep -rn "runAs" appTemplates/{{TEMPLATE}}/create-chain.json | grep -vc CurrentUser   # 0
grep -rn '\.\./' appTemplates/{{TEMPLATE}}   # 0
```

## 4. Authentication

4.1 The package performs no authentication of its own. 4.2 It performs no authorization of its own; the chain runs with the invoking admin's permissions and the created assets follow the org's Tableau Next sharing. 4.3 There is no unauthenticated access path; everything runs inside an authenticated Salesforce session.

## 5. Encryption on data transfer

5.1 The component initiates no transfers. 5.2 Platform-mediated traffic (the chain's REST calls, the dashboard's queries, the image load) is HTTPS to the org's own domain. 5.3 Nothing is stored in the browser. 5.4 No third-party services.

## 6. Data touchpoints

6.1 The chain creates data streams and a semantic model from the packaged CSVs. The CSVs are synthetic sample data (fictional accounts, opportunities, products, users). 6.2 The package does not read, copy, or export any existing subscriber data. 6.3 No data retention by the package. 6.4 No export.

## 7. Cross-site scripting posture

The component's template is one `<img>` element. Its `src` is the compiled resource URL, its `alt` is a config-panel string bound as an attribute, and all styling is built as CSS strings from typed or enum-constrained properties that are lower-cased, coerced with `Number()`, and clamped before use. Nothing is rendered as HTML. Lightning Web Security is on by default and is not bypassed.

## 8. Third-party libraries

None. The static resource is an image, not code.

## 9. Static analysis

Salesforce Code Analyzer 5.14.0, rule selectors `AppExchange` and `Recommended:Security`, run against the exact packaged source of {{VERSION_LABEL}}: **0 violations** across PMD, ESLint, retire-js, and regex. The flow engine was disabled because the package contains no Flow metadata (see the Code Analyzer notes).

## 10. Contact and support

{{PUBLISHER}}, via the listing's support contact.

## 11. Reference

Source and runbook: `tab-next` repository, `templates/sales-opportunity-template/`.
