from __future__ import annotations


def generate_readme() -> str:
    return _README


def generate_schema_reference() -> str:
    return _SCHEMA


def generate_api_reference() -> str:
    return _API


def generate_custom_instructions(repo_name: str, stats: dict) -> str:
    components = stats.get("components", "?")
    behaviors = stats.get("behaviors", "?")
    relationships = stats.get("relationships", "?")
    file_count = stats.get("file_count", "?")
    
    return f"""# Custom Instructions for Claude

Paste the following into your Claude Project's "Set custom instructions" field:

---

You have access to architecture model artifacts for the **{repo_name}** repository. These artifacts compress the full codebase into structured models that let you reason about system architecture without reading source code.

## Repository stats

- Components: {components}
- Behaviors: {behaviors}
- Relationships: {relationships}
- Export files: {file_count}

## How to navigate the artifacts

1. **Start with CONTEXT.md** — gives purpose, structure, decisions, current state
2. **Read the model YAML** — components, relationships, and behaviors
3. **Use behavior specs** — for cross-component flow understanding (if present)
4. **Reference manifests** — for ground-truth function signatures and call edges
5. **Check SCHEMA.md** — for valid entity types and relationship types
6. **Check API.md** — for tool capabilities and token-saving patterns

## File naming convention

Files are named `{{prefix}}--{{category}}.{{ext}}` where prefix identifies the repository.

## Key concepts

- **Token arbitrage**: Compress full repo into ~430 tokens of model context
- **Behavior flows**: Cross-component call chains traced from AST data
- **Sub-models**: Scoped architecture models for one component or behavior
- **Manifests**: AST-scanned code facts (functions, imports, calls)

## When asked about architecture or planning

- Reference the model YAML for component boundaries
- Reference behavior specs for understanding cross-cutting flows
- Use manifests to ground claims in actual code structure
- Use SCHEMA.md to validate any model changes proposed
- Use API.md token-saving strategies when suggesting efficient approaches

## When asked about next steps

Reference the "In Progress" section of the CONTEXT.md for current work and approved plans.
"""


_README = r"""# Architecture Model Export — Instructions for AI

## What This Is

This archive contains architecture documentation for a repository, exported as flat files suitable for upload to Claude Projects, ChatGPT, or similar AI assistants.

## How to Use This

### Quick Context Load

Read in this order:
1. `*--CONTEXT.md` — Project purpose, structure, decisions, current state
2. `*--model.yaml` — The architecture model (components, relationships, behaviors)
3. `*--docs.md` — Generated documentation (component specs, ICD, health, etc.)

### Understanding Components

The model YAML defines components (COMP-1, COMP-2, etc.) with:
- `name` — human-readable component name
- `status` — ACTIVE, PLANNED, or DEPRECATED
- `files` — source files belonging to this component

Relationships show how components interact:
- `depends_on` — compile/import dependency
- `realizes` — component implements a capability/behavior
- `uses` — runtime call dependency

### Understanding Behavior Flows

If behavior specs are present (`*--behavior-specs.md`):
- Each behavior spec shows which components participate
- Mermaid sequence diagrams show the call chain
- Data flow tables show inputs/outputs per step
- Error paths show what can throw

### Sub-Models (Drill Down)

`*--submodels.yaml` contains sub-models separated by `---`:
- F-block decompositions (F1, F2, etc.)
- Named sub-systems (core, cli, config, etc.)

`*--behavior-submodels.yaml` contains per-behavior sub-models.
`*--component-models.yaml` contains per-component sub-models.

### Manifests (Code Reality)

`*--manifests.md` contains markdown summaries of AST-scanned code facts:
- Every module, its functions, imports
- Use these to ground discussions in actual code structure

### File Separator Convention

Within concatenated files, individual source files are delimited by:
```
<!-- FILE: original/path/here -->
```
and separated by `---` horizontal rules.

## Schema Reference

See `SCHEMA.md` for the full entity type and relationship type reference.

## Token Budget Tips

See `API.md` for token-saving strategies, tool signatures, and budget guidelines.
"""


_SCHEMA = r"""# Architecture Model Schema Reference (v1.3)

## Entity Types

### Component
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., COMP-1) |
| name | str | yes | Human-readable name |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| description | str | no | What this component does |
| tags | list[str] | no | Classification tags |
| source_file | str | no | Primary source file |
| confidence | float | no | 0.0-1.0, extraction certainty |
| files | list[str] | no | Source files in this component |

### Behavior
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., BEH-42) |
| name | str | yes | Function/flow name |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| trigger | str | no | What initiates this (e.g., "POST /users") |
| actor | str | no | Who/what triggers it |
| steps | list[str] | no | Ordered function calls in the flow |
| preconditions | list[str] | no | Required state before execution |
| postconditions | list[str] | no | State after successful execution |
| frequency | str | no | How often triggered |
| priority | enum | no | HIGH, MEDIUM, LOW |
| pattern | enum | no | SEQUENTIAL, PARALLEL, SAGA, EVENT_DRIVEN |
| source_file | str | no | File containing the entry point |

### Capability
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., CAP-F1) |
| name | str | yes | What the system can do |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |

### Interface
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., IF-1) |
| name | str | yes | Interface name |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| provider | str | no | Component ID that exposes this |
| consumer | str | no | Component ID that consumes this |
| protocol | str | no | HTTP, gRPC, internal, etc. |

### Layer
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., L-1) |
| name | str | yes | Layer name |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| order | int | no | Stack position (0 = bottom) |

### Constraint
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., CON-1) |
| name | str | yes | Rule name |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| rule | str | no | The constraint rule |
| rationale | str | no | Why this constraint exists |

### Actor
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Unique ID (e.g., ACT-1) |
| name | str | yes | Actor name |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| type | str | no | human, system, external |

## Relationship Types

| Type | Meaning | Example |
|------|---------|---------|
| depends_on | Compile/import dependency | COMP-1 depends_on COMP-2 |
| realizes | Implements a capability/behavior | COMP-1 realizes CAP-F1 |
| uses | Runtime call dependency | COMP-1 uses COMP-3 |
| contains | Parent-child containment | L-1 contains COMP-1 |
| triggers | Initiates a behavior | ACT-1 triggers BEH-1 |
| implements | Implements an interface | COMP-1 implements IF-1 |
| exposes | Provides an interface | COMP-1 exposes IF-2 |
| constrains | Applies a constraint | CON-1 constrains COMP-1 |

## Validation Scoring (0-100)

| Check | Weight | What it validates |
|-------|--------|-------------------|
| ID uniqueness | Critical | No duplicate entity IDs |
| Referential integrity | Critical | All relationship endpoints exist |
| Orphan detection | Warning | Entities with no relationships |
| Meta completeness | Info | project name, schema_version present |
| Capability realization | Warning | Every capability realized by >=1 component |

**Score 100** = no critical/warning issues. **Score 80+** = acceptable.

## Model File Structure

```yaml
meta:
  project: my-project
  schema_version: '1.3'
entities:
  components: [...]
  capabilities: [...]
  behaviors: [...]
  interfaces: [...]
  layers: [...]
  constraints: [...]
  actors: [...]
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
```
"""


_API = r"""# MCP Tool API Reference

## Tool Pipeline (typical extraction flow)

```
1. architect_scan     -> understand repo structure
2. architect_group    -> get suggested component boundaries
3. architect_slice    -> get compressed context for reasoning
4. [agent produces YAML model]
5. architect_validate -> check model quality (target: 80+)
6. architect_extract  -> store model + auto-generate everything
7. architect_check    -> verify representativeness vs code reality
8. architect_export   -> export flat files for mobile AI use
```

## Tool Signatures & Returns

### architect_scan(repo_path) -> dict
AST-based reality manifest. Returns modules, functions, imports, metrics, suggested_components.

### architect_slice(repo_path, focus="all", budget=4000, detail="standard") -> str
Core token-arbitrage function. Compresses repo into dense context within budget.

### architect_validate(model_yaml) -> dict
Returns: score (0-100), issues, entity_count, relationship_count, is_valid.

### architect_extract(repo_path, model_yaml, context_tokens=0) -> dict
Stores model + auto-runs: docs, decompose, behaviors, flow classification, noise reduction.

### architect_group(repo_path, target_groups=0) -> dict
Returns suggested component groupings from code structure.

### architect_check(repo_path, model_yaml) -> dict
Returns: file_coverage, relationship_accuracy, boundary_coherence, overall (all 0-100%).

### architect_export(repo_path, output_format="zip", output_path="") -> dict
Exports flat files for mobile AI use. Returns: output_path, files, file_count, total_size.

### architect_docs(repo_path, formats="all") -> dict
Generates docs: component_spec, icd, dependency_matrix, health, drift, behaviors, index.

### architect_decompose(repo_path) -> dict
Decomposes model into F-block sub-models.

## Token Arbitrage — How to Save Tokens

### The Core Insight

The architecture model compresses a full repository (~500 files, ~50K lines) into:
- **Model YAML**: ~200-400 lines covering ALL components and relationships
- **Slice output**: ~430 tokens of dense context (configurable via budget)
- **Per-behavior sub-model**: ~20-50 lines for a specific flow

### Token-Saving Strategies

#### 1. Hierarchical Drill-Down (cheapest)
```
Start: model.yaml (~400 tokens)
  -> Identify relevant component
  -> Load component sub-model (~50 tokens)
  -> Load component manifest (~200 tokens)
  -> Only THEN read actual source files
```
**Cost: ~650 tokens instead of ~50,000 for reading all files**

#### 2. Behavior-Scoped Context
```
1. Check behavior index for the relevant flow
2. Load that behavior's sub-model (components involved)
3. Load scoped manifest (only touched files)
4. Read only those 3-5 files
```
**Cost: ~300 tokens + 5 file reads instead of blind exploration**

#### 3. Slice with Focus
```
architect_slice(repo, focus="COMP-3", budget=2000)  # One component
architect_slice(repo, focus="F2", budget=1000)       # One F-block
architect_slice(repo, focus="icd", budget=500)       # Just interfaces
```

#### 4. Manifest as Oracle
Manifest JSON has EVERY function signature, import, and call edge:
```
Load manifests/COMP-X.json -> find function -> read .calls field
-> Know dependencies without reading source
```

### Anti-Patterns (Token Waste)

| Wasteful | Better |
|----------|--------|
| Read all source files | Read model.yaml |
| Grep for function usages | Check manifest .calls field |
| Read 20 files for a flow | Load behavior spec |
| Generate manifest every time | Use cached manifests/*.json |
| Load full model for one component | Use slice with focus |

### Budget Guidelines

| Task | Recommended Budget |
|------|-------------------|
| Quick overview | 500 tokens |
| Feature planning | 2000 tokens |
| Full extraction | 4000 tokens |
| Single component | 1000 tokens |
"""
