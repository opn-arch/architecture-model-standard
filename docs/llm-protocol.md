# LLM Integration Protocol

## 1. Overview

The Architecture Model Standard provides a structured interface between architecture models and Large Language Models. This protocol defines how models are serialized, queried, and updated through LLM interactions.

### Core Principle

**The model is the architectural memory that LLMs lack.** Without it, each LLM call starts from zero context. With it, every generation is grounded in verified structural truth.

### Token Economics

| Representation | Tokens | Information Density |
|---------------|--------|-------------------|
| Full artifact markdown | ~15,000 | Low (prose, formatting) |
| Raw manifest JSON | ~8,000 | Medium (raw data) |
| Model context (standard) | ~1,100 | High (structured, compressed) |
| Model context (F-block slice) | ~430 | Very high (focused) |
| Model context (minimal) | ~250 | Maximum (entities only) |

The model achieves **~14:1 compression** vs full artifact text while preserving all structural relationships.

---

## 2. Protocol Commands

### LOAD — Serialize model for prompt injection

**Purpose**: Convert model (or slice) into compact text for LLM system/user prompt.

**Input**: Model instance + optional filters (artifact name, F-block, token budget)

**Output**: Structured text optimized for LLM comprehension

**Format** (standard detail level):
```
=== ARCHITECTURE MODEL: {project} ===
Schema: {version} | Generated: {date}

CAPABILITIES ({count}):
  {id}: {name} [{status}] (F-block: {f_block})

ACTORS ({count}):
  {id}: {name} ({type}) [{status}]

BEHAVIORS ({count}):
  {id}: {name} [Actor: {actor}] [{status}]

INTERFACES ({count}):
  {id}: {name} ({protocol}) [Provider: {provider} → Consumer: {consumer}]

CONSTRAINTS ({count}):
  {id}: {name} ({type}) [{status}]

LAYERS ({count}):
  {id}: {name} [{status}]

COMPONENTS ({count}):
  {id}: {name} [Layer: {layer}, F-block: {f_block}]

RELATIONSHIPS ({count}):
  {from} --{type}--> {to}
===
```

**Token budget control**:
- `minimal`: Capabilities + Actors only (~250 tokens)
- `standard`: All entity types, abbreviated (~1,100 tokens)
- `full`: All entities with descriptions + all relationships (~2,500 tokens)

### QUERY — Answer structural questions

**Purpose**: Answer questions about architecture using model data without requiring LLM inference.

**Input**: Model instance + natural language question

**Output**: Structured answer derived from model traversal

**Examples**:
```
Q: "What realizes F3?"
A: Components [COMP-kb-derive, COMP-update-kb, COMP-seed-kb, ...] realize CAP-F3

Q: "What actors interact with F1?"
A: Actors [A-01 (human), external-onedrive-onenote (external_service)] 
   via behaviors [BEH-01, BEH-02, BEH-03]

Q: "What depends on the data layer?"
A: Relationships: [pipeline depends-on data-layer, services depends-on data-layer]
```

**Implementation**: Graph traversal on relationship edges. No LLM needed.

### IMPACT — Trace change effects

**Purpose**: Given a proposed change to one entity, determine what other entities and artifacts are affected.

**Input**: Model instance + entity ID + optional depth limit

**Output**: List of affected entities (direct + transitive) + affected artifacts

**Algorithm**:
1. Find all relationships where entity is `from` or `to`
2. Collect connected entity IDs (depth 1)
3. If depth > 1, recursively expand
4. Map affected entities to artifact slicers → affected artifacts

**Example**:
```
IMPACT CAP-F3 --depth 2:
  Direct: [COMP-kb-derive, COMP-update-kb, COMP-seed-kb, ...]
  Transitive: [BEH-05, BEH-06, CON-03, ...]
  Affected artifacts: [functional-architecture, use-cases, operations-manual, testing]
```

### VALIDATE — Check model invariants

**Purpose**: Verify model consistency and report score.

**Input**: Model instance

**Output**: Score (0-100) + list of issues with severity/code/message

**See**: Specification section 6 for validation rules.

### UPDATE — Propose model changes

**Purpose**: After generating or modifying an artifact, extract new entities/relationships and propose model updates.

**Input**: Model instance + new artifact content + artifact name

**Output**: Proposed additions/modifications to the model (diff format)

**Workflow**:
1. Extract entities from new artifact text (table parsing, pattern matching)
2. Compare against existing model entities
3. Produce diff: new entities, modified entities, new relationships
4. Human reviews and approves changes
5. Apply approved changes to model YAML

### PROJECT — Generate focused context for artifact

**Purpose**: Combine model slice + manifest slice into a single context block optimized for a specific artifact's regeneration.

**Input**: Model instance + manifest data + artifact name + token budget

**Output**: Combined context block with both structural truth (model) and ground truth (manifest)

**Format**:
```
=== ARCHITECTURE CONTEXT for {artifact} ===

[MODEL SLICE — {entity_count} entities, {rel_count} relationships]
{formatted model context for this artifact}

[MANIFEST SLICE — verified from code]
{formatted manifest data for this artifact}
===
```

**This is the primary integration point** — used by `enrich_manifest_slice()` in the pipeline bridge.

---

## 3. Slicing Strategy

Each artifact gets a model subset optimized for its generation needs:

| Artifact | Primary Entities | Relationships | Approx Tokens |
|----------|-----------------|---------------|---------------|
| functional-architecture | Capabilities, Behaviors, Actors | realizes, contains | ~800 |
| logical-architecture | Layers, Components, Capabilities | allocated-to, depends-on | ~700 |
| use-cases | Actors, Behaviors, Capabilities | realizes, depends-on | ~600 |
| icd | Interfaces, Components, Layers | exposes, consumes | ~500 |
| requirements-analysis | Constraints, Capabilities, Behaviors | constrained-by, traces-to | ~600 |
| operations-manual | Behaviors, Components, Interfaces | realizes, exposes | ~700 |
| testing | Constraints, Behaviors, Components | realizes, constrained-by | ~600 |
| deployment-guide | Layers, Components, Interfaces, Actors | depends-on, exposes | ~500 |
| data-dictionary | Components (data layer), Interfaces | realizes, exposes | ~400 |
| readme | Actors, Capabilities, Layers | realizes | ~300 |
| conops | Actors, Capabilities, Behaviors, Constraints | realizes, depends-on | ~700 |

---

## 4. Integration Patterns

### Pattern 1: Prepend to Manifest Slice

The most common pattern — prepend model context before the manifest data in artifact generation prompts.

```python
from architecture_model.integrations.pipeline_bridge import enrich_manifest_slice

# Before: raw manifest slice
prompt_context = get_manifest_slice(manifest, "icd")

# After: model-enriched context
prompt_context = enrich_manifest_slice(manifest, "icd", project_root)
```

### Pattern 2: System Prompt Injection

For conversational interactions, inject model context into the system prompt:

```python
from architecture_model.integrations.llm_context import format_model_context

system_prompt = f"""You are an architecture assistant.

{format_model_context(model, max_tokens=1000)}

Answer questions about this system's architecture."""
```

### Pattern 3: Change Impact Pre-check

Before modifying code, check what artifacts need updating:

```python
from architecture_model.core.differ import diff_models
from architecture_model.integrations.pipeline_bridge import get_model

old_model = get_model(project_root)
# ... make changes, re-extract ...
new_model = get_model(project_root, force_refresh=True)

diff = diff_models(old_model, new_model)
print(f"Affected artifacts: {diff.affected_artifacts}")
```

### Pattern 4: Validation Gate

In CI/CD, fail the build if model degrades:

```python
from architecture_model.core.validator import validate_model
from architecture_model.core.parser import load_model

model = load_model("architecture-model.yaml")
result = validate_model(model)
if result.score < 90:
    raise SystemExit(f"Model score {result.score}/100 below threshold")
```

---

## 5. Token Budget Management

### Budget Allocation for Artifact Generation

Typical artifact generation uses ~62K token prompt. Budget allocation:

| Section | Tokens | Source |
|---------|--------|--------|
| System prompt + instructions | ~2,000 | Template |
| Architecture model context | ~1,000 | Model slice |
| Manifest slice | ~8,000 | Manifest |
| Template guidance | ~3,000 | Template definitions |
| Cross-reference context | ~500 | Other artifact summaries |
| **Total context** | **~14,500** | |
| **Available for generation** | **~47,500** | LLM output |

### Compression Techniques

1. **Entity abbreviation**: Omit descriptions when over budget
2. **Relationship deduplication**: Collapse symmetric relationships
3. **Status filtering**: Only include ACTIVE entities unless PLANNED is relevant
4. **Depth limiting**: For impact analysis, cap traversal depth
5. **Count-only mode**: Replace entity lists with counts when extremely constrained
