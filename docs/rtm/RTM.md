# Requirements Traceability Matrix (RTM)

Auto-generated from `.architecture-model.yaml`. Every requirement is linked
to the component(s) that satisfy it via `satisfies` relationships.

**Total requirements:** 45
**Total satisfies edges:** 45
**Coverage:** 45/45 = 100%

## Matrix

| Req ID | Requirement | Priority | Satisfied By | Rationale |
|--------|-------------|:--------:|--------------|-----------|
| REQ-E1 | test_pattern_classification.py has 11 error-handling functions | could | COMP-11 (Pipeline Learning) | Pipeline Learning subsystem provides error classification |
| REQ-O1 | validate_model requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments validate_model |
| REQ-O10 | slice_for_artifact requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments slice_for_artifact |
| REQ-O11 | generate_recursive_manifests requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments generate_recursive_manifests |
| REQ-O12 | compute_block_dependencies requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments compute_block_dependencies |
| REQ-O13 | generate_manifest requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments generate_manifest |
| REQ-O14 | enrich_from_manifest requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments enrich_from_manifest |
| REQ-O15 | enrich_behaviors_from_manifest requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments enrich_behaviors_from_manifest |
| REQ-O16 | enrich_with_block_context requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments enrich_with_block_context |
| REQ-O17 | create_behaviors_from_manifest requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments create_behaviors_from_manifest |
| REQ-O18 | decompose_model requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments decompose_model |
| REQ-O19 | compact_root_model requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments compact_root_model |
| REQ-O2 | compute_model_confidence requires monitored | should | COMP-13 (SI&L Instrumentation) | SI&L instruments compute_model_confidence |
| REQ-Q1 | Component COMP-28 has 82 test file(s) covering its source | should | COMP-1.2 (Validation) | Validation covers Component quality metrics |
| REQ-T20 | Python >=3.11: Project requires Python >=3.11 | must | COMP-9 (Configuration) | Configuration declares Python >=3.11 constraint |
| REQ-1 | Model validation score threshold | must | COMP-1.2 (Validation) | Validator enforces score >= 80 |
| REQ-10 | Multi-language scanning | should | COMP-3.1 (Scanners) | Multi-scanner supports Python/TS/Kotlin |
| REQ-11 | Live artifact regeneration | must | COMP-4.1 (Core Doc Generators) | Template-based generators run in <1s |
| REQ-12 | SE doc completeness | must | COMP-4.2 (SE Document Suite) | SE suite generates all required doc types |
| REQ-13 | User edit preservation | should | COMP-4.2 (SE Document Suite) | SE generator preserves user edits on regen |
| REQ-14 | Requirements-to-model parsing | must | COMP-7 (Authoring) | Authoring parser handles markdown requirements |
| REQ-15 | Regen score accuracy | should | COMP-1.5 (Quality Metrics) | Regen readiness scoring |
| REQ-16 | Per-component readiness | must | COMP-1.5 (Quality Metrics) | Per-component readiness with blockers |
| REQ-17 | Test preservation | must | COMP-2.4 (Specification & Contract Stages) | Validate stage ensures test preservation |
| REQ-18 | Behavior filtering cap | must | COMP-5.1 (Enrichment) | Enrichment applies behavior cap at 40 |
| REQ-19 | Boundary coherence | should | COMP-3.3 (Grouping & Generation) | Grouping optimizes boundary coherence |
| REQ-2 | Zero errors on valid models | must | COMP-1.2 (Validation) | Validator checks produce zero errors on valid models |
| REQ-20 | Token-efficient output | must | COMP-1.4 (Model Operations) | Slicer enforces token budget |
| REQ-21 | Self-documenting artifacts | must | COMP-4 (Documentation) | All docs are self-documenting markdown |
| REQ-22 | Hierarchical navigation | must | COMP-1.1 (Type System) | Type system supports parent_id/children |
| REQ-23 | Graceful degradation | must | COMP-2.1 (Pipeline Coordination) | Coordinator catches stage failures gracefully |
| REQ-24 | Uncertainty surfacing | should | COMP-2.2 (Observation Stages) | Infer stage surfaces uncertainties |
| REQ-25 | Large repo handling | should | COMP-2 (Pipeline) | Pipeline completes large repos without LLM |
| REQ-26 | MCP tool compatibility | must | COMP-8 (CLI) | CLI exposes all operations for MCP wrapping |
| REQ-27 | YAML round-trip fidelity | must | COMP-1.3 (Parser & Persistence) | Parser ensures round-trip fidelity |
| REQ-28 | Schema backward compatibility | should | COMP-1.3 (Parser & Persistence) | Parser handles old schema versions |
| REQ-29 | Flat-file export completeness | should | COMP-10 (Export) | Export includes all artifact types |
| REQ-3 | Hierarchy consistency | must | COMP-1.2 (Validation) | Hierarchy validator checks bidirectional consistency |
| REQ-30 | Offline AI usability | should | COMP-10 (Export) | Export is self-contained for AI |
| REQ-4 | Entity type coverage | must | COMP-2.2 (Observation Stages) | Infer stage produces all entity types |
| REQ-5 | Relationship population | must | COMP-2.3 (Allocation & Relation Stages) | Relate stage produces typed relationships |
| REQ-6 | Deterministic pipeline | must | COMP-2.1 (Pipeline Coordination) | Pipeline coordinator runs deterministically |
| REQ-7 | Pipeline stage independence | should | COMP-2.1 (Pipeline Coordination) | Stage caching enables independent runs |
| REQ-8 | Complete file scanning | must | COMP-3.1 (Scanners) | Scanners cover all Python files |
| REQ-9 | Import edge resolution | must | COMP-3.2 (Graph & Analysis) | Graph analysis resolves imports to edges |

## Coverage by Component

| Component | # Requirements Satisfied |
|-----------|-------------------------:|
| COMP-1.1 (Type System) | 1 |
| COMP-1.2 (Validation) | 4 |
| COMP-1.3 (Parser & Persistence) | 2 |
| COMP-1.4 (Model Operations) | 1 |
| COMP-1.5 (Quality Metrics) | 2 |
| COMP-10 (Export) | 2 |
| COMP-11 (Pipeline Learning) | 1 |
| COMP-13 (SI&L Instrumentation) | 12 |
| COMP-2 (Pipeline) | 1 |
| COMP-2.1 (Pipeline Coordination) | 3 |
| COMP-2.2 (Observation Stages) | 2 |
| COMP-2.3 (Allocation & Relation Stages) | 1 |
| COMP-2.4 (Specification & Contract Stages) | 1 |
| COMP-3.1 (Scanners) | 2 |
| COMP-3.2 (Graph & Analysis) | 1 |
| COMP-3.3 (Grouping & Generation) | 1 |
| COMP-4 (Documentation) | 1 |
| COMP-4.1 (Core Doc Generators) | 1 |
| COMP-4.2 (SE Document Suite) | 2 |
| COMP-5.1 (Enrichment) | 1 |
| COMP-7 (Authoring) | 1 |
| COMP-8 (CLI) | 1 |
| COMP-9 (Configuration) | 1 |

## Gaps

_None — every requirement is traced to at least one satisfying component._

---

Regenerate: `python -c "from architecture_model.docs.rtm import generate; generate()"`
or run `architecture-model rtm > docs/rtm/RTM.md` (Commit 11).
