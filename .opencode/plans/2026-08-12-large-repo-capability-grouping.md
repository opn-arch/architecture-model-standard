# Large Repo Capability Grouping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the infer and allocate stages to produce sensible capabilities and components for large repos (100+ modules), where the current per-module strategy creates 150+ capabilities instead of ~15-20.

**Architecture:** Add a package-hierarchy grouping strategy to the infer stage that activates for repos with >50 source modules. Instead of one capability per domain module, group modules by their top-level package (e.g., `django/db/**` → "Database" capability). The allocate stage's split logic also needs adjustment: when splitting oversized components, use 2-level directory grouping instead of leaf-directory splitting, to avoid fragmenting coherent packages.

**Tech Stack:** Python, pytest, architecture_model.pipeline

---

## Context

**The problem (Django case study):**
- 427 source modules → 157 capabilities (141 from domain_module strategy)
- 285 components, only 9 with ≥5 files → bad system decomposition
- Validate score: 15/100

**Desired outcome:**
- 427 source modules → ~15-25 capabilities (one per top-level package)
- ~15-25 components with meaningful file counts → good system decomposition
- Validate score: ≥70/100

**Key files:**
- `src/architecture_model/pipeline/infer.py` — capability inference (main fix)
- `src/architecture_model/pipeline/allocate.py` — component allocation (secondary fix)
- `tests/test_pipeline_stages.py` — pipeline stage tests

---

### Task 1: Add hierarchical capability grouping to infer stage

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py`
- Test: `tests/test_pipeline_stages.py`

**Step 1: Write the failing test**

Add a test that creates a large inventory (>50 modules) spread across multiple packages and verifies infer produces grouped capabilities.

```python
def test_infer_groups_by_package_for_large_repos():
    """Large repos (>50 modules) group capabilities by top-level package."""
    from architecture_model.pipeline.infer import InferStage
    from architecture_model.pipeline.observe_types import Inventory, ModuleRecord, FunctionRecord
    from architecture_model.pipeline.protocol import PipelineContext, StageResult

    # Create 60 modules across 4 packages
    modules = []
    for pkg in ["db", "core", "template", "forms"]:
        for i in range(15):
            modules.append(ModuleRecord(
                path=Path(f"src/myapp/{pkg}/mod_{i}.py"),
                imports=[],
                functions=[
                    FunctionRecord(name=f"func_{j}", line=j*10, is_async=False)
                    for j in range(5)
                ],
                classes=[],
            ))

    inventory = Inventory(modules=modules, edges=[], routes=[])
    ctx = PipelineContext(
        repo_path=Path("/tmp/test"),
        output_dir=Path("/tmp/test/.architecture/pipeline-cache"),
    )
    ctx.cache["observe"] = StageResult(
        output=inventory, quality=None, diagnostics=[], uncertainties=[]
    )

    stage = InferStage()
    result = stage.run(ctx)

    caps = result.output.capabilities
    # Should produce ~4 capabilities (one per package), not 60
    assert len(caps) <= 10, f"Expected <=10 caps for 4 packages, got {len(caps)}"
    assert len(caps) >= 3, f"Expected >=3 caps, got {len(caps)}"
    # Capability names should reference packages
    cap_names = [c.name.lower() for c in caps]
    assert any("db" in n for n in cap_names), f"Expected a DB capability, got {cap_names}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_stages.py::test_infer_groups_by_package_for_large_repos -v`
Expected: FAIL (currently produces 60 capabilities)

**Step 3: Implement package-hierarchy grouping**

In `infer.py`, modify `_infer_from_domain_modules()`:

- Add `_LARGE_REPO_MODULE_THRESHOLD = 50` constant
- When `len(source_modules) > threshold` and not scoped, call new `_infer_capabilities_by_package()`
- `_infer_capabilities_by_package()`: find common path prefix, group by first diverging directory, create one capability per group
- Keep original per-module logic for small repos and scoped contexts

Key implementation of `_infer_capabilities_by_package()`:
1. Find common prefix of all module paths
2. Group modules by the directory immediately after common prefix
3. Create one `InferredCapability` per group with `evidence_source="package_group"`
4. Skip "(root)" groups with <3 modules

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline_stages.py::test_infer_groups_by_package_for_large_repos -v`
Expected: PASS

**Step 5: Run full test suite for regressions**

Run: `pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: All existing tests pass (small repos still use per-module strategy)

**Step 6: Commit**

```bash
git add src/architecture_model/pipeline/infer.py tests/test_pipeline_stages.py
git commit -m "feat(infer): add package-hierarchy grouping for large repos (>50 modules)"
```

---

### Task 2: Fix allocate split logic for package-coherent components

**Files:**
- Modify: `src/architecture_model/pipeline/allocate.py`
- Test: `tests/test_pipeline_stages.py`

**Step 1: Write the failing test**

```python
def test_allocate_splits_by_package_not_leaf_dir():
    """When splitting oversized components, group by sub-package, not leaf dir."""
    from architecture_model.pipeline.allocate import _split_oversized
    from architecture_model.pipeline.allocate_types import ComponentAllocation

    # Component with 18 files across 3 sub-packages, each with 2 sub-dirs
    files = []
    for subpkg in ["models", "backends", "sql"]:
        for subdir in ["a", "b"]:
            for i in range(3):
                files.append(Path(f"django/db/{subpkg}/{subdir}/f{i}.py"))

    comp = ComponentAllocation(id="COMP-1", name="Db", files=files, layer="data")
    result = _split_oversized([comp])
    # Should split into ~3 components (by subpkg), not 6 (by leaf dir)
    assert len(result) <= 4, f"Expected <=4 splits, got {len(result)}"
    assert len(result) >= 2, f"Expected >=2 splits, got {len(result)}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_stages.py::test_allocate_splits_by_package_not_leaf_dir -v`
Expected: FAIL (current splits by leaf dir → 6 components)

**Step 3: Implement package-level splitting**

Replace `_split_oversized()` to use `_group_by_package_level()`:
1. Find common prefix of all files in the component
2. Group by first directory after common prefix
3. Create sub-components per group

**Step 4: Run test + full suite**

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/allocate.py tests/test_pipeline_stages.py
git commit -m "feat(allocate): use package-level splitting instead of leaf-directory"
```

---

### Task 3: Integration test with Django-like structure

**Files:**
- Test: `tests/test_pipeline_stages.py`

Write an end-to-end test that creates a ~90-module repo (6 packages × 15 modules), runs observe → infer → allocate → relate → decompose, and asserts:
- `len(caps) <= 20`
- `len(comps) <= 20`
- `len(systems) >= 3`

Commit: `git commit -m "test: add integration test for large repo capability grouping"`

---

### Task 4: Re-extract Django with scoped enrichment

**Operational task (not code):**

1. Clear Django cache: `architect_pipeline(django_path, stage="observe", clear_cache=true)`
2. Run stages observe → validate with LLM enrichment
3. At decompose, verify systems match Django's actual architecture (~10 systems: db, core, template, forms, views, http, urls, utils, middleware, management)
4. Run scoped sub-pipelines for each detected system
5. Run synthesize + emit
6. Evaluate validate score (target: ≥70)

---

### Task 5: Evaluate model quality for SE rigor

**Criteria:**

| Metric | Target | Method |
|--------|--------|--------|
| Capabilities match human SE | ≥80% overlap with Django docs | Manual review |
| Boundary coherence | ≥60% | allocate quality sub_scores |
| System decomposition | Matches Django's major subsystems | Compare to known architecture |
| Validate score | ≥70/100 | validate output |
| Enrichment quality | body_hints + test_contracts present | `architecture-model enrich` |

**Expected Django systems (what a human SE would model):**

| System | Key Components |
|--------|---------------|
| ORM (db) | models, sql, backends, migrations |
| Templates | engine, loaders, tags, filters |
| Forms | forms, fields, widgets, formsets |
| HTTP Layer | request, response, middleware, sessions |
| URL Routing | urls, resolvers, converters |
| Core | settings, signals, exceptions, serialization |
| Utils | encoding, crypto, functional, text |
| Management | CLI commands, management base |
| Views | generic views, class-based views |
| i18n/l10n | translation, locale formats |
