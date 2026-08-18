---
document: ConOps
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-17T18:14:22Z
generator_version: 0.3.0
model_hash: 107792ca3a62
edition: 4
---

# Concept of Operations: architecture-model-standard

## System Overview

architecture-model-standard provides 15 capabilities implemented across 29 components.

**Core Capabilities:**

- **Validate Architecture Models** - Check model correctness, completeness, hierarchy consistency, and domain rules
- **Extract Architecture from Code** - Scan source code AST and derive components, relationships, behaviors automatically
- **Run Modular Extraction Pipeline** - Execute 10-stage pipeline (observe→infer→allocate→relate→specify→contract→validate→decompose→synthesize→emit)
- **Generate Reality Manifest** - Scan source files to produce structural facts (functions, imports, classes, routes, tests)
- **Generate SE Documentation** - Produce functional analysis, logical architecture, use cases, requirements, V&V, operations docs
- **Author Model from Requirements** - Parse requirements document into a concept-phase architecture model
- **Slice and Query Models** - Filter model by block, layer, status, artifact for focused context delivery
- **Diff Model Versions** - Compare two model versions showing additions, removals, and changes
- **Decompose Models Hierarchically** - Break coarse models into per-system sub-models with parent/child relationships
- **Enrich Models with Code Intelligence** - Auto-populate signatures, constants, test contracts, behaviors from source
- **Assess Regen Readiness** - Score how well a model captures enough detail to regenerate code
- **Check Development Gate** - Verify code reality is tracking toward authored architecture intent
- **Detect and Fix Model Drift** - Compare model against current code, report coverage gaps
- **Manage Global Learnings** - Store, retrieve, and apply heuristics/archetypes/workflows across pipeline runs
- **Export for AI Consumption** - Produce flat-file exports optimized for token-limited AI environments

## Stakeholders

| Actor | Type | Goals |
|-------|------|-------|
| AI Agent (MCP Client) | human | — |
| Developer | human | — |
| CI/CD Pipeline | human | — |

## Operational Scenarios

*No behaviors defined in the model.*

## System Context

*No interfaces defined in the model.*

## Operational Constraints

*No constraints defined in the model.*
