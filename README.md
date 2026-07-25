# Tab Next

A Claude Code **plugin marketplace** of pro-code skills for building **Tableau Next / Salesforce Data 360 semantic models as code**. Describe every table and field, define relationships and cardinality, and deploy, all version-controlled in Git and tuned for **Tableau Pulse** and **Agentforce**.

> A marketplace is simply a Git repo that Claude Code can install plugins from. You add this repo once, install the plugin below, and its skills load automatically. They trigger on their own when you work on a semantic model, or you can call one by name (for example, `/tableau-semantics-dx`).

---

## What you get

Installing the **`tableau-next-semantics`** plugin adds three field-tested skills:

| Skill | What it does | It kicks in when you |
|---|---|---|
| **tableau-semantics-dx** | The core pro-code loop: retrieve a model as JSON, edit it, validate, deploy. Carries the platform know-how and gotchas. | edit a retrieved `Semantic Models/...` folder, add calculated fields, metrics, or descriptions, or deploy and debug. |
| **semantic-descriptions-from-spreadsheet** | Turns a metadata workbook into agent-ready field and table descriptions and writes them into the model in bulk. | have a data dictionary and want high-quality descriptions for conversational analytics. |
| **tableau-semantic-relationships** | Authors joins and cardinality directly in `relationships.json`, including true Many-to-One. | build or fix relationships from a cardinality spec, or debug a relationship deploy error. |

The three are designed to work together: fill a metadata workbook, describe and relate the model, then deploy.

---

## Prerequisites

These skills automate a real toolchain, so you need it in place first:

- **Salesforce CLI** (`sf`), installed and authorized to your org.
- **VS Code** (or Cursor) with the **Salesforce Extension Pack** and the **Salesforce Tableau Semantics** extension.
- A Salesforce org with **Data 360 and Tableau Next** provisioned.
- **Git**, for versioning the model.

Tip for org login: `sf org login web` against the generic login page can time out. Target your org's own domain instead:
`sf org login web --instance-url https://YOUR-DOMAIN.my.salesforce.com --alias my-org --set-default -b chrome`.

---

## Install

```text
/plugin marketplace add celiafryar/tab-next
/plugin install tableau-next-semantics@tab-next
/reload-plugins
```

This repo is **private**, so you need read access to it (you will authenticate with your GitHub account or `gh`). See **Access** below.

## Manage and update

Use the `/plugin` menu to add, update, disable, or remove marketplaces and plugins, then run `/reload-plugins` to apply. When this repo publishes a new version, update the marketplace and reinstall the plugin to pull the change.

---

## How it works (quick start)

1. **Retrieve** the target model in VS Code: right-click the `Semantic Models` folder, then **Tableau Semantic: Retrieve Model to Folder**. This writes a folder of JSON files.
2. **Provide the input** the skill asks for: a metadata workbook (for descriptions) or a cardinality spec (for relationships). Each skill prompts for this and confirms what it found before doing anything.
3. **Let the skill edit the JSON** (`dataObjects.json`, `relationships.json`, and so on), matching your model by field and table labels.
4. **Validate and deploy** from the extension: right-click `model.json`, then **Validate Model**, then **Deploy Model**.
5. **Commit** to Git for history, review, and rollback.

A blank intake template for the description workflow (tables, fields, roles, primary keys, relationships, business synonyms) can be produced by the `semantic-descriptions-from-spreadsheet` skill on request.

---

## Capabilities and hard-won rules

The skills already encode these, but they are useful to know:

- **Match by label, not API name.** Data Cloud makes field API names globally unique, so `Sales` can become `Sales2`. Always resolve fields by their label.
- **Descriptions cap at 255 characters** (both field and table). Validate passes even when a description is too long; only Deploy catches it.
- **Hide system and lineage fields** with `isVisible: false` (for example `cdp_sys_*`, `KQ_*`, `Data_Source*`, `Internal_Organization*`, `uuid_temp*`).
- **Many-to-One needs `primaryNameField`.** Set the parent object's `primaryNameField` to its business key to enable Many-to-One. The field-level `isPrimaryKey` flag is read-only and does nothing.
- **The relationship graph must be acyclic.** Two fact tables sharing several dimensions creates a cycle; make one fact the hub. You can change an existing relationship's cardinality, but not its left (child) side. Re-orienting one means delete and recreate.

---

## Access

The repo is private. Anyone who adds this marketplace needs read access. To open it to everyone, make the repo public:

```text
gh repo edit celiafryar/tab-next --visibility public
```

---

## Repo structure

```text
tab-next/
  .claude-plugin/
    marketplace.json                 # the marketplace definition
  plugins/
    tableau-next-semantics/          # one plugin, three skills
      .claude-plugin/
        plugin.json                  # the plugin manifest
      skills/
        tableau-semantics-dx/
        semantic-descriptions-from-spreadsheet/
        tableau-semantic-relationships/
  README.md
```

The `plugins/` layout leaves room to add more Tableau Next plugins to this same marketplace later.

---

## Maintaining this marketplace

Each skill's source of truth lives in `~/.claude/skills/`. This repo holds the distributed copies. When a skill changes:

1. Update the copy here under `plugins/tableau-next-semantics/skills/`.
2. Bump `version` in `.claude-plugin/marketplace.json` and `plugins/tableau-next-semantics/.claude-plugin/plugin.json`.
3. Commit and push. Installers pick up the update through `/plugin`.

---

## Roadmap

- A Snowflake and dbt metadata extraction skill will join this plugin once it is validated against a live source.
- Skill families beyond Tableau Next will live in their own separate marketplace repos, so this one stays focused.

---

## About

Built by Cecilia Fryar, XeoMatrix. For team and partner use.
