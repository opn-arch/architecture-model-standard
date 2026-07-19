# Recursive Sub-Models Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan from this design.

**Goal:** Make sub-models genuinely recursive — each level adds detail not present above — and provide Mermaid visualization of the architecture.

## Current Problem

Sub-models are pure subsets of the parent model. Every entity, relationship, and behavior in a sub-model also exists identically in the parent. They provide filtered views, not additional information.

## Design

### Phase B: Enrich Sub-Behaviors via AST

Write `scripts/enrich_sub_behaviors.py` that:

1. Maps each sub-behavior ID to a source function via a hardcoded mapping table:
   - `BEH-VALIDATE-IDS` --> `src/architecture_model/core/validator.py::_check_id_uniqueness`
   - etc.
2. Parses each function's AST to extract:
   - **steps**: Ordered list of key operations (function calls, conditionals, loops)
   - **preconditions**: Parameter type annotations, early-return guards, assertions
   - **postconditions**: Return type annotation, return value patterns
   - **trigger**: Name of the calling function (from call graph)
3. Updates Behavior objects in the model and saves

**Output:** ~70 sub-behaviors with populated steps/preconditions/postconditions fields.

### Phase A: Strict Layering (True Recursion)

Modify the decompose pipeline so parent and sub-models contain different information:

**Parent model changes:**
- Keep ONLY 9 top-level behaviors (BEH-INIT, BEH-VALIDATE, BEH-MANIFEST, BEH-ENRICH, BEH-EXTRACT, BEH-SLICE, BEH-DIFF, BEH-MERGE, BEH-DECOMPOSE)
- Remove all 70 sub-behaviors and their `contains`/`traces-to` relationships
- Parent = architecture overview (what the system does)

**Sub-model changes:**
- Decomposer injects sub-behaviors from an enrichment data source
- Sub-behaviors have full detail (steps, pre/post, trigger)
- Sub-model = implementation detail (how the block does it)

**Recursion mechanism:** Components + `contains` relationships, NOT System entities.
- Parent: `COMP-CORE` (contains 7 sub-components, traces-to `BEH-VALIDATE`)
- F3 sub-model: `COMP-CORE-VALIDATOR` (traces-to `BEH-VALIDATE-IDS` with steps/pre/post)
- `meta.refines_component = "COMP-CORE"` links sub-model back to parent

**Loading protocol:**
- `load_model(parent)` --> 9 behaviors, 25 components, architecture overview
- `load_model(sub)` --> block-specific sub-behaviors with implementation detail

### Phase C: Mermaid Visualization

Add `architecture-model visualize` CLI command generating `.md` files with Mermaid diagrams:

1. **Overview diagram** (`output/diagrams/overview.md`):
   - 9 behaviors as nodes in a flowchart
   - Components grouped by f_block in subgraphs
   - `traces-to` edges from components to behaviors

2. **Per-block diagrams** (`output/diagrams/F{n}-detail.md`):
   - Sub-behaviors as nodes
   - `contains` hierarchy (parent behavior --> sub-behaviors)
   - Steps listed as labels
   - `depends-on` edges to other blocks

3. **Dependency graph** (`output/diagrams/dependencies.md`):
   - Components as nodes, colored by f_block
   - `depends-on` edges
   - Cross-block boundaries highlighted

## Why NOT System Entities

The `System` entity type aggregates components into subsystems, but parent Components + `contains` relationships already express this hierarchy. Adding System would create a parallel, redundant grouping. System is designed for the decomposer's `identify_systems` (discovering groupings in unknown codebases), not for modeling known architecture.

## Validation

- Parent model: 100/100 (fewer entities = fewer orphan risks)
- Sub-models: Should each validate independently
- All 453 tests pass throughout
- Each sub-model has behaviors NOT in parent (verified programmatically)
