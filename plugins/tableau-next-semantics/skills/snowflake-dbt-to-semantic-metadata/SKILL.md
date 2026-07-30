---
name: snowflake-dbt-to-semantic-metadata
description: >-
  Extract existing semantic metadata (table/column descriptions, data types, primary/foreign keys,
  roles) from a Snowflake database or a dbt project, and normalize it into the metadata-spreadsheet
  shape consumed by the semantic-descriptions-from-spreadsheet and tableau-semantic-relationships
  skills. Use as the FRONT-END when migrating a customer's Snowflake/dbt semantic definitions into a
  Tableau Next / Data 360 semantic model. Templates — validate identifiers against the live source.
---

# Snowflake / dbt → Semantic Metadata (Extraction Front-End)

Produces the normalized inputs the downstream skills need:
- **fields**: Table, Field, Field Description, Example Value, Recommended Role
- **tables**: Table, table_description
- **relationships**: From Table, From Field, To Table, To Field, Relationship Type
(then feed to `semantic-descriptions-from-spreadsheet` for descriptions and
`tableau-semantic-relationships` for joins → deploy via `tableau-semantics-dx`).

## Step 0 — ask for the source and target first
- **Ask which source** and how you'll reach it — don't assume or guess connection details:
  - **Snowflake** → need the **database + schema**, and how the SQL runs (the user pastes query
    results back, or you have a connection/CLI to run them).
  - **dbt project** → need the path to **`target/manifest.json`** (and ideally `catalog.json`).
- If the user isn't sure what's available, ask what they have (a Snowflake login? a dbt repo?) and
  pick the matching path.
- Confirm the **target** Tableau Next model this feeds (workspace + semantic model name).
- **Echo back** the DB/schema or project path before running anything.

## Two-migration reminder
This is the **metadata** half. The **data** must already be (or be getting) into Data Cloud
(Snowflake connector / ingestion / zero-copy federation) as DMOs. Also: DMO field API names get
mangled (`SALES`→`Sales2`), so downstream **matches by LABEL**, not name — keep the source
column/table *names* as the labels here.

---

## Path A — Snowflake (INFORMATION_SCHEMA + SHOW)

### Columns, comments, types, role heuristic
```sql
SELECT
  c.table_name  AS "Table Name",
  c.column_name AS "Field Name",
  c.comment     AS "Field Description",
  c.data_type,
  CASE
    WHEN c.data_type IN ('NUMBER','DECIMAL','INT','INTEGER','BIGINT','SMALLINT','FLOAT','DOUBLE','REAL')
     AND UPPER(c.column_name) NOT LIKE '%\_ID'  ESCAPE '\'
     AND UPPER(c.column_name) NOT LIKE '%\_KEY' ESCAPE '\'
     AND UPPER(c.column_name) NOT LIKE '%CODE'
    THEN 'Measure' ELSE 'Dimension'
  END AS "Recommended Role"
FROM <DB>.INFORMATION_SCHEMA.COLUMNS c
WHERE c.table_schema = '<SCHEMA>'
ORDER BY c.table_name, c.ordinal_position;
```

### Table descriptions
```sql
SELECT table_name AS "Table Name", comment AS "table_description"
FROM <DB>.INFORMATION_SCHEMA.TABLES
WHERE table_schema = '<SCHEMA>' AND table_type = 'BASE TABLE';
```

### Relationships (declared foreign keys)
Snowflake FKs are informational (not enforced) but declarable & queryable. `SHOW` gives the cleanest
from/to column mapping:
```sql
SHOW IMPORTED KEYS IN SCHEMA <DB>.<SCHEMA>;
SELECT "fk_table_name"  AS "From Table", "fk_column_name" AS "From Field",
       "pk_table_name"  AS "To Table",   "pk_column_name" AS "To Field",
       'Many-to-one'    AS "Relationship Type"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```
Primary keys (useful to know which "to" side is unique — matters for M:1 vs M:M downstream):
```sql
SHOW PRIMARY KEYS IN SCHEMA <DB>.<SCHEMA>;
```
If FKs aren't declared, derive candidates by naming convention (a `<X>_ID` column matching another
table's PK) and confirm with the customer.

### Example values (optional — used to infer format like $ / rate / date)
Not in metadata; sample one non-null per column. Scriptable: for each column emit
`SELECT '<tbl>','<col>', TO_VARCHAR(MAX("<col>")) FROM <DB>.<SCHEMA>."<tbl>" WHERE "<col>" IS NOT NULL LIMIT 1;`
and union the results. Skip if not worth the runtime.

---

## Path B — dbt (parse target/manifest.json — richest source)
```python
import json
m = json.load(open("target/manifest.json", encoding="utf-8"))
fields, tables = [], []
by_uid = {}
for uid, n in m["nodes"].items():
    if n.get("resource_type") != "model": continue
    t = n["name"]; by_uid[uid] = t
    tables.append({"Table Name": t, "table_description": n.get("description","")})
    for cname, col in n.get("columns", {}).items():
        fields.append({"Table Name": t, "Field Name": cname,
                       "Field Description": col.get("description",""),
                       "Recommended Role": ""})   # fill via type heuristic or catalog.json

# relationships: from dbt 'relationships' tests
rels = []
for uid, n in m["nodes"].items():
    if n.get("resource_type") != "test": continue
    tm = n.get("test_metadata") or {}
    if tm.get("name") != "relationships": continue
    kw = tm.get("kwargs", {})
    child = by_uid.get((n.get("depends_on",{}).get("nodes") or [None])[0], "")
    parent = str(kw.get("to","")).replace("ref(","").replace(")","").strip("'\" ")
    rels.append({"From Table": child, "From Field": kw.get("column_name") or kw.get("field"),
                 "To Table": parent, "To Field": kw.get("field"),
                 "Relationship Type": "Many-to-one"})
```
Newer dbt also carries model-level `constraints` (primary_key / foreign_key) in the manifest and
column data types in `target/catalog.json` — prefer those when present (cleaner than tests).

---

## Normalize + hand off
Write one working JSON `{ "fields":[...], "tables":[...], "relationships":[...], "synonyms":[] }`
(the exact shape the downstream skills read), or an .xlsx with those tabs. Then:
1. `semantic-descriptions-from-spreadsheet` → agent-optimized descriptions (≤255 chars) → deploy.
2. `tableau-semantic-relationships` → build joins (remember: M:M unless DMO PKs are recognized;
   keep the graph acyclic).

## What ports cleanly vs needs reshaping
- **Clean:** descriptions, data types, roles, FK-based relationships.
- **Reshaping:** any **metrics/calcs** from a source semantic layer (dbt Semantic Layer/MetricFlow,
  Cube, AtScale) — the expression *language* must be translated to Tableau semantic syntax; not 1:1.
- **Out of scope here:** the data movement itself, RLS/governance, hierarchies.

## Caveats
Templates, not run against a live source — verify DB/schema identifiers, quoting/case, and
permissions. Snowflake SHOW output column names are lowercase and quoted. Role heuristic is a
starting point (numeric IDs/codes are dimensions). Confirm undeclared FKs with the customer.
