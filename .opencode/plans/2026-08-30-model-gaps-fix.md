# Fix Model Gaps: Systems in Diagrams, L2 Capability Mappings, Behavior Flows

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make systems visible in high-level diagrams, add `realizes` relationships for L2 capabilities, and show full-depth behavior hierarchy.

**Architecture:** Three-pronged fix: (1) add ~78 `realizes` relationships to YAML model for L2 capabilities using manifest-based smart inference, (2) update 3 diagram generators to include system groupings and full behavior depth, (3) regenerate viewer.

**Tech Stack:** Python, YAML model editing, Mermaid diagram generation

---

### Task 1: Smart-infer L2 capability `realizes` relationships

**Files:**
- Modify: `.architecture-model.yaml` (add relationships)

**Approach:**
1. Load model + generate manifest
2. For each L2 cap (CAP-N.X), find the component realizing parent CAP-N
3. If that component has children (COMP-M.Y), match L2 cap name keywords against child component file functions/classes
4. If match found → L2 realized by child. Otherwise → L2 realized by parent component
5. Append new `realizes` relationships to YAML

**Verify:** `generate_entity_explorer(model, 'capability', 'CAP-1.1')` should return non-empty facets with "Components" key.

---

### Task 2: Add systems to Logical Architecture diagram

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `generate_logical_architecture_diagram()` (line 934)
- Test: `tests/test_se_diagrams.py`

**Change:** Group components by system (using `sys.component_ids`) as outer subgraphs, then by layer within each system. Unassigned components in "Other" subgraph.

---

### Task 3: Add systems to ConOps diagram

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `generate_conops_diagram()` (line 784)
- Test: `tests/test_se_diagrams.py`

**Change:** Add system nodes between actors and capabilities. Actors → systems → L1 capabilities (systems as intermediary showing which capabilities they provide).

---

### Task 4: Full-depth behavior hierarchy in overview

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `generate_behavior_overview_diagram()` (line 985)
- Test: `tests/test_se_diagrams.py`

**Change:** Show all behavior levels using nested subgraphs. BEH-P1 subgraph contains BEH-P1.1..BEH-P1.R nodes, each of which contains their children. Show `contains` as dotted lines, `triggers` as solid.

---

### Task 5: Run full test suite, regenerate viewer, push

Expected baseline: 7 pre-existing failures, ~1755+ passed
