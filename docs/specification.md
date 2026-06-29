# Architecture Model Standard — Specification v0.1.0

## 1. Overview

The Architecture Model Standard defines a universal, machine-readable format for capturing software system architecture. It serves as the authoritative structural spine that LLMs reference when generating, validating, or updating systems engineering documentation.

### Design Goals

1. **Machine-readable**: Parseable by any YAML library in any language
2. **Human-editable**: Concise enough to maintain by hand in a text editor
3. **Git-diffable**: Line-oriented format that produces meaningful diffs
4. **LLM-efficient**: Compact representations that fit within token budgets
5. **Tool-agnostic**: No dependency on specific modeling tools or frameworks
6. **Validation-first**: Every model instance can be validated against invariants

### Non-Goals

- Replacing UML/SysML formal notation (this is a data format, not a visual language)
- Runtime execution (this describes architecture, not behavior)
- Prescribing a specific architecture style

---

## 2. Model Structure

A model instance is a YAML document with three top-level sections:

```yaml
meta:        # Model metadata (version, project, timestamps)
entities:    # Seven typed entity collections
relationships:  # Typed connections between entities
```

### 2.1 Meta

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Semver (e.g., "0.1.0") |
| `project` | string | yes | Project identifier |
| `system` | string | no | System name (human-readable) |
| `generated_at` | datetime | yes | ISO 8601 timestamp |
| `source_artifacts` | string[] | no | Artifacts used to build this model |
| `manifest_hash` | string | no | SHA-256 prefix of source manifest |

---

## 3. Entity Types

Seven entity types represent the architectural building blocks:

### 3.1 Actors

External users or systems that interact with the modeled system.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "A-01", "external-ollama") |
| `name` | string | yes | Human-readable name |
| `type` | enum | yes | `human`, `external_service`, `internal_system` |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `description` | string | no | What this actor does |

### 3.2 Capabilities

High-level functional groupings (what the system CAN do).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "CAP-F1") |
| `name` | string | yes | Capability name |
| `f_block` | string | yes | Functional block ID (e.g., "F1") |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `description` | string | no | What this capability provides |

### 3.3 Behaviors

Observable system actions (what the system DOES). Maps to use cases.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "BEH-01", "UC-01") |
| `name` | string | yes | Behavior/use-case name |
| `actor` | string | no | Primary actor ID (comma-separated if multiple) |
| `trigger` | string | no | What initiates this behavior |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `tags` | string[] | no | F-block tags (e.g., ["F1", "F3"]) |
| `description` | string | no | What happens during this behavior |

### 3.4 Interfaces

System boundaries and communication contracts.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "IFC-01") |
| `name` | string | yes | Interface name |
| `protocol` | string | no | Communication protocol (REST, gRPC, SQL, etc.) |
| `provider` | string | no | Providing entity/block |
| `consumer` | string | no | Consuming entity/block |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `description` | string | no | Contract description |

### 3.5 Constraints

Quality attributes, NFRs, and design rules.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "CON-01") |
| `name` | string | yes | Constraint name |
| `type` | string | no | Category (performance, security, reliability, etc.) |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `description` | string | no | What this constraint requires |

### 3.6 Layers

Logical architecture layers (vertical slicing of the system).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "web-layer") |
| `name` | string | yes | Layer name |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `directories` | string[] | no | Source directories allocated to this layer |
| `description` | string | no | Layer responsibility |

### 3.7 Components

Implementation units (files, modules, packages) that realize capabilities.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., "COMP-ingest-onenote") |
| `name` | string | yes | Component name (usually filename) |
| `layer` | string | no | Layer this component belongs to |
| `f_block` | string | no | Functional block this component implements |
| `status` | Status | yes | ACTIVE, PLANNED, or DORMANT |
| `files` | string[] | no | Source file paths |
| `source_file` | string | no | Primary source file |
| `description` | string | no | What this component does |

---

## 4. Relationship Types

Eight relationship types connect entities:

| Type | Semantics | Typical From → To |
|------|-----------|-------------------|
| `realizes` | Implementation relationship | Component → Capability |
| `contains` | Composition/ownership | Capability → Behavior |
| `depends-on` | Runtime dependency | Component → Component, Layer → External |
| `exposes` | Service provision | Component → Interface |
| `consumes` | Service consumption | Component → Interface |
| `allocated-to` | Physical allocation | Component → Layer |
| `traces-to` | Traceability link | Behavior → Constraint |
| `constrained-by` | Quality constraint | Capability → Constraint |

### Relationship Schema

```yaml
- type: realizes        # One of the 8 types above
  from: COMP-xyz       # Source entity ID
  to: CAP-F1           # Target entity ID
  description: "..."   # Optional human description
```

### Cardinality Rules

- An entity may have 0..N relationships of any type
- `realizes` relationships from Components to Capabilities form the primary traceability chain
- Orphan components (no `realizes` relationship) produce INFO-level validation messages
- Dangling references (to non-existent entity IDs) produce WARNING-level messages

---

## 5. Status Markers

Every entity carries a `status` field:

| Status | Meaning | Validator Behavior |
|--------|---------|-------------------|
| `ACTIVE` | Implemented and operational | Fully validated |
| `PLANNED` | Designed but not yet implemented | Skipped by reality validators |
| `DORMANT` | Previously active, now disabled | Not flagged as orphan |

Status markers propagate to documentation artifacts via `[ACTIVE]`/`[PLANNED]`/`[DORMANT]` inline tags.

---

## 6. Validation Rules

The validator checks model invariants and produces a score (0-100):

### Scoring Algorithm

```
score = 100 - (errors * 10) - (warnings * 2) - (info * 0)
score = max(0, min(100, score))
```

### Invariant Checks

| Code | Severity | Rule |
|------|----------|------|
| `MISSING_ENTITY` | ERROR | Required entity field is empty |
| `DANGLING_REF` | WARNING | Relationship references non-existent entity |
| `ORPHAN_ENTITY` | INFO | Entity has no relationships (except DORMANT) |
| `DUPLICATE_ID` | ERROR | Two entities share the same ID |
| `INVALID_TYPE` | ERROR | Relationship type not in allowed set |

### Known External Convention

Entity IDs matching these patterns are exempt from dangling-ref checks:
- IDs ending in `-layer` (layer references)
- IDs starting with `external-` (external service references)
- Short layer slugs: `web`, `services`, `data`, `pipeline`, `scheduling`

---

## 7. YAML Format Conventions

### ID Conventions

- Actors: `A-NN` (numbered) or `external-{name}` (auto-discovered)
- Capabilities: `CAP-{fblock}` (e.g., `CAP-F1`)
- Behaviors: `BEH-NN` or `UC-NN` (use case IDs)
- Interfaces: `IFC-NN` or `intf-{name}` (slugified)
- Constraints: `CON-NN`
- Layers: `{name}-layer` (e.g., `web-layer`)
- Components: `COMP-{name}` or `{slugified-path}`

### File Organization

```yaml
# architecture-model.yaml
meta:
  schema_version: "0.1.0"
  project: my-project
  # ...

entities:
  actors:
    - id: A-01
      # ...
  capabilities:
    - id: CAP-F1
      # ...
  # ... (7 entity types in fixed order)

relationships:
  - type: realizes
    from: COMP-xyz
    to: CAP-F1
  # ...
```

### Versioning

Schema versions follow semver:
- **MAJOR**: Breaking changes to entity/relationship schema
- **MINOR**: New optional fields, new relationship types
- **PATCH**: Documentation fixes, validation rule adjustments

---

## 8. Tool Ecosystem

### Core Library (Python)

```bash
pip install architecture-model-standard
```

Commands:
- `architecture-model validate <model.yaml>` — Check invariants, report score
- `architecture-model extract <artifacts-dir>` — Build model from markdown artifacts
- `architecture-model slice <model.yaml> --fblock F3` — Extract focused subset
- `architecture-model context <model.yaml> --artifact icd` — Generate LLM context
- `architecture-model impact <model.yaml> CAP-F1` — Trace change impact
- `architecture-model diff <old.yaml> <new.yaml>` — Structural comparison
- `architecture-model stats <model.yaml>` — Entity/relationship counts
- `architecture-model query <model.yaml> "question"` — Structural queries

### Integration Points

1. **CI/CD**: Validate model on every commit, fail if score < threshold
2. **Artifact Generation**: Prepend model context to LLM prompts
3. **Change Impact**: Before modifying code, trace affected artifacts
4. **Documentation Sync**: Detect when model diverges from artifacts
