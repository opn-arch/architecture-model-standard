# Pipeline Quality + Live Artifacts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise benchmark extraction scores +6-10 pts on arbitrary repos and keep core SE artifacts live-regenerated with regen readiness as quality signal.

**Architecture:** Three workstreams — (1) pipeline quality improvements in architecture-model-standard (hierarchy decompose, capability fallback, USES relationships), (2) live artifact regeneration triggered from extract/pipeline, (3) regen readiness surfaced in slice/gate/health for both human and AI consumers.

**Tech Stack:** Python dataclasses, YAML, pytest, no LLM required (all deterministic)

---

## Task 1: Hierarchical Decompose Stage

**Files:**
- Modify: `src/architecture_model/pipeline/decompose.py`
- Test: `tests/test_pipeline_decompose.py`

**What:** When a component has ≥8 files, cluster by import affinity into sub-components. Set `parent_id` on children, `children` on parent. Add `contains` relationships.

**Current behavior:** Components with ≥5 files become "systems" (flat). No nesting.
**New behavior:** Components with ≥8 files get sub-components using import clustering. Parent retains the __init__.py, children get the clustered files.

---

## Task 2: Fallback Capability Inference for Library Repos

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py`
- Test: `tests/test_pipeline_infer.py`

**What:** If no capabilities found via routes/triggers/CLI, fall back to treating each top-level package with >3 public functions as a capability.

**Current behavior:** Library repos with no routes/CLI/triggers produce 0 capabilities → 0 realizes edges → orphan warnings.
**New behavior:** Minimum 1 capability per repo guaranteed.

---

## Task 3: USES Relationship for Utility-Layer Imports

**Files:**
- Modify: `src/architecture_model/pipeline/relate.py`
- Test: `tests/test_pipeline_relate.py`

**What:** If target component's layer is "infrastructure" or "utility" or name matches common utility patterns (utils, helpers, common, shared), use `USES` instead of `depends-on`.

---

## Task 4: Live Artifact Regeneration Flag

**Files:**
- Modify: `src/architecture_model/docs/generator.py`
- Modify: `src/architecture_model/cli/main.py`

**What:** Add `live_only=True` parameter to `generate_docs()` that only regenerates: health, functional-analysis, logical-architecture, dependency-matrix, component-specs. Add `--live` CLI flag.

---

## Task 5: Auto-Regen After Extract and Pipeline

**Files:**
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/extract.py`
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/pipeline.py`

**What:** After successful model store (extract) or pipeline emit, auto-regenerate live artifacts. Non-fatal — wrapped in try/except.

---

## Task 6: Regen Score in Health Report

**Files:**
- Modify: `src/architecture_model/docs/health.py`

**What:** Add per-component regen readiness grade (A-F) to health report. Traffic-light visualization.

---

## Task 7: Regen Grade in architect_slice Header

**Files:**
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/slice.py`

**What:** Add `Regen: B (72%)` line to slice output header so AI sees quality immediately.

---

## Task 8: Gate Recommendation for Low Regen

**Files:**
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/gate.py`

**What:** If overall regen score < 50 (grade D/F), add recommendation: "Consider running enrichment before proceeding — model lacks detail for reliable code generation."

---

## Task 9: Requirements in Model + Live Doc

**Files:**
- Modify: architecture-model-standard `.architecture-model.yaml` (add top-level requirements)
- Modify: `src/architecture_model/docs/se/requirements_analysis.py` (generate from model.entities.requirements)

**What:** Add 30-40 key requirements to model entities, generate hierarchical requirements doc from them.

---
