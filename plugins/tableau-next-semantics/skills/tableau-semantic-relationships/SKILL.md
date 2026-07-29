---
name: tableau-semantic-relationships
description: >-
  Define table relationships (joins + cardinality) in a Tableau Next semantic model
  programmatically via relationships.json — outside the model-canvas GUI. Use when building or
  editing relationships from a data model / cardinality spec (e.g., a Solution Design Document's
  "Relationship and Cardinality Rules"), wiring up a retrieved semantic model's joins, or
  debugging relationship deploy/validation errors (cyclic relationship, cardinality, "no mapped
  semantic definition ID"). Companion to tableau-semantics-dx (retrieve/validate/deploy loop) and
  semantic-descriptions-from-spreadsheet.
---

# Building Tableau Next Relationships in Pro-Code

How to define semantic-model relationships in `relationships.json` and deploy them, without the
GUI. Proven on the Alderstone "All Tables" model (25 tables, 21 relationships; a few tables
standalone). Use the
`tableau-semantics-dx` skill for org auth, retrieve, validate, and deploy mechanics.

## relationships.json item shape
```json
{
  "apiName": "Child_Parent",
  "cardinality": "ManyToMany",
  "criteria": [{
    "joinOperator": "Equals",
    "leftFieldType": "TableField",  "leftSemanticFieldApiName": "<field apiName on left obj>",
    "rightFieldType": "TableField", "rightSemanticFieldApiName": "<field apiName on right obj>"
  }],
  "isEnabled": true, "isQueryable": "Queryable", "joinType": "Auto",
  "label": "Child : Parent",
  "leftSemanticDefinitionApiName": "<object apiName>",
  "rightSemanticDefinitionApiName": "<object apiName>"
}
```
- `leftSemanticFieldApiName` must be a field on `leftSemanticDefinitionApiName` (same for right).
- Omit server-populated fields (`id`, `createdBy`, `createdDate`, `lastModified*`) when creating.
- `joinType: "Auto"` is the norm.

## Inputs you need
1. **Cardinality rules** — which table relates to which, and the direction (a From→To / "one X has
   many Y" table, e.g. a Solution Design Doc §"Relationship and Cardinality Rules").
2. **Join keys** — the field on each side (often in a metadata "Relationships" tab, or infer the
   FK↔PK ID pair).
3. **Real API names** — read them from the model's `dataObjects.json`. Field API names carry
   numeric suffixes (`Project_ID`, `Region9`, `State8`, `Employee_ID2`) and object labels may have
   a `.csv` suffix — **match everything by LABEL, then resolve to apiName.**

## Process
0. **Ask first — get the spec and the target.** If the user hasn't provided the relationship /
   cardinality rules, ask for them: a Solution Design Doc section, a metadata "Relationships" tab,
   an ERD, or simply "which tables join to which, in what direction." **Never invent joins.** Also
   confirm the **target model** (workspace + semantic model name). If there's no written spec, offer
   to derive candidates from ID-naming conventions (a `<X>_ID` column matching another table's key)
   or an existing Relationships tab, then confirm each with the user before building.
1. Retrieve the model. Read `dataObjects.json` → build `{tableLabel: {objApiName, {fieldLabel: fieldApiName}}}`.
2. **Dry-run verify** every intended relationship's join keys exist in the model (report gaps —
   e.g., a doc may reference a Region ID that Projects doesn't have).
3. Build `relationships.json` items (resolve apiNames from step 1). `apiName` = a unique valid
   identifier, e.g. `clean(childLabel)_clean(parentLabel)`.
4. **Acyclic check locally** before deploy (see constraint 2).
5. Validate → deploy → retrieve → commit (via tableau-semantics-dx).

## THE THREE CONSTRAINTS (learned the hard way)

### 1. Many-to-One requires a UNIQUE "one" side — which comes from the load-time Primary Key
**Cardinality is driven by the DLO's Primary Key Field, assigned when the table is loaded through a
Data Stream.** The platform will only accept `ManyToOne` (and the UI cardinality dialogue will only
offer 1:M) when the column on the "one" side is already known to be unique, and the load-time primary
key is what makes it known.

**CONFIRMED 2026-07-29 on the AAA sales model (`sales-opportunity-sdx`):** 9 relationships across 10
objects all deployed and round-tripped as `ManyToOne` with **`primaryNameField` absent on every
object**, purely because the business key was designated as the primary key during CSV load. Nothing
in the semantic layer was needed.

**So the first question is always: were the primary keys assigned at load?**
- Yes → just write `cardinality: "ManyToOne"`. Nothing else required.
- No → Data Cloud generated a `uuid_temp` (+ `KQ_uuid_temp`) row-id and made *that* the Primary Key
  Field. It cannot be reassigned from the semantic model. Either re-ingest with the business key as
  PK / map the DLO to a DMO keyed on it, **or** use the `primaryNameField` fallback below.

**Read the key state from the files:** exactly one `KQ_<businessKey>` per object and no `uuid_temp`
anywhere = keys assigned at load. `uuid_temp` + `KQ_uuid_temp` = they were not. That fingerprint is
the ONLY trace the model folder carries — see constraint 1a.

#### The `primaryNameField` fallback (for models with no real key)
Setting the parent object's **object-level `primaryNameField`** to its business key also satisfies the
uniqueness requirement, writable pro-code with no Data Stream reload:
```jsonc
// object level in dataObjects.json (sibling of apiName/label, not inside a field)
{ "apiName":"Department1", "label":"Department", "primaryNameField":"department_id2", ... }
```
CONFIRMED on HR Test, where all four tables had `uuid_temp` primary keys and this was the only way to
get M:1. **Treat it as a workaround, not the mechanism.** It was mis-recorded as "THE lever" because
HR Test was the first model where M:1 worked, and nobody had yet built a model with proper keys to
compare against. Cost: `primaryNameField` is also the record's display name, so pointing it at an ID
makes the ID the record's shown name.

**When the keys ARE set properly, use `primaryNameField` for its real purpose** — the readable name
(`AccountName1`, `ProductName`, `FullName`, `TerritoryName`) so records name themselves legibly to the
agent. CONFIRMED safe: pointing it at a non-key name field disturbed none of the 9 existing M:1 joins.

What does NOT work (don't waste time here):
- The **field-level `isPrimaryKey` flag is read-only AND worthless as evidence** — it deploys without
  error but does nothing, and it reads `false` even on a field that genuinely IS the DLO primary key.
  Never conclude "this model has no primary keys" from it.
- Designating a PK in the **model canvas** doesn't reliably propagate (it writes `primaryNameField`).
- With neither a load-time key nor `primaryNameField`, a `ManyToOne` deploy fails **500 "The API Name
  has no mapped semantic definition ID"** and the GUI offers only Many-to-Many. That is what forced
  M:M on construction-sdx — no key at ingest and no `primaryNameField`.

### 1a. The Primary Key Field is INVISIBLE to pro-code
The object hover card shows two rows, **Primary Key Field** and **Primary Name Field**, and they are
different properties. Only the second one exists in the retrieved JSON:

| UI row | JSON | Writable? | Role |
|---|---|---|---|
| **Primary Key Field** | *nowhere in any of the 14 files* | No — set at Data Stream ingest, immutable | The uniqueness guarantee. Drives cardinality. |
| **Primary Name Field** | `primaryNameField` on the object | Yes | Record display name. |

CONFIRMED 2026-07-29: Account.csv showed Primary Key Field `AccountId` with the key icon in the UI
while `AccountId1` retrieved as `isPrimaryKey: false`, from a retrieve taken *after* the key was set.
So you cannot verify or set primary keys from pro-code in either direction — ask the user to hover the
object, or infer from the `KQ_` fingerprint. It is normal and fine to see Primary Key Field populated
while Primary Name Field reads `None`.

#### Fixing a model that was loaded WITHOUT primary keys
This is the situation `primaryNameField` exists to paper over, and the paper-over is fine for a demo:
M:1 works, aggregation is correct, the agent is correct. Leave it.

It is NOT fine when the data refreshes or goes to production, because the real Primary Key Field is
still the generated `uuid_temp` row-id, so upserts and record identity are wrong. That can only be
fixed upstream: re-create the data stream with the business field as the primary key, or map the DLO
to a DMO whose primary key is the business field. **Then the model layer must be rebuilt** — re-add
objects, retrieve, re-apply descriptions, hides and relationships — because new DLOs mean new
apiNames. Budget for that before promising a production path.

Best practice going forward: **assign the primary key at load time on every table.** It costs nothing
at upload, and it is the difference between `cardinality: "ManyToOne"` just working and a rebuild.

Other notes:
- **`ManyToMany` always works** and gives correct aggregation; it's the safe fallback when you have
  neither a load-time key nor `primaryNameField`. M:1 is a performance optimization that additionally
  requires a recognized unique key — it is not required for correct numbers.
- All relationships are Many-to-One **in intent** from the FK-holder to the PK-holder, even when they
  have to be deployed as M:M.

### 2. The relationship graph must be ACYCLIC
Validate fails with **`CYCLIC_RELATIONSHIP_ERROR`**, listing the objects in the loop. Causes & fixes:
- **Two fact tables sharing 2+ common (conformed) dimensions is a cycle.** Fix: make one fact the
  **dimension hub** (it owns Clients/Offices/Types/…); the other connects via a single
  **conversion/leaf link** and slices on its own denormalized inline columns. (Alderstone: Projects
  is the hub; Opportunities links only via `Projects→Opportunities` and uses inline Client Name /
  Project Type / Nearest Office.)
- **Redundant second paths.** Don't add `Tasks→Projects` when `Tasks→Milestones→Projects` already
  connects them — the extra edge closes a loop.
- Removing a single offending edge (often the optional/conversion one) breaks the cycle.

### 3. Two gates, different checks
**Validate** catches cycles and structural issues. **Deploy** catches cardinality / key-mapping.
A set can validate clean and still fail deploy on cardinality — always test both.

### 4. On an EXISTING relationship you can change cardinality, NOT the left/child definition
Deploy will update an existing relationship's `cardinality` (e.g., M:M → M:1) fine. But changing its
`leftSemanticDefinitionApiName` (the child/"many" side) fails **400: "Updating the left semantic
definition is not allowed in a semantic relationship."** (CONFIRMED on construction-sdx.) The batch
is atomic, so one illegal left-change fails the whole deploy. **To re-orient an existing
relationship (swap child/parent), DELETE it and CREATE a new one with a new apiName** — don't edit
the left side in place. This matters when a relationship was first made in the GUI with the wrong
side as the child (its orientation is then locked for in-place edits).

## When stuck on structure/cardinality: GUI-seed
Create ONE relationship in the model canvas, save, retrieve, and read `relationships.json`. That
reveals the exact structure the server produces AND the cardinality the platform will accept for
your keys (e.g., if it forces Many-to-Many, that's your answer). Reuse that item verbatim (keep its
`id`) so you don't duplicate the pair, and add the rest in the same shape.

## Modeling judgment notes
- All relationships are Many-to-One from the FK-holder (child) to the PK-holder (parent) in intent,
  even when deployed as M:M.
- A join can use any matching fields, not just IDs — e.g. Alderstone joined Offices→Regions on
  `State → Primary State` when neither had a Region ID (region ≡ state 1:1).
- Multiple relationships between the same two objects (role-playing, e.g. PM/Superintendent/Exec →
  Employees) risk ambiguous-path errors — prefer one primary role unless validated.
- Tables with no spec'd relationship stay standalone (fine); log them so it's not mistaken for a miss.

## Reference implementation
Alderstone "All Tables": `C:\Users\celia\source\repos\construction-sdx` (GitHub
`celiafryar/construction-sdx`), built from `Alderstone_Builders_Solution_Design_Document_v2.docx`
§5.1/§6. See the `alderstone-construction-model` memory.
