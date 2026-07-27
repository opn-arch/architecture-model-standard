# Fix Decompose — Relationship Tracing + F-block Alignment

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make sub-models 100% representative by tracing parent model relationships instead of inventing entities, and align f_block numbering with config.

**Architecture:** Decompose traces `realizes`, `exposes`, `traces-to`, `constrained-by` from block components to pull in existing parent entities. F-block IDs on capabilities/components are renumbered to match config's directory-based block IDs.

**Tech Stack:** Python 3.11+, dataclasses, YAML, pytest

---

### Task 1: Fix parent model f_block numbering + add F9

**Files:**
- Modify: `.architecture-model.yaml`

**What it does:**
- Renumber capability f_block fields to match config F-block IDs:
  - CAP-F1 "Parsing" → f_block=F3 (Core)
  - CAP-F2 "Manifest" → f_block=F5
  - CAP-F4 "CLI" → f_block=F1
  - CAP-F5 "Config" → f_block=F2
  - CAP-F6 "Schema" → f_block=F7
  - CAP-F7 "Extraction" → f_block=F4
  - CAP-F8 "Profiles" → f_block=F6
  - CAP-F9 "Utils" → f_block=F8
  - CAP-F10 "Enrichment" → f_block=F9
- Set f_block on ALL components based on file path matching
- Add COMP-ENRICH f_block=F9, COMP-DECOMPOSE f_block=F9 (new Orchestration block)
- Add decompose.py to components if not present

### Task 2: Rewrite decompose with relationship tracing

**Files:**
- Modify: `src/architecture_model/decompose.py`
- Modify: `tests/test_decompose.py`

**What it does:**
Replace `_derive_capabilities()` and `_derive_interfaces()` with relationship tracing:

For each config F-block:
1. Find block components (by file path match) — KEEP
2. Find parent component (by contains) — KEEP
3. Trace outward from ALL block component IDs:
   - `realizes` → pull in Capability
   - `exposes` → pull in Interface
   - `traces-to` → pull in Behavior
   - `constrained-by` → pull in Constraint
4. Collect ALL relationships where both endpoints are in the entity set
5. Include cross-block `depends-on` as boundary relationships
6. Build sub-model with parent's actual entities (not invented ones)
7. Optionally layer manifest-derived intra-block import interfaces

### Task 3: Add F9 Orchestration to config + regenerate

**Files:**
- Modify: `.architecture-model.yaml` (if not done in Task 1)

**What it does:**
- Ensure enrich.py and decompose.py are mapped to F9
- Regenerate recursive manifests (now with F9)
- Regenerate sub-models
- Verify: union of all sub-model entities ≈ parent model entities

### Task 4: Verify + commit

**What it does:**
- Run full test suite
- Check each sub-model has parent capabilities, interfaces, behaviors, constraints
- Regenerate PDFs
- Commit

---
