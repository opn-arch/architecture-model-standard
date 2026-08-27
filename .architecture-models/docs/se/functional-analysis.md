---
document: Functional Analysis
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:21Z
generator_version: 0.3.0
model_hash: 08abc716587d
edition: 9
---

# Functional Analysis: architecture-model-standard

## Capability Inventory

| ID | Capability | Priority | Status | Description | Intent |
|----|-----------|----------|--------|-------------|--------|
| CAP-1 | Validate Architecture Models | medium | ACTIVE | Check model correctness, completeness, hierarchy consistency, and domain rules | Ensure architecture models are structurally sound and internally consistent before downstream consumption |
| CAP-2 | Extract Architecture from Code | medium | ACTIVE | Scan source code AST and derive components, relationships, behaviors automatically | Bootstrap architecture models from existing codebases without manual authoring |
| CAP-3 | Run Modular Extraction Pipeline | medium | ACTIVE | Execute 10-stage pipeline (observe→infer→allocate→relate→specify→contract→validate→decompose→synthesize→emit) | Provide a repeatable, cacheable, stage-by-stage process for producing architecture models from code |
| CAP-4 | Generate Reality Manifest | medium | ACTIVE | Scan source files to produce structural facts (functions, imports, classes, routes, tests) | Establish ground-truth code inventory so architecture claims can be verified against reality |
| CAP-5 | Generate SE Documentation | medium | ACTIVE | Produce functional analysis, logical architecture, use cases, requirements, V&V, operations docs | Auto-generate standards-compliant systems engineering documentation from architecture models |
| CAP-6 | Author Model from Requirements | medium | ACTIVE | Parse requirements document into a concept-phase architecture model | Enable forward-engineering by converting stakeholder requirements into architecture before code exists |
| CAP-7 | Slice and Query Models | medium | ACTIVE | Filter model by block, layer, status, artifact for focused context delivery | Deliver only relevant architecture context to token-limited AI agents and focused human queries |
| CAP-8 | Diff Model Versions | medium | ACTIVE | Compare two model versions showing additions, removals, and changes | Track architectural evolution over time and detect unintended structural changes |
| CAP-9 | Decompose Models Hierarchically | medium | ACTIVE | Break coarse models into per-system sub-models with parent/child relationships | Enable scalable architecture management by splitting large models into focused, self-contained subsystems |
| CAP-10 | Enrich Models with Code Intelligence | medium | ACTIVE | Auto-populate signatures, constants, test contracts, behaviors from source | Bridge the gap between abstract architecture and concrete code to enable faithful code regeneration |
| CAP-11 | Assess Regen Readiness | medium | ACTIVE | Score how well a model captures enough detail to regenerate code | Quantify whether a model contains sufficient information for an AI agent to regenerate working code |
| CAP-12 | Check Development Gate | medium | ACTIVE | Verify code reality is tracking toward authored architecture intent | Prevent architectural drift by gating development milestones on model-to-code alignment |
| CAP-13 | Detect and Fix Model Drift | medium | ACTIVE | Compare model against current code, report coverage gaps | Keep architecture models synchronized with evolving codebases by detecting and reporting divergence |
| CAP-14 | Manage Global Learnings | medium | ACTIVE | Store, retrieve, and apply heuristics/archetypes/workflows across pipeline runs | Improve pipeline accuracy over time by accumulating and reusing extraction patterns |
| CAP-15 | Export for AI Consumption | medium | ACTIVE | Produce flat-file exports optimized for token-limited AI environments | Make architecture models portable and consumable by AI agents that cannot access the repository directly |

## Measures of Effectiveness

| Capability | MOE |
|---|---|
| Validate Architecture Models (CAP-1) | Validation score >= 80 on well-formed models |
| Validate Architecture Models (CAP-1) | Zero false-positive errors on valid models |
| Validate Architecture Models (CAP-1) | All referential integrity violations detected |
| Extract Architecture from Code (CAP-2) | Extraction produces valid models scoring >= 90 on arbitrary Python repos |
| Extract Architecture from Code (CAP-2) | All non-trivial source files represented in the model |
| Extract Architecture from Code (CAP-2) | Relationship types correctly inferred from import analysis |
| Run Modular Extraction Pipeline (CAP-3) | All 10 stages complete without error on repos with >200 files |
| Run Modular Extraction Pipeline (CAP-3) | Each stage independently runnable with cached predecessors |
| Run Modular Extraction Pipeline (CAP-3) | Deterministic output for identical input |
| Generate Reality Manifest (CAP-4) | All non-trivial Python files scanned with function/class extraction |
| Generate Reality Manifest (CAP-4) | Import edges resolved with >95% accuracy |
| Generate Reality Manifest (CAP-4) | Manifest generation completes in <10s for repos with 200 files |
| Generate SE Documentation (CAP-5) | Generate at least 15 SE document types from a single model |
| Generate SE Documentation (CAP-5) | Core docs (health, functional-analysis) regenerate in <1s without LLM |
| Generate SE Documentation (CAP-5) | User-edited sections preserved across regeneration |
| Author Model from Requirements (CAP-6) | Parse markdown requirements into valid ArchitectureModel |
| Author Model from Requirements (CAP-6) | Actors, capabilities, and constraints correctly extracted |
| Author Model from Requirements (CAP-6) | Generated model passes validation with score >= 80 |
| Slice and Query Models (CAP-7) | Sliced output fits within 4000-token budget |
| Slice and Query Models (CAP-7) | Slice preserves all relationships touching included entities |
| Slice and Query Models (CAP-7) | Query response time <100ms for any slice operation |
| Diff Model Versions (CAP-8) | All added, removed, and changed entities detected |
| Diff Model Versions (CAP-8) | Diff output human-readable and machine-parseable |
| Diff Model Versions (CAP-8) | Diff completes in <1s for models with 100+ entities |
| Decompose Models Hierarchically (CAP-9) | Components with >=5 files produce autonomous sub-models |
| Decompose Models Hierarchically (CAP-9) | Each sub-model is independently valid |
| Decompose Models Hierarchically (CAP-9) | Parent model correctly references all child systems |
| Enrich Models with Code Intelligence (CAP-10) | Signatures populated for >90% of public functions |
| Enrich Models with Code Intelligence (CAP-10) | Body hints cover trivial functions (one-liners) |
| Enrich Models with Code Intelligence (CAP-10) | Test contracts extracted for all test files with assertions |
| Assess Regen Readiness (CAP-11) | Regen score correlates with actual test pass rate (r > 0.8) |
| Assess Regen Readiness (CAP-11) | Per-component scores with actionable blocker list |
| Assess Regen Readiness (CAP-11) | Grade scale (A-F) matches blind regeneration fidelity |
| Check Development Gate (CAP-12) | Gate check reports coverage percentage of authored capabilities |
| Check Development Gate (CAP-12) | Unimplemented capabilities clearly flagged |
| Check Development Gate (CAP-12) | Gate result includes pass/fail with actionable gaps |
| Detect and Fix Model Drift (CAP-13) | File coverage reported as percentage of source files modeled |
| Detect and Fix Model Drift (CAP-13) | Orphan components (no matching files) detected |
| Detect and Fix Model Drift (CAP-13) | Drift report generated in <5s |
| Manage Global Learnings (CAP-14) | Learnings persisted across pipeline runs |
| Manage Global Learnings (CAP-14) | Pattern lookup returns relevant heuristics in <100ms |
| Manage Global Learnings (CAP-14) | Duplicate learnings deduplicated by content hash |
| Export for AI Consumption (CAP-15) | Export includes model, sub-models, docs, manifests, and diagrams |
| Export for AI Consumption (CAP-15) | Exported package is self-contained (no external dependencies) |
| Export for AI Consumption (CAP-15) | Total export size fits within reasonable token budgets for frontier models |

## Functional Decomposition

```mermaid
graph TD
    CAP-1["Validate Architecture Models"]
    CAP-2["Extract Architecture from Code"]
    CAP-3["Run Modular Extraction Pipeline"]
    CAP-4["Generate Reality Manifest"]
    CAP-5["Generate SE Documentation"]
    CAP-6["Author Model from Requirements"]
    CAP-7["Slice and Query Models"]
    CAP-8["Diff Model Versions"]
    CAP-9["Decompose Models Hierarchically"]
    CAP-10["Enrich Models with Code Intelligence"]
    CAP-11["Assess Regen Readiness"]
    CAP-12["Check Development Gate"]
    CAP-13["Detect and Fix Model Drift"]
    CAP-14["Manage Global Learnings"]
    CAP-15["Export for AI Consumption"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Validate Architecture Models | Validation (COMP-1.2) | library |
| Extract Architecture from Code | Extract (COMP-6) | library |
| Run Modular Extraction Pipeline | Pipeline (COMP-2) | service |
| Generate Reality Manifest | Manifest (COMP-3) | library |
| Generate SE Documentation | SE Document Suite (COMP-4.2) | library |
| Author Model from Requirements | Authoring (COMP-7) | library |
| Slice and Query Models | Model Operations (COMP-1.4) | library |
| Diff Model Versions | Model Operations (COMP-1.4) | library |
| Decompose Models Hierarchically | Decomposition (COMP-5.2) | service |
| Enrich Models with Code Intelligence | Enrichment (COMP-5.1) | service |
| Assess Regen Readiness | Quality Metrics (COMP-1.5) | library |
| Check Development Gate | Authoring (COMP-7) | library |
| Detect and Fix Model Drift | Model Operations (COMP-1.4) | library |
| Manage Global Learnings | Pipeline Learning (COMP-11) | library |
| Export for AI Consumption | Export (COMP-10) | library |

### Design Trade-offs

**Core** (COMP-1):
- Rich type system vs. schema simplicity for external consumers
- Strict validation vs. permissive parsing for backward compatibility
- Monolithic core vs. fine-grained packages (chose monolithic for import simplicity)

**Pipeline** (COMP-2):
- Stage granularity (10 stages) vs. simpler monolithic extraction
- Cache correctness vs. cache invalidation complexity
- Determinism vs. allowing LLM enrichment between stages

**Manifest** (COMP-3):
- AST-only analysis (fast, deterministic) vs. runtime analysis (more accurate)
- Language-specific scanners vs. universal parsing (chose per-language for accuracy)
- Scan depth vs. performance on large repos

**Documentation** (COMP-4):
- Template-based generation (fast, consistent) vs. LLM-generated prose (richer)
- Document completeness vs. generation speed
- Preserving user edits vs. full regeneration freshness

**Orchestration** (COMP-5):
- Automated enrichment (convenient) vs. manual curation (precise)
- Aggressive decomposition vs. keeping small systems inline
- Behavior cap (40 per component) vs. complete behavioral coverage

**Extract** (COMP-6):
- Framework-specific detection (accurate) vs. generic heuristics (portable)
- Extracting from code vs. from documentation (chose both with priority on code)
- Precision vs. recall in constraint detection

**Authoring** (COMP-7):
- Structured parsing (reliable) vs. LLM-based understanding (flexible)
- Strict gate enforcement vs. advisory-only feedback
- Requirements granularity vs. model abstraction level

**CLI** (COMP-8):
- Single monolithic CLI vs. per-subsystem CLIs (chose monolithic for discoverability)
- Rich interactive output vs. machine-parseable output (support both via flags)
- Exposing all operations vs. curating a minimal command set

**Configuration** (COMP-9):
- Convention-over-configuration (easy start) vs. explicit config (predictable)
- Built-in profiles vs. user-defined profiles (support both)
- Schema strictness vs. forward compatibility with new fields

**Export** (COMP-10):
- Complete export (large) vs. minimal export (fits token budgets)
- Directory-based export vs. single archive (support both)
- Including all artifacts vs. selective export based on use case

**Utilities** (COMP-12):
- Shared utilities (DRY) vs. subsystem autonomy (decoupled)
- Monitoring overhead vs. operational visibility
- General-purpose utilities vs. domain-specific helpers

## Behavioral Coverage

Total behaviors: 7

**Untraced behaviors:** 7
- CLI: Test Guided Round Trip (BEH-19)
- CLI: Test Enriched Round Trip (BEH-20)
- CLI: Test Multi Repo (BEH-21)
- CLI: Test Round Trip (BEH-22)
- CLI: Test Decomposed Round Trip (BEH-23)
- CLI: Main (BEH-24)
- CLI: Runner (BEH-25)
