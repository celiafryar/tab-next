# Tab Next — Tableau Next Semantics DX skills (Claude Code marketplace)

A Claude Code plugin marketplace of pro-code skills for building **Tableau Next / Data 360 semantic models as code**.

## Install

```
/plugin marketplace add celiafryar/tab-next
/plugin install tableau-next-semantics@tab-next
```

Then `/reload-plugins` (or restart Claude Code).

## What's inside — plugin `tableau-next-semantics`

Three field-tested skills (auto-available once installed):

- **tableau-semantics-dx** — the pro-code loop: retrieve, edit JSON, validate, deploy; plus platform gotchas (API-name suffixes, 255-char description cap, hide fields via `isVisible`, `primaryNameField` as the Many-to-One lever).
- **semantic-descriptions-from-spreadsheet** — turn a metadata workbook into agent-ready field/table descriptions and deploy them in bulk.
- **tableau-semantic-relationships** — define joins and cardinality in `relationships.json`, including true Many-to-One.

## Notes

- Private repo: people adding this marketplace need access to it (or make it public for open sharing).
- Future skill families beyond Tableau Next will live in their own separate repos/marketplaces.
