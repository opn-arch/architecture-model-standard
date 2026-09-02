# Hierarchy Semantic Preservation Design

## Goal

Preserve scoped workflow evidence and inline architecture detail during hierarchical synthesis while deriving universal component semantics only from model evidence.

## Architecture

Synthesis will use boundary-aware evidence selection before launching each scoped pipeline. A correction is included when its source files, sent files, or file allocations intersect the boundary, or when it is explicitly marked project-wide/shared. LLM provenance follows selected corrections by resolution ID, preventing evidence leakage between disjoint systems.

The existing scoped model builder will become the canonical projection path for full systems and inline components. Full-system projections remain standalone submodels. Inline projections are merged into the top model because they have no `sub_model_ref`; IDs and references are deterministically remapped when they collide with systems, actors, components, or other inline entities.

After projection, graph-derived enrichment populates component semantics, requirement references, and interface references. Values are copied only from realized capabilities, exposed interfaces, ownership-linked requirements, and existing source semantics. Derivation provenance is recorded in supported evidence or extension fields, with no synthetic measures or rationale.

## Data Flow

1. Decomposition supplies full-system and inline boundaries.
2. Synthesis filters corrections and matching LLM calls for each full-system scoped context.
3. Scoped stages produce complete full-system models.
4. Top-stage outputs are projected independently for each inline boundary.
5. Inline projections are merged into the top System-of-Systems model with collision-safe IDs and valid relationships.
6. Semantic references and component summaries are derived from the resulting local graph.
7. Validation, promotion, and viewer generation consume the unchanged model schema.

## Testing

Strict red-green tests cover disjoint correction/provenance propagation first. An end-to-end fixture then covers one five-file subsystem and two inline components, each with structured workflow evidence and numeric requirement/interface data. Assertions cover scope isolation, semantic derivation, no flattening, unique IDs, no dangling references, model validation, promotion, qualified viewer relationships, and viewer page embedding.
