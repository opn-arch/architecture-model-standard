# Manifest-Enforced Interface Mapping — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure the architecture model's relationship graph faithfully reflects the manifest's import dependency structure via prompt hints and deterministic post-fill.

**Architecture:** Two-phase approach. Phase 1 adds a block-level dependency matrix to the oracle context summary so the LLM has structural guidance. Phase 2 adds a post-extraction `InterfaceEnforcer` that aggregates file-level imports to component-level edges using the module-component map, infers relationship types from import context, and injects missing relationships. Deduplication: skip component pairs that already have any relationship.

**Tech Stack:** Python dataclasses, `ManifestCoverageComputer._build_module_component_map()` for reuse, `collections.Counter` for aggregation.

**Test suite command:** `pytest --tb=short -q` (expect 409+ passed, 0 failed)

---

### Task 1: InterfaceEnforcer — Failing Tests

**Files:**
- Create: `tests/test_training/test_interface_enforcer.py`

**Step 1: Write the failing tests**

```python
"""Tests for manifest-enforced interface mapping."""

import pytest
from architecture_model.training.interface_enforcer import InterfaceEnforcer
from architecture_model.core.types import (
    ArchitectureModel, Entities, Component, Capability, Layer,
    Relationship, RelationType, Strength, Status, ModelMeta,
)


def _make_manifest():
    """Manifest with 3 modules and 2 import edges."""
    return {
        "modules": [
            {"file": "src/client.py", "name": "HTTP Client", "line_count": 200,
             "functions": ["get(url)", "post(url, data)", "connect()"],
             "imports": ["src/pool.py"], "status": "active"},
            {"file": "src/pool.py", "name": "Connection Pool", "line_count": 150,
             "functions": ["acquire()", "release()"],
             "imports": ["src/utils.py"], "status": "active"},
            {"file": "src/utils.py", "name": "Utilities", "line_count": 30,
             "functions": ["format_url(raw)"],
             "imports": [], "status": "active"},
        ],
        "interfaces": [
            {"source": "src/client.py", "target": "src/pool.py", "import_path": "pool"},
            {"source": "src/pool.py", "target": "src/utils.py", "import_path": "utils"},
        ],
        "functional_blocks": {},
    }


def _make_model_no_deps():
    """Model with 3 components in separate layers, NO relationships between them."""
    meta = ModelMeta(schema_version="1.0", project="test")
    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[],
            layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            components=[
                Component(id="C1", name="HTTP Client", layer="L1", status=Status.ACTIVE),
                Component(id="C2", name="Connection Pool", layer="L1", status=Status.ACTIVE),
                Component(id="C3", name="Utilities", layer="L1", status=Status.ACTIVE),
            ],
        ),
        relationships=[],
    )


def _make_model_partial_deps():
    """Model with one existing relationship, one missing."""
    meta = ModelMeta(schema_version="1.0", project="test")
    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[],
            layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            components=[
                Component(id="C1", name="HTTP Client", layer="L1", status=Status.ACTIVE),
                Component(id="C2", name="Connection Pool", layer="L1", status=Status.ACTIVE),
                Component(id="C3", name="Utilities", layer="L1", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            # C1→C2 already exists, but C2→C3 is missing
            Relationship(type=RelationType.CONSUMES, from_id="C1", to_id="C2"),
        ],
    )


class TestInterfaceEnforcer:
    def test_injects_missing_relationships(self):
        """Enforcer adds depends-on for all cross-component import edges."""
        manifest = _make_manifest()
        model = _make_model_no_deps()
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        # Should have added 2 relationships: C1→C2 and C2→C3
        assert len(result.relationships) == 2
        from_to = {(r.from_id, r.to_id) for r in result.relationships}
        assert ("C1", "C2") in from_to
        assert ("C2", "C3") in from_to

    def test_skips_existing_relationships(self):
        """Enforcer doesn't duplicate edges that already exist (any type)."""
        manifest = _make_manifest()
        model = _make_model_partial_deps()
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        # C1→C2 already exists as 'consumes', only C2→C3 should be added
        assert len(result.relationships) == 2
        # Original relationship preserved
        assert any(r.type == RelationType.CONSUMES and r.from_id == "C1" for r in result.relationships)
        # New one added
        assert any(r.from_id == "C2" and r.to_id == "C3" for r in result.relationships)

    def test_infers_consumes_for_api_functions(self):
        """Target with API-like functions (get, post, connect) → consumes."""
        manifest = {
            "modules": [
                {"file": "src/app.py", "name": "App", "line_count": 100,
                 "functions": ["main()"], "imports": ["src/api.py"], "status": "active"},
                {"file": "src/api.py", "name": "API Server", "line_count": 200,
                 "functions": ["get(path)", "post(path, body)", "subscribe(topic)"],
                 "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/app.py", "target": "src/api.py", "import_path": "api"},
            ],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[],
                components=[
                    Component(id="C1", name="App", layer="", status=Status.ACTIVE),
                    Component(id="C2", name="API Server", layer="", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        assert len(result.relationships) == 1
        assert result.relationships[0].type == RelationType.CONSUMES

    def test_strength_from_edge_count(self):
        """5+ import edges between components → strong strength."""
        manifest = {
            "modules": [
                {"file": f"src/a{i}.py", "name": f"A{i}", "line_count": 50,
                 "functions": [f"fn{i}()"], "imports": [f"src/b{i}.py"], "status": "active"}
                for i in range(6)
            ] + [
                {"file": f"src/b{i}.py", "name": f"B{i}", "line_count": 50,
                 "functions": [f"helper{i}()"], "imports": [], "status": "active"}
                for i in range(6)
            ],
            "interfaces": [
                {"source": f"src/a{i}.py", "target": f"src/b{i}.py", "import_path": f"b{i}"}
                for i in range(6)
            ],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[],
                components=[
                    Component(id="CA", name="Group A", layer="",
                              files=[f"src/a{i}.py" for i in range(6)],
                              status=Status.ACTIVE),
                    Component(id="CB", name="Group B", layer="",
                              files=[f"src/b{i}.py" for i in range(6)],
                              status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        assert len(result.relationships) == 1
        assert result.relationships[0].strength == Strength.STRONG

    def test_internal_edges_not_injected(self):
        """Import edges within the same component don't produce relationships."""
        manifest = {
            "modules": [
                {"file": "src/client/get.py", "name": "GET", "line_count": 50,
                 "functions": ["get()"], "imports": ["src/client/base.py"], "status": "active"},
                {"file": "src/client/base.py", "name": "Base", "line_count": 80,
                 "functions": ["request()"], "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client/get.py", "target": "src/client/base.py",
                 "import_path": "base"},
            ],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[],
                components=[
                    Component(id="C1", name="HTTP Client", layer="",
                              files=["src/client/get.py", "src/client/base.py"],
                              status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        assert len(result.relationships) == 0

    def test_empty_manifest_no_change(self):
        """Empty manifest interfaces → no relationships added."""
        manifest = {"modules": [], "interfaces": [], "functional_blocks": {}}
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[],
                components=[Component(id="C1", name="X", layer="", status=Status.ACTIVE)],
            ),
            relationships=[],
        )
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        assert len(result.relationships) == 0

    def test_bidirectional_imports_become_depends_on(self):
        """When A imports B AND B imports A, type is depends-on (mutual coupling)."""
        manifest = {
            "modules": [
                {"file": "src/a.py", "name": "Module A", "line_count": 100,
                 "functions": ["fn_a()"], "imports": ["src/b.py"], "status": "active"},
                {"file": "src/b.py", "name": "Module B", "line_count": 100,
                 "functions": ["fn_b()"], "imports": ["src/a.py"], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/a.py", "target": "src/b.py", "import_path": "b"},
                {"source": "src/b.py", "target": "src/a.py", "import_path": "a"},
            ],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[],
                components=[
                    Component(id="C1", name="Module A", layer="", status=Status.ACTIVE),
                    Component(id="C2", name="Module B", layer="", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        # Bidirectional → depends-on (mutual coupling)
        for rel in result.relationships:
            assert rel.type == RelationType.DEPENDS_ON

    def test_enforce_returns_summary(self):
        """enforce() returns an EnforcementResult with counts."""
        manifest = _make_manifest()
        model = _make_model_no_deps()
        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)
        assert result.added_count >= 2
        assert result.skipped_count == 0
        assert result.internal_count >= 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_training/test_interface_enforcer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'architecture_model.training.interface_enforcer'`

---

### Task 2: InterfaceEnforcer — Implementation

**Files:**
- Create: `src/architecture_model/training/interface_enforcer.py`

**Step 1: Implement InterfaceEnforcer**

The class must:
1. Reuse `ManifestCoverageComputer._build_module_component_map()` to map files to components
2. Aggregate file-level imports into component-level directed edges with counts
3. Build a file→module lookup to access target functions for type inference
4. For each cross-component edge where no relationship exists:
   - Infer type: `consumes` if target functions match API patterns, `depends-on` for bidirectional or default
   - Infer strength from edge count: 5+ strong, 2-4 moderate, 1 weak
   - Add the relationship
5. Return an `EnforcementResult` with the enriched model and stats

API pattern keywords for `consumes` inference (check target module function names):
`get`, `post`, `put`, `delete`, `send`, `receive`, `publish`, `subscribe`,
`emit`, `connect`, `request`, `fetch`, `query`, `execute`, `call`, `invoke`

**Step 2: Run tests**

Run: `pytest tests/test_training/test_interface_enforcer.py -v`
Expected: All 8 tests PASS

**Step 3: Run full suite**

Run: `pytest --tb=short -q`
Expected: 417+ passed, 0 failed

**Step 4: Commit**

```bash
git add src/architecture_model/training/interface_enforcer.py tests/test_training/test_interface_enforcer.py
git commit -m "feat(training): add InterfaceEnforcer for manifest-derived dependency injection"
```

---

### Task 3: Block-Level Dependency Matrix in Context

**Files:**
- Modify: `src/architecture_model/training/oracle_context.py:114-158` (`_format_manifest_summary`)

**Step 1: Write a test for the new context section**

Add to existing test file or create: `tests/test_training/test_oracle_context.py`

Add a test that verifies `_format_manifest_summary()` output contains a "Block-Level Dependencies" section when interfaces and blocks both exist.

**Step 2: Implement block-level dependency aggregation**

In `_format_manifest_summary()`, replace the "Dependency Hotspots" section (lines 149-156) with a block-level dependency matrix:

1. Build file→block mapping from `functional_blocks[*].sub_functions[*].file`
2. For each interface edge, look up source block and target block
3. Aggregate into `Counter[(source_block, target_block)]`
4. Classify strength: 10+ edges "strong", 5-9 "moderate", 1-4 "weak"
5. Render as sorted list: `- Internal -> Root: 45 edges (strong)`

Keep the hotspots section too (both are useful), but put block-level deps FIRST since it's the structural hint the LLM needs.

**Step 3: Run tests**

Run: `pytest tests/test_training/test_oracle_context.py -v`
Expected: All PASS (existing + new)

**Step 4: Run full suite**

Run: `pytest --tb=short -q`
Expected: 418+ passed, 0 failed

**Step 5: Commit**

```bash
git add src/architecture_model/training/oracle_context.py tests/test_training/test_oracle_context.py
git commit -m "feat(training): add block-level dependency matrix to oracle context summary"
```

---

### Task 4: Wire InterfaceEnforcer into Pipeline and Exports

**Files:**
- Modify: `src/architecture_model/training/pipeline.py:174-182` (after oracle extraction)
- Modify: `src/architecture_model/training/__init__.py` (add export)

**Step 1: Wire into pipeline**

In `_process_repo()`, after the oracle model is extracted and optionally refined by self-critique (line 182), add:

```python
from architecture_model.training.interface_enforcer import InterfaceEnforcer
# ... after self-critique refinement ...
enforcer = InterfaceEnforcer()
enforcement = enforcer.enforce(oracle_model, manifest)
oracle_model = enforcement.model
```

**Step 2: Add to `__init__.py` exports**

Add `InterfaceEnforcer` and `EnforcementResult` to imports and `__all__`.

**Step 3: Run full suite**

Run: `pytest --tb=short -q`
Expected: 418+ passed, 0 failed

**Step 4: Commit**

```bash
git add src/architecture_model/training/pipeline.py src/architecture_model/training/__init__.py
git commit -m "feat(training): wire InterfaceEnforcer into MPC pipeline after oracle extraction"
```

---

### Task 5: Update Test Script and Validate on Pydantic

**Files:**
- Modify: `scripts/test_oracle_learning.py`

**Step 1: Add enforcement step to test script**

After each model extraction (before coverage analysis), run the enforcer and show before/after:

```python
from architecture_model.training.interface_enforcer import InterfaceEnforcer

enforcer = InterfaceEnforcer()
# After extraction:
enforcement = enforcer.enforce(model, manifest)
print(f"   Interface enforcement: +{enforcement.added_count} rels, "
      f"{enforcement.skipped_count} skipped, {enforcement.internal_count} internal")
model = enforcement.model
```

**Step 2: Run on pydantic**

Run: `python scripts/test_oracle_learning.py /tmp/test-repos/pydantic`

Expected: Interface coverage should jump from ~6% to ~80-90%. Overall coverage should exceed 85%.

**Step 3: Commit**

```bash
git add scripts/test_oracle_learning.py
git commit -m "feat(training): add interface enforcement to oracle test script"
```
