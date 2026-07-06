# architecture-model-standard

A universal, machine-readable Architecture-as-Code standard for LLM-driven system engineering.

## Overview

The Architecture Model Standard defines a YAML schema for capturing software system architecture — entities, relationships, constraints — in a format that is human-editable, git-diffable, and optimized for LLM token budgets. It serves as the architectural spine between raw code analysis and artifact generation: code is scanned into a Reality Manifest, parsed into a structured architecture model, and projected as compact context for LLM-driven document generation.

The package provides a CLI for model management, a validation engine that scores architectural consistency, an LLM integration protocol with six structured verbs, and an MPC training loop that fine-tunes local models toward frontier-model quality using architecture extraction as the training task.

```
Code --> [AST Scan] --> Reality Manifest --> [Architecture Model] --> LLM Context --> Artifact Generation
                                                    ^
                                          [MPC Training Loop]
                                          Surrogate <-> Oracle
                                           LoRA Fine-tuning
```

## Install

Basic installation:

```bash
pip install architecture-model-standard
```

With MPC training loop dependencies:

```bash
pip install architecture-model-standard[training]
```

Python 3.10+ required.

## Quick Start

Initialize a project descriptor by scanning directory structure:

```bash
architecture-model init /path/to/project
```

This auto-discovers the source root (src-layout, flat-layout, or lib-layout), enumerates subpackages as functional blocks, and writes `.architecture-model.yaml`.

Extract an architecture model from generated artifacts:

```bash
architecture-model extract /path/to/artifacts
```

Validate the model and report a consistency score:

```bash
architecture-model validate architecture-model.yaml
```

The validator checks invariants (missing fields, dangling references, duplicate IDs, orphaned entities) and produces a score from 0 to 100.

## Schema Reference

### Entity Types

The schema defines seven entity types representing architectural building blocks:

| Type | ID Pattern | Description |
|------|-----------|-------------|
| Actors | `A-01`, `external-*` | External users or systems that interact with the system |
| Capabilities | `CAP-F1` | High-level functional groupings (F-blocks) the system provides |
| Behaviors | `BEH-01`, `UC-01` | Observable system actions, use cases, operational sequences |
| Interfaces | `IFC-01`, `intf-*` | APIs, protocols, and data exchange contracts between components |
| Constraints | `CON-01` | Non-functional requirements, quality attributes, design rules |
| Layers | `*-layer` | Logical architecture tiers (web, services, data, pipeline) |
| Components | `COMP-*` | Deployable units, modules, and packages that realize capabilities |

Every entity carries a `status` field: `ACTIVE`, `PLANNED`, or `DORMANT`.

### Relationship Types

Eight relationship types connect entities:

| Type | Semantics | Typical Direction |
|------|-----------|-------------------|
| `realizes` | Implementation relationship | Component --> Capability |
| `uses` | Service consumption | Component --> Interface |
| `constrains` | Quality constraint application | Constraint --> Entity |
| `contains` | Composition/ownership | Layer --> Component |
| `triggers` | Behavioral sequencing | Behavior --> Behavior |
| `depends_on` | Runtime dependency | Component --> Component |
| `implements` | Behavioral implementation | Component --> Behavior |
| `exposes` | Service provision | Component --> Interface |

## LLM Protocol

The model achieves approximately 14:1 compression versus full artifact text while preserving all structural relationships. Six protocol verbs define interactions between the model and LLMs:

| Verb | Purpose |
|------|---------|
| **LOAD** | Serialize model (or slice) into compact text for prompt injection. Supports `minimal` (~250 tokens), `standard` (~1,100 tokens), and `full` (~2,500 tokens) detail levels. |
| **QUERY** | Answer structural questions via graph traversal on relationship edges. No LLM inference required. |
| **IMPACT** | Trace change effects through relationships — given an entity, determine all affected entities and artifacts at configurable traversal depth. |
| **VALIDATE** | Check model invariants and report a consistency score (0-100) with categorized issues. |
| **UPDATE** | After generating or modifying an artifact, extract new entities and relationships and propose model changes in diff format. |
| **PROJECT** | Combine a model slice with a manifest slice into a single context block optimized for a specific artifact's regeneration. |

Integration example:

```python
from architecture_model.integrations.pipeline_bridge import enrich_manifest_slice

# Prepend model context before manifest data in artifact generation prompts
prompt_context = enrich_manifest_slice(manifest, "icd", project_root)
```

## CLI Reference

The `architecture-model` CLI provides commands for the full model lifecycle:

| Command | Description |
|---------|-------------|
| `init <path>` | Scan directory structure and generate `.architecture-model.yaml` |
| `extract <artifacts-dir>` | Build architecture model from markdown artifacts |
| `validate <model.yaml>` | Check invariants, report score (0-100) |
| `slice <model.yaml> --fblock F3` | Extract a focused subset of the model by functional block |
| `diff <old.yaml> <new.yaml>` | Structural comparison between two model versions |
| `query <model.yaml> "question"` | Answer structural questions via graph traversal |
| `context <model.yaml> --artifact icd` | Generate LLM context optimized for a specific artifact |
| `stats <model.yaml>` | Report entity and relationship counts |
| `impact <model.yaml> CAP-F1` | Trace change impact through relationships |
| `generate` | Test-guided code generation from architecture models |

## MPC Training Loop

The training module (39 source files, 10,662 lines) implements a Model-Predictive Control loop that fine-tunes a local LLM to perform architecture extraction at frontier-model quality.

**How it works:**

1. A **surrogate model** (local LLM via Ollama) generates architecture extractions from code
2. An **oracle** (frontier model via litellm) scores each extraction against ground truth
3. A **multi-objective evaluator** computes loss across dimensions and maintains a Pareto front
4. **LoRA fine-tuning** adapts the surrogate's weights toward oracle-quality outputs
5. The loop iterates until the surrogate converges or a budget is exhausted

Key components:

| Module | Role |
|--------|------|
| `surrogate.py` | Local LLM client (Ollama integration) |
| `oracle.py` | Frontier model client (litellm) |
| `pipeline.py` | Training orchestrator |
| `evaluator.py` | Multi-objective loss with Pareto front tracking |
| `lora_finetuner.py` | LoRA adapter training |
| `dataset.py` | Training data management |
| `checkpoint.py` | Model checkpoint persistence |

## Test-Guided Code Generation

Added in v0.3.0, the test-guided generation pipeline uses existing test suites as behavioral specifications to drive code generation with iterative refinement.

**Pipeline stages:**

1. **TestContractMiner** extracts behavioral contracts (expected inputs, outputs, exceptions) from test files
2. **CodeWriter** materializes generated code into testable package structures
3. **TestGuidedGenerator** runs a generate-test-analyze-retry loop, feeding failure diagnostics back to the model
4. **FailureParser** provides structured pytest output parsing to identify root causes

The pipeline supports Copilot-relay integration for frontier model code generation alongside local model execution.

**Proof-of-concept results:** 33.3% test pass rate on the python-dotenv package, a 3x improvement over local model baseline.

Key modules:

| Module | Role |
|--------|------|
| `test_guided_generator.py` | Generate --> test --> analyze --> retry loop |
| `test_contract_miner.py` | Behavioral contract extraction from test suites |
| `failure_parser.py` | Structured pytest output parsing |
| `code_writer.py` | Package materializer for generated code |

## Package Structure

```
src/architecture_model/
├── cli/          — CLI commands (init, extract, validate, slice, diff, query, context, stats, impact, generate)
├── config/       — Configuration loading, auto-discovery, schema definition
├── core/         — Parser, validator, slicer, differ, merger, decomposer, type system
├── extract/      — Extract model from generated Tier 1 artifacts
├── integrations/ — LLM context formatting, pipeline bridge
├── manifest/     — Reality Manifest generator (AST scanning, metrics, blocks, interfaces)
├── spec/         — JSON Schema for model validation
└── training/     — MPC training loop (39 modules, 10.6K lines)
    ├── surrogate.py        — Local LLM client (Ollama)
    ├── oracle.py           — Frontier model client (litellm)
    ├── pipeline.py         — Training orchestrator
    ├── evaluator.py        — Multi-objective loss with Pareto front
    ├── test_guided_generator.py — Generate --> test --> retry loop
    ├── test_contract_miner.py   — Behavioral contract extraction
    ├── failure_parser.py   — Structured pytest output parsing
    ├── code_writer.py      — Package materializer
    └── ... (31 more modules)
```

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Specification](docs/specification.md) — Full schema specification (entity types, relationship types, validation rules, YAML format conventions)
- [LLM Protocol](docs/llm-protocol.md) — Integration protocol (6 verbs, slicing strategy, token budget management, integration patterns)

## Development

Install in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

Run the full test suite:

```bash
pytest
```

Run only training module tests:

```bash
pytest tests/training/
```

## Status

| Item | Value |
|------|-------|
| Schema version | 1.3 |
| Package version | 0.3.0 |
| Python | 3.10+ |
| Test suite | 904+ tests passing |
| Training tests | 619 tests (42 files, 12,048 lines) |
| Training source | 39 files, 10,662 lines |
| Entity types | 7 |
| Relationship types | 8 |
| LLM protocol verbs | 6 |
| CLI commands | 10 |
