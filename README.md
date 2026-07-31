# Tab Next

A Claude Code **plugin marketplace** of pro-code skills for building **Tableau Next / Salesforce Data 360 semantic models as code**. Describe every table and field, define relationships and cardinality, assign geographic roles, and deploy, all version-controlled in Git and tuned for **Tableau Pulse** and **Agentforce**.

> A marketplace is simply a Git repo that Claude Code can install plugins from. You add this repo once, install the plugin below, and its skills load automatically. They trigger on their own when you work on a semantic model, or you can call one by name (for example, `/tableau-semantics-dx`).

---

## What you get

Installing the **`tableau-next-semantics`** plugin adds six field-tested skills.

| Skill | The value it delivers | It kicks in when you |
|---|---|---|
| **tableau-semantics-dx** | The core pro-code loop: retrieve a model as JSON, edit, validate, deploy. Carries the platform know-how that otherwise costs a day of trial and error, from the 255-character description cap to what actually controls join cardinality. | edit a retrieved `Semantic Models/...` folder, author calculated fields or descriptions, deploy, or debug a deploy error. |
| **semantic-descriptions-from-spreadsheet** | Turns a metadata workbook into agent-ready descriptions for hundreds of fields at once and writes them into the model. The highest-leverage thing you can do for Tableau Agent and Pulse answer quality, and unbearable by hand. | have a data dictionary and want conversational analytics to map questions to the right fields. |
| **tableau-semantic-relationships** | Authors joins and cardinality directly in `relationships.json`, outside the model canvas. Knows why Many-to-One gets refused, and checks the graph is acyclic before you spend a deploy finding out. | build or fix relationships from a cardinality spec, or hit `CYCLIC_RELATIONSHIP_ERROR` or a cardinality rejection. |
| **tableau-semantic-geo-roles** | Assigns geographic roles so place-name fields map and the agent can answer geography questions. Gets the two-property mechanism right, and knows which look-geographic-but-aren't fields to leave alone. | have city, state, country or coordinate columns, or maps and geography questions are not working. |
| **tableau-business-preferences** | Authors and tests the instruction file that teaches the agent business language, intent and safe defaults. Carries what live testing proved about which instructions the agent actually obeys, which is not what the documentation implies. | the agent misreads a word, returns a right number that answers the wrong question, or ignores an instruction. |
| **snowflake-dbt-to-semantic-metadata** | The front end for migrations: pulls existing descriptions, types and keys out of Snowflake or a dbt project and normalizes them into the workbook the other skills consume. Stops you retyping metadata the customer already wrote. | migrate an existing Snowflake or dbt semantic layer into Tableau Next. |

**They chain.** Extract with the Snowflake/dbt skill, or start from a metadata workbook. Describe and relate the model. Assign geographic roles. Deploy and commit with the core skill. Then teach the agent how the business speaks with Business Preferences, and test it against a precomputed answer key. Each step hands the next a known shape.

> The Snowflake/dbt skill ships as **templates**. Its queries and identifiers must be validated against the live source before you trust the output, and the skill says so up front.

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

1. **Retrieve** the target model in VS Code: right-click the `Semantic Models` folder, then **Tableau Semantic: Retrieve Model to Folder**. This writes a folder of JSON files. Commit it as your baseline.
2. **Provide the input** the skill asks for: a metadata workbook for descriptions, a cardinality spec for relationships. Each skill prompts and confirms what it found before changing anything.
3. **Let the skill edit the JSON** (`dataObjects.json`, `relationships.json`, `calculatedDimensions.json`, and so on), resolving your model by field and table labels.
4. **Validate and deploy** from the extension: right-click `model.json`, then **Validate Model**, then **Deploy Model**.
5. **Retrieve again, then commit.** The retrieve is what proves the change landed and captures the IDs the server assigns. Commit only verified states.

A blank intake template for the description workflow (tables, fields, roles, primary keys, relationships, business synonyms) can be produced by the `semantic-descriptions-from-spreadsheet` skill on request.

---

## Capabilities and hard-won rules

The skills already encode these. They are worth knowing anyway, because most are not documented anywhere else.

- **Match by label, not API name.** Data Cloud makes field API names globally unique per org, so `Sales` becomes `Sales2` and `Account.csv` becomes `Account_csv1`. Resolve by label, then use the real API name.
- **Strip the `.csv` suffix from object labels.** File-upload tables arrive labelled with the filename, and it leaks into the object list, agent answers and any generated documentation. It cannot be fixed at ingest, only here.
- **Descriptions cap at 255 characters**, field and table alike. Validate passes even when one is too long; only Deploy catches it. Enforce the cap when generating.
- **Many-to-One comes from the primary key you assign at Data Stream load**, not from anything in the semantic layer. Assign it while uploading and `cardinality: "ManyToOne"` simply works. Skip it and Data Cloud generates a `uuid_temp` row ID that cannot be reassigned afterward. `primaryNameField` is the *fallback* for models loaded without a key; otherwise leave it for its real job, the record's display name.
- **`isPrimaryKey` lies.** It is read-only, and it reads `false` even on a field that genuinely is the primary key. The Primary Key Field appears nowhere in the retrieved JSON at all. Never conclude a model has no keys from that flag.
- **The relationship graph must be acyclic.** Two fact tables sharing several dimensions is a cycle; make one fact the hub. You can change an existing relationship's cardinality but not its left (child) side, so re-orienting one means delete and recreate.
- **Hide system and lineage fields** with `isVisible: false`: `cdp_sys_*`, `KQ_*`, `Data_Source*`, `Internal_Organization*`, `uuid_temp*`. Five or six per file-upload table, and they otherwise clutter every field list the agent reads.
- **A geographic role is two properties**, not one. `dataType` must become `"Geo"` *and* `semanticDataType` must hold the role, while `storageDataType` stays as it was. Setting only the second is the usual mistake.
- **Calculated dimensions and measures have different shapes.** Dimensions are leaner and use `level: "Row"`; measures carry the aggregation keys. `dataType: "Boolean"` works, and a Boolean field can serve directly as an `IF` condition.
- **A calculated field touching one table appears at the end of that table's column list.** Only ones spanning multiple tables show under "Calculated Fields", which is easily ten minutes of hunting the first time.
- **A 401 "Session expired" from the extension is not dead auth.** The CLI's refresh token is almost always still valid: run any `sf` command to refresh, then retry.
- **Validate can report "0 validation errors" directly above real errors.** The top-level array is empty while the actual problems sit nested under `subResources`. If there is a warning triangle, read the JSON.
- **Metrics can build on your calculated measures** via `measurementReference.calculatedFieldApiName`, or point straight at a raw column via `tableFieldReference`. Polarity lives at `insightsSettings.sentiment`, and there is no display-format property at all.
- **A metric's API name is minted from its label at creation and never updates.** Rename a metric and the API name keeps the old word forever, so one real model ended up with `Revenue_mtc` displaying "Net Revenue". To rename meaningfully, delete and recreate. Metrics also have no visibility flag, so deletion is the only way to remove one.
- **A metric's aggregation must match whether its calculation aggregates itself,** or the metric silently shows nothing. A formula wrapping its own `SUM` needs the metric set to user aggregation; a bare row-level formula needs the metric set to `Sum`. Get it backwards and the tile renders a dash and "couldn't load the metric comparison", while both objects validate individually and the model reports itself valid. Worse, the calculation still works correctly on a worksheet, because only the metric overrides it, so "the calc is fine" doesn't clear the calc.
- **A metric cannot slice below its measure's grain.** An opportunity-level measure broken down by product counts each deal once per product family it contains. One real model returned $1.06B against a true $393.87M and got the ranking wrong. The fix is a second measure at the finest grain. The self-check worth teaching the agent: a breakdown must add up to the same total as the whole.
- **Deploying cleanly is not evidence that a formula evaluates.** Syntax can parse, validate, and deploy and still return nothing useful. Put the measure on a worksheet and check it against a number you computed independently before recording anything as confirmed.
- **The "lower is better" sentiment enum is `SentimentTypeUpIsBad`,** not the `DownIsGood` you would guess. A wrong enum fails the entire atomic deploy. Raw measure fields accept sentiment too; the key is simply absent until set, which is a good general reminder that an absent key here does not mean an unsupported one.
- **"Error when loading invalid metric" usually means a stale dashboard, not a broken metric.** A metric created after a dashboard exists fails only in that dashboard, while validating clean and rendering fine in a new one. Hard refresh, re-add the widget, or use a new dashboard.
- **You can read the deployed model without the extension.** `sf api request rest "/services/data/v66.0/ssot/semantic/models/<apiName>"` returns the whole thing including the live Business Preferences text, and a `/validate` endpoint answers whether the server considers the model valid. Invaluable for telling a real metadata problem apart from a client-side one.
- **A geo-roled field cannot be a metric dimension.** Assigning a map role changes `dataType` to `Geo`, and metrics accept only Text, Number, Boolean, Email, PhoneNumber or Url. Governed metrics therefore break down by region and territory; direct questions about state still work fine.
- **Never allow a metric dimension reached through a one-to-many hop.** It multiplies the measure. A contact attribute on an opportunity-grain metric can inflate it by nearly 2x.
- **Business Preferences govern method, not prose.** Which field, filter, population, scope and sort are obeyed reliably. Instructions about the wording of the narrative are largely ignored, because the platform owns the response structure.
- **The narrative is the summary; the Sources panel is the receipt.** Sources carries Fields Used and Filters Applied and is the only precise part of an answer. Teach every user to open it.
- **Never prohibit without substituting.** "Do not call it revenue" fails, because the agent still has to answer something. Say what to use instead.
- **Duplicate field labels cause silent wrong-field selection.** One real model had 19 of 109 labels appearing on more than one table, and Fields Used names a field without its table. No preference can disambiguate what the agent cannot distinguish.

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
    tableau-next-semantics/          # one plugin, six skills
      .claude-plugin/
        plugin.json                  # the plugin manifest
      skills/
        tableau-semantics-dx/
        semantic-descriptions-from-spreadsheet/
        tableau-semantic-relationships/
        tableau-semantic-geo-roles/
        tableau-business-preferences/
        snowflake-dbt-to-semantic-metadata/
  README.md
```

The `plugins/` layout leaves room to add more Tableau Next plugins to this same marketplace later.

---

## Maintaining this marketplace

Each skill's source of truth lives in `~/.claude/skills/`. This repo holds the distributed copies. When a skill changes:

1. Update the copy here under `plugins/tableau-next-semantics/skills/`.
2. Bump `version` in `.claude-plugin/marketplace.json` and `plugins/tableau-next-semantics/.claude-plugin/plugin.json`.
3. Commit and push. Installers pick up the update through `/plugin`.

**Keep the claims true.** These skills are valuable because what they assert has actually been verified. When something turns out to be wrong, correct it everywhere rather than bolting on a caveat, and give any known-bug note an explicit re-test date so it gets deleted once the platform fixes it. A stale warning misleads as much as a wrong rule.

---

## Roadmap

- Validate the Snowflake and dbt extraction skill against a live source and promote it from templates to confirmed.
- Metrics authoring at scale. The `metrics.json` item shape is now confirmed by a live deploy and documented in `tableau-semantics-dx`.
- A controlled test of whether large Business Preferences files genuinely degrade latency, or whether the real variable is contradictory rules. The 30,000 character cap is far above any file we have built.
- Skill families beyond Tableau Next will live in their own separate marketplace repos, so this one stays focused.

---

## About

Built by Cecilia Fryar, XeoMatrix. For team and partner use.
