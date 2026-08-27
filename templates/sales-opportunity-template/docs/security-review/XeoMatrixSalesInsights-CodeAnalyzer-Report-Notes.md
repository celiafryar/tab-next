# XeoMatrix Sales Insights - Code Analyzer Report Notes

**Package**: XeoMatrix Sales Insights (Managed 2GP)
**Namespace**: `xeomatrix`
**Subscriber Package Version ID**: `04tQQ00000FxUsfYAF` (v1.0.0-6)
**Scan target**: `force-app/` (the exact source the version was built from)
**Scan date**: 2026-08-27
**Report file**: `CodeAnalyzerReport.html` (also `CodeAnalyzerReport.json`)

## 1. Scan invocation

```
sf code-analyzer run \
  --rule-selector AppExchange \
  --rule-selector Recommended:Security \
  --config-file code-analyzer.yml \
  --target force-app \
  --output-file CodeAnalyzerReport.html \
  --output-file CodeAnalyzerReport.json
```

### 1.1 Rule selectors
`AppExchange` and `Recommended:Security`, as required for AppExchange submission.

### 1.2 Engines executed
Code Analyzer 5.14.0: pmd, eslint, retire-js, regex. All four completed.

## 2. Result

**0 violations.** No findings of any severity, so nothing was suppressed. Grep for inline suppressions in the package source returns zero:

```
grep -rnE "eslint-disable|SuppressWarnings" force-app   # 0
```

## 3. One engine disabled: flow

`code-analyzer.yml` contains:

```yaml
engines:
  flow:
    disable_engine: true
```

### 3.1 Justification
The package contains no Flow metadata, so the flow engine has nothing to scan. It is a Python-based scanner that errors without Python 3.10 or later, unrelated to package content.

### 3.2 What this disable does not hide
Nothing. The package's metadata types are AppFrameworkTemplateBundle, LightningComponentBundle, and StaticResource. The flow engine only scans `Flow` metadata.

## 4. Coverage summary

| File type | Count | Engines that scanned it |
|---|---|---|
| LWC JavaScript (`.js`) | 1 | eslint, retire-js, regex |
| LWC HTML / CSS / meta | 3 | eslint (html), regex |
| Template JSON (chain, workspace, model, 15 vizzes, dashboard, streams) | 31 | regex |
| CSV data | 10 | regex |
| PNG static resource | 1 | none applicable |

## 5. What is not in this package

No Apex, no Visualforce, no Aura, no Flow, no custom objects, no permission sets, no third-party JavaScript. PMD ran and had no Apex to scan.

## 6. Where to find the raw report

`docs/security-review/CodeAnalyzerReport.html` in the source repository; also uploaded on the listing's Upload Documentation page.

## 7. Re-scan policy

Every new package version is re-scanned with the same selectors before promotion.

## 8. Contact

XeoMatrix, via the listing's support contact.
