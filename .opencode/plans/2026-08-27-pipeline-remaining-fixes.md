# Pipeline Remaining Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three remaining pipeline weaknesses: layer keyword leakage (per-file voting), generic capability naming for large repos, and adaptive similarity threshold in the diff engine.

**Architecture:** Task 1 replaces concatenated-path layer detection with per-file voting. Task 2 enhances `_infer_capabilities_by_package()` to derive meaningful names from sub-package structure and dominant module themes. Task 3 makes the gap analysis diff engine's similarity threshold adaptive based on entity count.

**Tech Stack:** Python, pytest, `difflib.SequenceMatcher`

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp/`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
**Pre-existing failures (7):** `test_includes_confidence`, `test_includes_components`, `test_real_logs_db`, `test_name_version_requires`, `test_schema_json_has_all_relationship_types`, plus 2 manifest test failures. Baseline: **7 failed, 1529 passed, 98 skipped**.

---

### Task 1: Per-file layer voting in `_infer_layer()`

**Problem:** `_infer_layer()` at `src/architecture_model/pipeline/allocate.py:475-488` concatenates ALL file paths into one string and matches keywords. One file with "handler" or "view" in its path infects the entire component's layer. For example, `src/architecture_model/cli/handler.py` makes a 16-component allocation all get `web` layer.

**Files:**
- Modify: `src/architecture_model/pipeline/allocate.py:475-488`
- Test: `tests/test_pipeline_allocate.py` (TestInferLayerEnhancements class, lines 92-112)

**Step 1: Write the failing tests**

Add to `tests/test_pipeline_allocate.py` in the `TestInferLayerEnhancements` class:

```python
def test_one_handler_file_does_not_infect_layer(self):
    """One file with 'handler' should not make the whole component 'web'."""
    files = [
        Path("src/mylib/core/parser.py"),
        Path("src/mylib/core/types.py"),
        Path("src/mylib/core/validator.py"),
        Path("src/mylib/core/handler.py"),  # only 1 of 4
    ]
    result = _infer_layer(files, "library")
    # Majority of files are core-like, not web
    assert result != "web"

def test_majority_web_files_get_web_layer(self):
    """When most files ARE web-related, should get web layer."""
    files = [
        Path("src/app/api/routes.py"),
        Path("src/app/api/views.py"),
        Path("src/app/api/handlers.py"),
        Path("src/app/api/utils.py"),  # only 1 non-web
    ]
    result = _infer_layer(files, "web_app")
    assert result == "web"

def test_single_file_uses_direct_match(self):
    """Single file should use direct keyword match."""
    files = [Path("src/app/handler.py")]
    result = _infer_layer(files, "web_app")
    assert result == "web"
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_allocate.py::TestInferLayerEnhancements -v`
Expected: `test_one_handler_file_does_not_infect_layer` FAILS (currently returns "web" because concatenated match)

**Step 3: Implement per-file voting**

Replace `_infer_layer()` in `src/architecture_model/pipeline/allocate.py:475-488`:

```python
_LAYER_KEYWORDS: dict[str, list[str]] = {
    "web": ["api", "route", "view", "handler", "endpoint"],
    "data": ["model", "schema", "db", "repository", "migration"],
    "service": ["service", "usecase", "domain", "logic"],
    "core": ["core", "engine", "kernel"],
    "infra": ["util", "helper", "common", "compat"],
}


def _infer_layer(files: list[Path], project_type: str = "library") -> str:
    """Guess architectural layer from file paths using per-file majority voting."""
    default = "library" if project_type == "library" else "infra"
    if not files:
        return default

    votes: dict[str, int] = {}
    for f in files:
        path_str = str(f).lower()
        matched = False
        for layer, keywords in _LAYER_KEYWORDS.items():
            if any(kw in path_str for kw in keywords):
                votes[layer] = votes.get(layer, 0) + 1
                matched = True
                break  # one vote per file
        if not matched:
            votes[default] = votes.get(default, 0) + 1

    if not votes:
        return default

    # Majority wins; tie-break by keyword priority order
    max_count = max(votes.values())
    for layer in _LAYER_KEYWORDS:
        if votes.get(layer, 0) == max_count:
            return layer
    return default
```

**Step 4: Run tests to verify they pass**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_allocate.py::TestInferLayerEnhancements -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py 2>&1 | tail -5`
Expected: 1529+ passed, 7 failed (pre-existing only)

**Step 6: Commit**

```bash
git add src/architecture_model/pipeline/allocate.py tests/test_pipeline_allocate.py
git commit -m "fix(pipeline): per-file layer voting prevents keyword leakage from single files"
```

---

### Task 2: Meaningful capability names for large repos

**Problem:** `_infer_capabilities_by_package()` at `src/architecture_model/pipeline/infer.py:420-466` groups modules by top-level package dir, producing names like "Scripts" and "Src" that are too generic. For large repos (>50 source modules), capability names should derive from sub-package structure.

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py:420-466`
- Test: `tests/test_pipeline_infer.py`

**Step 1: Write the failing tests**

Add a new test class to `tests/test_pipeline_infer.py`:

```python
class TestInferCapabilitiesByPackageNaming:
    """Tests for meaningful capability naming in large repos."""

    def test_subpackage_names_used_over_toplevel(self):
        """Sub-package names should be preferred over top-level 'src'."""
        modules = []
        # Create modules under src/myapp/core/ and src/myapp/api/
        for i in range(4):
            modules.append(_make_module(
                f"src/myapp/core/mod{i}.py",
                funcs=[f"func{j}" for j in range(3)],
            ))
        for i in range(4):
            modules.append(_make_module(
                f"src/myapp/api/mod{i}.py",
                funcs=[f"func{j}" for j in range(3)],
            ))
        result = _infer_capabilities_by_package(modules, set())
        names = {cap.name for cap in result}
        # Should NOT contain generic "Src" or "Myapp"
        assert "Src" not in names
        assert "Myapp" not in names
        # Should contain meaningful sub-package names
        assert any("Core" in n for n in names)
        assert any("Api" in n for n in names)

    def test_single_package_uses_dominant_module_theme(self):
        """When all modules are in one package, use module stem themes."""
        modules = [
            _make_module("src/myapp/parser.py", funcs=["parse_a", "parse_b", "parse_c"]),
            _make_module("src/myapp/tokenizer.py", funcs=["tokenize_a", "tokenize_b", "tokenize_c"]),
            _make_module("src/myapp/formatter.py", funcs=["format_a", "format_b", "format_c"]),
        ]
        result = _infer_capabilities_by_package(modules, set())
        # Should have at least one capability, not named "Myapp"
        assert len(result) >= 1
        names = {cap.name for cap in result}
        assert "Myapp" not in names
```

Note: `_make_module` helper likely already exists in test_pipeline_infer.py — use the existing one or create one that returns a `ModuleRecord` with the needed fields.

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_infer.py::TestInferCapabilitiesByPackageNaming -v`
Expected: FAIL — current implementation produces "Src" or "Myapp"

**Step 3: Implement improved naming**

Modify `_infer_capabilities_by_package()` in `src/architecture_model/pipeline/infer.py`:

Key changes:
1. After grouping by top-level package, if the group name is generic (common prefixes like "src", "lib", "app", single-char), re-group by the NEXT directory level
2. If still generic, use the most common module stem as capability name
3. Strip common project prefixes (the project name itself)

```python
_GENERIC_PACKAGE_NAMES = {"src", "lib", "app", "pkg", "source", "sources", "code"}


def _infer_capabilities_by_package(
    source_modules: list[ModuleRecord],
    existing_names: set[str],
) -> list[InferredCapability]:
    """Group large repos by package, using deepest meaningful directory name."""
    # Find common prefix to strip
    all_parts = [Path(m.path).parts for m in source_modules]
    prefix_len = 0
    if all_parts:
        for i in range(min(len(p) for p in all_parts)):
            vals = {p[i] for p in all_parts}
            if len(vals) == 1:
                prefix_len = i + 1
            else:
                break

    # Group by first meaningful directory after prefix
    groups: dict[str, list[ModuleRecord]] = {}
    for mod in source_modules:
        parts = Path(mod.path).parts[prefix_len:]
        # Find first non-generic part
        group_name = "(root)"
        for part in parts[:-1]:  # skip filename
            if part.lower() not in _GENERIC_PACKAGE_NAMES and len(part) > 1:
                group_name = part
                break
        if group_name == "(root)" and len(parts) > 1:
            # Use the directory just above the file
            group_name = parts[-2] if len(parts) >= 2 else parts[0]
        groups.setdefault(group_name, []).append(mod)

    # If everything ended up in (root), fall back to module stem naming
    if len(groups) == 1 and "(root)" in groups:
        # One cap per module that meets thresholds
        caps = []
        for mod in groups["(root)"]:
            stem = Path(mod.path).stem
            name = stem.lstrip("_").replace("_", " ").title()
            if name not in existing_names:
                caps.append(InferredCapability(
                    name=name,
                    module_sources=[mod.path],
                    origin="domain_module",
                ))
                existing_names.add(name)
        return caps

    # Build capabilities from groups
    caps: list[InferredCapability] = []
    for group_name, mods in sorted(groups.items()):
        if group_name == "(root)" and len(mods) < 3:
            continue
        name = group_name.lstrip("_").replace("_", " ").title()
        if name in existing_names:
            continue
        caps.append(InferredCapability(
            name=name,
            module_sources=[m.path for m in mods],
            origin="package_grouping",
        ))
        existing_names.add(name)
    return caps
```

**Step 4: Run tests to verify they pass**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_infer.py::TestInferCapabilitiesByPackageNaming -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py 2>&1 | tail -5`
Expected: 1529+ passed, 7 failed (pre-existing only)

**Step 6: Commit**

```bash
git add src/architecture_model/pipeline/infer.py tests/test_pipeline_infer.py
git commit -m "feat(pipeline): meaningful capability names for large repos via sub-package grouping"
```

---

### Task 3: Adaptive similarity threshold in gap analysis diff engine

**Problem:** `diff_stage_outputs()` in `src/architecture_model/pipeline/gap_analysis.py:180-204` uses a fixed `0.3` similarity threshold for name matching. On large repos with many entities, this produces false matches (e.g., "Create Llm Callback" ↔ "Cross-Repo Consistency Check" at 0.38).

**Files:**
- Modify: `src/architecture_model/pipeline/gap_analysis.py:143-227`
- Test: `tests/test_gap_analysis.py`

**Step 1: Write the failing tests**

Add to `tests/test_gap_analysis.py`:

```python
def test_adaptive_threshold_large_entity_count():
    """Large entity counts should use higher similarity threshold."""
    # With many entities, 0.38 similarity should NOT match
    det = [{"id": f"C-{i}", "name": f"Component {i}"} for i in range(50)]
    det.append({"id": "C-special", "name": "Create Llm Callback"})
    llm = [{"id": f"L-{i}", "name": f"Capability {i}"} for i in range(50)]
    llm.append({"id": "L-special", "name": "Cross-Repo Consistency Check"})

    result = diff_stage_outputs(det, llm, "capabilities")
    # These should NOT be matched — similarity is only ~0.38
    renamed_names = {r["det_name"] for r in result.get("renamed", [])}
    assert "Create Llm Callback" not in renamed_names

def test_adaptive_threshold_small_entity_count():
    """Small entity counts should still match at lower similarity."""
    det = [{"id": "C-1", "name": "Parser"}]
    llm = [{"id": "L-1", "name": "Parsing"}]
    result = diff_stage_outputs(det, llm, "capabilities")
    # These SHOULD match — small set, reasonable similarity
    assert len(result.get("renamed", [])) == 1 or len(result.get("removed", [])) == 0
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_analysis.py::test_adaptive_threshold_large_entity_count -v`
Expected: FAIL — currently matches at 0.3 threshold regardless of entity count

**Step 3: Implement adaptive threshold**

In `src/architecture_model/pipeline/gap_analysis.py`, modify the name-similarity fallback section (around lines 180-204):

```python
def _adaptive_threshold(entity_count: int) -> float:
    """Higher threshold for larger entity sets to reduce false matches."""
    if entity_count <= 10:
        return 0.30
    if entity_count <= 30:
        return 0.40
    return 0.50


def diff_stage_outputs(...):
    # ... existing ID-matching code ...

    # Name-similarity fallback for unmatched
    total_entities = len(det_entities) + len(llm_entities)
    threshold = _adaptive_threshold(total_entities)

    # Replace hardcoded 0.3 with `threshold` in the matching loop
    # ...
```

**Step 4: Run tests to verify they pass**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_analysis.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py 2>&1 | tail -5`
Expected: 1529+ passed, 7 failed (pre-existing only)

**Step 6: Commit**

```bash
git add src/architecture_model/pipeline/gap_analysis.py tests/test_gap_analysis.py
git commit -m "fix(pipeline): adaptive similarity threshold in diff engine reduces false matches on large repos"
```

---

### Task 4: Push all commits

**Step 1: Push**

```bash
git -c http.proxy="" push <remote-with-credentials> feature/model-quality-16wp
```

---

### Task 5 (optional): E2E validation on self-analysis

After all 3 fixes, re-run the gap analysis on the repo itself to verify improvements:

```bash
/opt/anaconda3/bin/python -m architecture_model pipeline . --gap-analysis
```

Expected: Layer assignments should no longer show 14/16 components as "web". Capability names should be more meaningful than "Scripts"/"Src".
