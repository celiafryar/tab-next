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

### 1. Many-to-One requires `primaryNameField` on the parent object (THE lever)
To make a `ManyToOne` join into a table work, set that (parent, "one"-side) object's **object-level
`primaryNameField`** in `dataObjects.json` to its business key, e.g.
`Department.primaryNameField = "department_id2"`. Then joins into that table deploy as ManyToOne and
show as Many-to-One in the UI. **This is writable pro-code and needs NO Data Stream reload.**
CONFIRMED on the HR test model: with `primaryNameField` set on all four tables, the full
child→parent chain deployed as ManyToOne.

```jsonc
// object level in dataObjects.json (sibling of apiName/label, not inside a field)
{ "apiName":"Department1", "label":"Department", "primaryNameField":"department_id2", ... }
```

What does NOT work (don't waste time here):
- The **field-level `isPrimaryKey` flag is read-only** — setting it `true` deploys without error but
  reverts to `false` on retrieve and does nothing. Ignore it.
- Designating a PK in the **model canvas** doesn't reliably propagate either (it writes the same
  `primaryNameField` — so just set that property directly in pro-code).
- Without `primaryNameField`, a `ManyToOne` deploy fails **500 "The API Name has no mapped semantic
  definition ID"** and the GUI offers only Many-to-Many. (That — not any data problem — is what
  forced M:M on construction-sdx: it simply never had `primaryNameField` set.)

Background: File-Upload DMOs default their identity to a generated `uuid_temp` + `KQ_uuid_temp` key
qualifier when no business key is designated at ingest; `primaryNameField` gives the semantic layer
the recognized key it needs for M:1 regardless.

### Primary Name Field vs Primary Key (two different things; do not confuse them)
The Tableau Next model UI shows BOTH on an object's hover card, and they are separate:
- **Primary Name Field** is what `primaryNameField` sets (a business field like `organization_id`).
  It lives in the semantic layer, is writable pro-code, and is the property that unlocks
  Many-to-One. This is the one that matters for relationships.
- **Primary Key** is the object's true identity: a DLO/DMO property set at **Data Stream ingest**
  and immutable afterward. For File uploads with no business key chosen at ingest, Data Cloud
  generates `uuid_temp` (plus `KQ_uuid_temp`) and uses that as the Primary Key. The semantic model
  cannot change it (`isPrimaryKey` is read-only).
- It is normal, and fine, to see **Primary Key = `uuid_temp`** while **Primary Name Field = the
  business key**. Joins and Many-to-One work off the Primary Name Field, so queries and the agent
  are correct. Safe to leave for demos. (CONFIRMED on HR Test: Organization DLO showed Primary Key
  `uuid_temp`, Primary Name Field `organization_id`.)
- To make the **Primary Key** itself the business key (matters for correct upserts and identity when
  data refreshes or goes to production, not for a static demo), fix it upstream: re-create the data
  stream with the business field as the primary key, or map the DLO to a DMO whose primary key is
  the business field. Then rebuild the model layer (re-add objects, retrieve, re-apply descriptions,
  hides, relationships).

Caveats:
- `primaryNameField` is also the object's display/name field in Salesforce terms. Pointing it at an
  ID can make that ID the record's shown "name" — usually fine on keyed lookup tables, but verify
  display on real models (or point it at a human-readable name field if that reads better and still
  satisfies the join).
- **`ManyToMany` always works** and gives correct aggregation; it's the safe fallback if you can't
  or don't want to set `primaryNameField`.

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
