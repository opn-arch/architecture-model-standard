# Pipeline Precision Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 6 pipeline weaknesses exposed by colorama gap analysis to achieve near-perfect deterministic modeling across all repo types (web apps, CLI tools, libraries).

**Architecture:** Each fix is a targeted change to one pipeline stage, with an LLM QA layer added as a cross-cutting concern. Fixes are ordered by dependency: relationship serialization bug first (unblocks everything), then diff engine (unblocks accurate gap analysis), then the 4 pipeline stage improvements (infer, allocate, specify, contract).

**Tech Stack:** Python 3.12, dataclasses, AST, SequenceMatcher, asyncio for LLM callbacks

**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

**Baseline:** 7 failed (pre-existing), 1500 passed, 98 skipped

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp/`

---

## Task 1: Fix relationship type serialization bug

**Files:**
- Modify: `src/architecture_model/pipeline/gap_analysis.py:104-112`
- Modify: `src/architecture_model/pipeline/stage_tracer.py:255`
- Test: `tests/test_gap_analysis.py`

**Problem:** `DerivedRelationship` has field `rel_type` (not `type`). `extract_stage_data("relate")` reads `getattr(r, "type", None)` → always `None`. This cascades to stage_tracer rendering `"COMP-1 None CAP-1"`.

**Step 1: Write failing test**

```python
def test_extract_stage_data_relate_has_type():
    """Relationship type must be extracted (not None)."""
    from architecture_model.pipeline.gap_analysis import extract_stage_data

    class FakeRel:
        from_id = "COMP-1"
        to_id = "CAP-1"
        rel_type = "realizes"

    class FakeOutput:
        relationships = [FakeRel()]

    data = extract_stage_data("relate", FakeOutput())
    assert data["relationships"][0]["type"] == "realizes"
```

**Step 2: Run test — expect FAIL** (currently returns `None`)

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_analysis.py::test_extract_stage_data_relate_has_type -v`

**Step 3: Fix `extract_stage_data`**

In `gap_analysis.py`, line 110, change:
```python
# OLD
"type": getattr(r, "type", None),
# NEW
"type": getattr(r, "rel_type", None) or getattr(r, "type", None),
```

**Step 4: Fix `stage_tracer.py` to handle None type gracefully**

In `stage_tracer.py`, line 255, change:
```python
# OLD
rtype = rel.get("type", "")
# NEW
rtype = rel.get("type") or ""
```

**Step 5: Run test — expect PASS**

**Step 6: Run full test suite — expect baseline**

**Step 7: Commit**
```
fix(pipeline): extract rel_type from DerivedRelationship in gap analysis
```

---

## Task 2: Diff engine name-similarity fallback

**Files:**
- Modify: `src/architecture_model/pipeline/gap_analysis.py:142-189`
- Test: `tests/test_gap_analysis.py`

**Problem:** LLM entities have no `id` field, so ID-matching finds nothing. All LLM entities go to `added`, all pipeline entities go to `removed`, and `renamed` is always empty. We need name-similarity matching for unmatched entities.

**Step 1: Write failing tests**

```python
def test_diff_matches_by_name_similarity():
    """Entities without IDs should match by name similarity."""
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs

    det = {"capabilities": [
        {"id": "CAP-1", "name": "Ansitowin32"},
        {"id": "CAP-2", "name": "Ansi"},
    ]}
    llm = {"capabilities": [
        {"name": "ANSI-to-Win32 Conversion"},  # no id, but similar name
        {"name": "ANSI Code Generation"},       # no id, similar to "Ansi"
    ]}
    gap = diff_stage_outputs("infer", det, llm)
    # Should match by name similarity, not leave as added/removed
    assert len(gap.renamed) == 2
    assert len(gap.added) == 0
    assert len(gap.removed) == 0


def test_diff_name_match_threshold():
    """Names below similarity threshold stay as added/removed."""
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs

    det = {"capabilities": [{"id": "CAP-1", "name": "Parser"}]}
    llm = {"capabilities": [{"name": "Completely Unrelated Widget"}]}
    gap = diff_stage_outputs("infer", det, llm)
    assert len(gap.renamed) == 0
    assert len(gap.added) == 1
    assert len(gap.removed) == 1
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement name-similarity fallback**

After ID-matching (line 172), before building added/removed lists, add a second pass that matches remaining entities by name similarity. Use greedy best-match with threshold 0.3 (low threshold because pipeline names like "Ansi" vs LLM names like "ANSI Code Generation" are very different but semantically related). Also try substring matching (if one name contains the other).

```python
# After ID matching, before building added/removed:
# --- Name-similarity fallback for entities without matching IDs ---
unmatched_det = {eid: e for eid, e in det_by_id.items() if eid not in matched_det_ids}
unmatched_llm_no_id = [e for e in llm_list if isinstance(e, dict) and not e.get("id")]
unmatched_llm_with_id = {eid: e for eid, e in llm_by_id.items() if eid not in matched_llm_ids}

# Combine all unmatched LLM entities
all_unmatched_llm = list(unmatched_llm_with_id.values()) + unmatched_llm_no_id

if unmatched_det and all_unmatched_llm:
    used_llm: set[int] = set()
    for det_id, det_e in list(unmatched_det.items()):
        det_name = det_e.get("name", "")
        if not det_name:
            continue
        best_idx, best_sim, best_llm = -1, 0.0, None
        for i, llm_e in enumerate(all_unmatched_llm):
            if i in used_llm:
                continue
            llm_name = llm_e.get("name", "")
            if not llm_name:
                continue
            sim = SequenceMatcher(None, det_name.lower(), llm_name.lower()).ratio()
            # Bonus for substring containment
            if det_name.lower() in llm_name.lower() or llm_name.lower() in det_name.lower():
                sim = max(sim, 0.5)
            if sim > best_sim:
                best_sim = sim
                best_idx = i
                best_llm = llm_e
        if best_sim >= 0.3 and best_llm is not None:
            renamed.append({
                "det": det_name, "llm": best_llm.get("name", ""),
                "similarity": best_sim, "id": det_id,
            })
            matched_det_ids.add(det_id)
            used_llm.add(best_idx)
```

Then update the added/removed logic to handle LLM entities without IDs:

```python
# Track which no-id LLM entities were used in name matching
used_llm_no_id = {i - len(unmatched_llm_with_id) for i in used_llm if i >= len(unmatched_llm_with_id)}

for eid, e in llm_by_id.items():
    if eid not in matched_llm_ids:
        added.append(e)
for i, e in enumerate(unmatched_llm_no_id):
    if i not in used_llm_no_id:
        added.append(e)
for eid, e in det_by_id.items():
    if eid not in matched_det_ids:
        removed.append(e)
```

**Step 4: Run tests — expect PASS**

**Step 5: Run full test suite**

**Step 6: Commit**
```
feat(pipeline): name-similarity fallback in gap analysis diff engine
```

---

## Task 3: Library behavior inference

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py` (add `_infer_library_behaviors`)
- Test: `tests/test_pipeline_infer.py`

**Problem:** `_infer_behaviors()` only detects route handlers, CLI commands, handler classes, and workflow patterns. Pure libraries (colorama, requests, structlog) get 0 behaviors.

**Step 1: Write failing tests**

```python
def test_infer_library_behaviors_from_public_api():
    """Library modules with public functions should generate behaviors."""
    from architecture_model.pipeline.infer import _infer_library_behaviors
    from architecture_model.pipeline.observe_types import ModuleRecord, FunctionRecord
    from architecture_model.pipeline.infer_types import InferredCapability
    from pathlib import Path

    mod = ModuleRecord(
        path=Path("colorama/initialise.py"),
        functions=[
            FunctionRecord(name="init", signature="init(autoreset=False)", line=10),
            FunctionRecord(name="deinit", signature="deinit()", line=30),
            FunctionRecord(name="reinit", signature="reinit()", line=40),
            FunctionRecord(name="_setup", signature="_setup()", line=50),
        ],
        classes=[], imports=[], constants=[], line_count=60,
    )
    cap = InferredCapability(id="CAP-1", name="Initialise", description="", evidence_source="domain")
    behaviors = _infer_library_behaviors([mod], [cap], [])
    assert len(behaviors) >= 1
    names = [b.name for b in behaviors]
    assert any("init" in n.lower() for n in names)


def test_infer_library_behaviors_context_manager():
    """Classes with __enter__/__exit__ should generate context manager behavior."""
    from architecture_model.pipeline.infer import _infer_library_behaviors
    from architecture_model.pipeline.observe_types import ModuleRecord, ClassRecord
    from architecture_model.pipeline.infer_types import InferredCapability
    from pathlib import Path

    mod = ModuleRecord(
        path=Path("lib/connection.py"),
        functions=[],
        classes=[ClassRecord(
            name="Connection", bases=[],
            methods=["__init__", "__enter__", "__exit__", "execute", "commit"],
            line=1,
        )],
        imports=[], constants=[], line_count=80,
    )
    cap = InferredCapability(id="CAP-1", name="Connection", description="", evidence_source="domain")
    behaviors = _infer_library_behaviors([mod], [cap], [])
    assert any("context" in b.name.lower() or "connection" in b.name.lower() for b in behaviors)


def test_infer_library_behaviors_lifecycle():
    """Classes with open/close or connect/disconnect should generate lifecycle behavior."""
    from architecture_model.pipeline.infer import _infer_library_behaviors
    from architecture_model.pipeline.observe_types import ModuleRecord, ClassRecord
    from architecture_model.pipeline.infer_types import InferredCapability
    from pathlib import Path

    mod = ModuleRecord(
        path=Path("lib/session.py"),
        functions=[],
        classes=[ClassRecord(
            name="Session", bases=[],
            methods=["__init__", "open", "close", "execute"],
            line=1,
        )],
        imports=[], constants=[], line_count=60,
    )
    cap = InferredCapability(id="CAP-1", name="Session", description="", evidence_source="domain")
    behaviors = _infer_library_behaviors([mod], [cap], [])
    assert any("lifecycle" in b.name.lower() or "session" in b.name.lower() for b in behaviors)


def test_infer_library_behaviors_processing_chain():
    """Modules with parse/validate/apply-like chains should generate workflow."""
    from architecture_model.pipeline.infer import _infer_library_behaviors
    from architecture_model.pipeline.observe_types import ModuleRecord, FunctionRecord
    from architecture_model.pipeline.infer_types import InferredCapability
    from pathlib import Path

    mod = ModuleRecord(
        path=Path("lib/config.py"),
        functions=[
            FunctionRecord(name="parse", signature="parse(path)", line=10),
            FunctionRecord(name="validate", signature="validate(data)", line=30),
            FunctionRecord(name="apply", signature="apply(config)", line=50),
        ],
        classes=[], imports=[], constants=[], line_count=100,
    )
    cap = InferredCapability(id="CAP-1", name="Config", description="", evidence_source="domain")
    behaviors = _infer_library_behaviors([mod], [cap], [])
    assert len(behaviors) >= 1
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `_infer_library_behaviors()`**

Add to `infer.py`:

```python
# API entry point function names that suggest behaviors
_API_ENTRY_POINTS = {
    "init", "initialize", "setup", "configure", "create", "build",
    "connect", "open", "close", "load", "run", "start", "stop",
    "deinit", "shutdown", "teardown", "destroy", "reset",
}

# Lifecycle method pairs
_LIFECYCLE_PAIRS = [
    ("open", "close"), ("connect", "disconnect"), ("start", "stop"),
    ("acquire", "release"), ("lock", "unlock"), ("enter", "exit"),
    ("setup", "teardown"), ("init", "deinit"), ("begin", "end"),
]

# Processing chain indicators (ordered sequences)
_CHAIN_PATTERNS = [
    ["parse", "validate", "apply"],
    ["read", "process", "write"],
    ["load", "transform", "save"],
    ["fetch", "parse", "store"],
    ["encode", "decode"],
    ["serialize", "deserialize"],
    ["compress", "decompress"],
    ["encrypt", "decrypt"],
]


def _infer_library_behaviors(
    source_modules: list[ModuleRecord],
    capabilities: list[InferredCapability],
    actors: list[InferredActor],
) -> list[InferredBehavior]:
    """Infer behaviors from library API patterns that _infer_behaviors misses."""
    behaviors: list[InferredBehavior] = []
    bid = 0

    # Build cap_id lookup by module path
    cap_by_mod: dict[str, str] = {}
    for cap in capabilities:
        for src in getattr(cap, "module_sources", []):
            cap_by_mod[str(src)] = cap.id

    for mod in source_modules:
        if _is_non_source_module(mod):
            continue

        mod_stem = mod.path.stem.replace("_", " ").title()
        cap_id = cap_by_mod.get(str(mod.path), "")
        pub_funcs = [f for f in mod.functions if not f.name.startswith("_")]
        pub_func_names = {f.name.lower() for f in pub_funcs}

        # Pattern 1: API entry points
        for func in pub_funcs:
            if func.name.lower() in _API_ENTRY_POINTS:
                bid += 1
                verb = func.name.replace("_", " ").title()
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{bid}", name=f"{verb} {mod_stem}",
                    capability_id=cap_id, behavior_type="library_api",
                    steps=[func.signature or func.name],
                ))

        # Pattern 2: Context managers
        for cls in mod.classes:
            methods = {m.lower() for m in getattr(cls, "methods", [])}
            if "__enter__" in methods and "__exit__" in methods:
                bid += 1
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{bid}", name=f"{cls.name} context management",
                    capability_id=cap_id, behavior_type="use_case",
                    steps=["__enter__", "use", "__exit__"],
                ))

        # Pattern 3: Lifecycle methods
        for cls in mod.classes:
            methods = {m.lower() for m in getattr(cls, "methods", [])}
            for open_m, close_m in _LIFECYCLE_PAIRS:
                if open_m in methods and close_m in methods:
                    bid += 1
                    behaviors.append(InferredBehavior(
                        id=f"BEH-LIB-{bid}", name=f"{cls.name} lifecycle",
                        capability_id=cap_id, behavior_type="workflow",
                        steps=[open_m, "use", close_m],
                    ))
                    break  # One lifecycle behavior per class

        # Pattern 4: Processing chains
        for chain in _CHAIN_PATTERNS:
            if all(any(c in fn for fn in pub_func_names) for c in chain):
                bid += 1
                matched = [f.name for f in pub_funcs if any(c in f.name.lower() for c in chain)]
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{bid}", name=f"{mod_stem} processing pipeline",
                    capability_id=cap_id, behavior_type="workflow",
                    steps=matched,
                ))
                break  # One chain per module

        # Pattern 5: Factory/builder patterns
        for func in pub_funcs:
            if func.name.startswith(("create_", "make_", "build_")):
                bid += 1
                obj = func.name.split("_", 1)[1].replace("_", " ").title()
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{bid}", name=f"Create {obj}",
                    capability_id=cap_id, behavior_type="use_case",
                ))
        for cls in mod.classes:
            if "Builder" in cls.name or "Factory" in cls.name:
                bid += 1
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{bid}", name=f"Build {cls.name.replace('Builder','').replace('Factory','')}",
                    capability_id=cap_id, behavior_type="use_case",
                ))

    return behaviors
```

Wire into `run()`: after `_infer_behaviors()`, call `_infer_library_behaviors()` and extend the behaviors list. Deduplicate by checking if a behavior with the same `capability_id` and similar name already exists.

**Step 4: Run tests — expect PASS**

**Step 5: Run full test suite**

**Step 6: Commit**
```
feat(pipeline): library behavior inference from public API, context managers, and call chains
```

---

## Task 4: Add `library` and `core` layers + LLM QA layer for allocation

**Files:**
- Modify: `src/architecture_model/pipeline/allocate.py` (enhance `_infer_layer`, add `_detect_project_type`)
- Modify: `src/architecture_model/pipeline/stage_review.py` (add allocate-specific LLM review prompt)
- Modify: `src/architecture_model/pipeline/auto_correct.py` (add layer field as correctable)
- Test: `tests/test_pipeline_allocate.py`

**Problem:** `_infer_layer()` only has 4 layers (web/data/service/infra) via keyword matching. Libraries like colorama get "infra" for everything. Need `library` and `core` layers, plus LLM validation of layer assignments.

**Step 1: Write failing tests**

```python
def test_infer_layer_library_default():
    """Pure library files should get 'library' layer when project is library type."""
    from architecture_model.pipeline.allocate import _infer_layer
    from pathlib import Path
    assert _infer_layer([Path("colorama/ansi.py")], project_type="library") == "library"


def test_infer_layer_core():
    """Modules in core/ should get 'core' layer."""
    from architecture_model.pipeline.allocate import _infer_layer
    from pathlib import Path
    assert _infer_layer([Path("mylib/core/engine.py")]) == "core"


def test_infer_layer_still_detects_web():
    """Web keywords still work even in library projects."""
    from architecture_model.pipeline.allocate import _infer_layer
    from pathlib import Path
    assert _infer_layer([Path("mylib/api/routes.py")], project_type="library") == "web"


def test_detect_project_type_library():
    """Project with no web/CLI frameworks is classified as library."""
    from architecture_model.pipeline.allocate import _detect_project_type
    from architecture_model.pipeline.observe_types import ModuleRecord
    from pathlib import Path

    mods = [
        ModuleRecord(path=Path("mylib/core.py"), functions=[], classes=[],
                     imports=["os", "sys"], constants=[], line_count=50),
    ]
    assert _detect_project_type(mods) == "library"


def test_detect_project_type_web():
    """Project with Flask import is classified as web_app."""
    from architecture_model.pipeline.allocate import _detect_project_type
    from architecture_model.pipeline.observe_types import ModuleRecord
    from pathlib import Path

    mods = [
        ModuleRecord(path=Path("app/main.py"), functions=[], classes=[],
                     imports=["flask", "flask.Blueprint"], constants=[], line_count=50),
    ]
    assert _detect_project_type(mods) == "web_app"
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement**

**3a. Add `_detect_project_type()`:**
```python
_WEB_FRAMEWORKS = {"flask", "django", "fastapi", "starlette", "tornado", "aiohttp", "sanic", "bottle", "pyramid", "quart"}
_CLI_FRAMEWORKS = {"click", "typer"}

def _detect_project_type(modules: list[ModuleRecord]) -> str:
    all_imports: set[str] = set()
    for mod in modules:
        for imp in mod.imports:
            root = imp.split(".")[0].lower()
            all_imports.add(root)
    if all_imports & _WEB_FRAMEWORKS:
        return "web_app"
    if all_imports & _CLI_FRAMEWORKS:
        return "cli_tool"
    return "library"
```

**3b. Enhance `_infer_layer()`:**
```python
def _infer_layer(files: list[Path], project_type: str = "library") -> str:
    paths_str = " ".join(str(f) for f in files).lower()
    if any(w in paths_str for w in ("api", "route", "view", "handler", "endpoint")):
        return "web"
    if any(w in paths_str for w in ("model", "schema", "db", "repository", "migration")):
        return "data"
    if any(w in paths_str for w in ("service", "usecase", "domain", "logic")):
        return "service"
    if any(w in paths_str for w in ("core", "engine", "kernel")):
        return "core"
    if any(w in paths_str for w in ("util", "helper", "common", "compat")):
        return "infra"
    return "library" if project_type == "library" else "infra"
```

**3c. Update `run()` to call `_detect_project_type()` and pass result through.**

**3d. Enhance `build_semantic_review_prompt()` in `stage_review.py`** for allocate stage:
Add a LAYER VALIDATION section to the prompt asking the LLM to verify/correct layer assignments, especially when all components share the same layer.

**3e. Add `"layer"` to correctable fields** in `auto_correct.py`.

**Step 4: Run tests — expect PASS**

**Step 5: Run full test suite**

**Step 6: Commit**
```
feat(pipeline): add library/core layers with project type detection and LLM QA
```

---

## Task 5: Semantic interface naming

**Files:**
- Modify: `src/architecture_model/pipeline/specify.py` (add `_name_library_interface`, replace generic naming)
- Test: `tests/test_pipeline_specify.py`

**Problem:** All library interfaces are named `"COMP-X Library API"` — uses component ID, not even the component name. Module names, class names, and public symbols are all available but unused.

**Step 1: Write failing tests**

```python
def test_library_interface_uses_component_name():
    """Library API interfaces should include the component name, not comp ID."""
    from architecture_model.pipeline.specify import _name_library_interface

    name = _name_library_interface(
        comp_id="COMP-1", comp_name="AnsiToWin32",
        public_symbols={"AnsiToWin32": "class AnsiToWin32", "wrap_stream": "wrap_stream(stream)"},
        module_stems=["ansitowin32"],
    )
    assert "COMP-1" not in name
    assert "AnsiToWin32" in name


def test_library_interface_dominant_class():
    """If there's one dominant class, name after it."""
    from architecture_model.pipeline.specify import _name_library_interface

    name = _name_library_interface(
        comp_id="COMP-1", comp_name="Connections",
        public_symbols={"Connection": "class Connection", "connect": "connect()", "close": "close()"},
        module_stems=["connections"],
    )
    assert "Connection" in name


def test_library_interface_function_module():
    """If component exports mostly functions, use component name."""
    from architecture_model.pipeline.specify import _name_library_interface

    name = _name_library_interface(
        comp_id="COMP-2", comp_name="Ansi",
        public_symbols={"code": "code(n)", "set_title": "set_title(t)", "clear_screen": "clear_screen()"},
        module_stems=["ansi"],
    )
    assert "Ansi" in name or "ANSI" in name
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `_name_library_interface()`**

```python
def _name_library_interface(
    comp_id: str, comp_name: str,
    public_symbols: dict[str, str], module_stems: list[str],
) -> str:
    """Generate a descriptive interface name from component metadata."""
    classes = [name for name, sig in public_symbols.items() if sig.startswith("class ")]
    if len(classes) == 1:
        return f"{classes[0]} API"
    if comp_name and comp_name != comp_id:
        return f"{comp_name} API"
    if module_stems:
        stem = module_stems[0].replace("_", " ").title()
        return f"{stem} API"
    return f"{comp_id} Library API"
```

Replace both occurrences of `f"{comp_id} Library API"` (lines ~165 and ~182) with calls to this function. Build `comp_name` lookup from allocation data (available via `PipelineContext`) and `module_stems` from component files.

**Step 4: Run tests — expect PASS**

**Step 5: Run full test suite**

**Step 6: Commit**
```
feat(pipeline): semantic interface naming from component/class/module names
```

---

## Task 6: Improve contract matching for flat layouts

**Files:**
- Modify: `src/architecture_model/pipeline/contract.py` (add test_ prefix stripping)
- Test: `tests/test_pipeline_contract.py`

**Problem:** 0/7 contracts matched on colorama. Test file `tests/test_ansi.py` should match component with `colorama/ansi.py`, but the target `"test_ansi"` doesn't match stem `"ansi"` via existing strategies. Need to strip `test_` prefix before matching.

**Step 1: Write failing tests**

```python
def test_match_strips_test_prefix():
    """Contract matching should strip test_ prefix from test file stems."""
    from architecture_model.pipeline.contract import _match_target
    from pathlib import Path

    stem_to_comp = {"ansi": "COMP-2", "winterm": "COMP-3"}
    name_to_comp = {"ansi": "COMP-2", "winterm": "COMP-3"}

    result = _match_target("test_ansi", Path("tests/test_ansi.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-2"


def test_match_strips_test_suffix():
    """Contract matching should strip _test suffix."""
    from architecture_model.pipeline.contract import _match_target
    from pathlib import Path

    stem_to_comp = {"parser": "COMP-1"}
    name_to_comp = {"parser": "COMP-1"}

    result = _match_target("parser_test", Path("tests/parser_test.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-1"


def test_match_compound_test_name():
    """test_ansitowin32 should match ansitowin32 component file."""
    from architecture_model.pipeline.contract import _match_target
    from pathlib import Path

    stem_to_comp = {"ansitowin32": "COMP-1"}
    name_to_comp = {"ansitowin32": "COMP-1"}

    result = _match_target("test_ansitowin32", Path("tests/test_ansitowin32.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-1"
```

**Step 2: Run tests — expect FAIL**

First verify these actually fail. Strategy 4 (stem substring in target) checks if `"ansi"` (3 chars, >=3) is in `"test_ansi"` — this SHOULD match. If tests pass already, the bug is in the caller (how `target` is computed). Investigate.

**Step 3: Implement test_ prefix stripping**

Add as strategy 0 at the top of `_match_target()`:

```python
# Strategy 0: Strip test_ prefix / _test suffix
stripped = target
if stripped.startswith("test_"):
    stripped = stripped[5:]
elif stripped.endswith("_test"):
    stripped = stripped[:-5]
if stripped and stripped != target:
    if stripped in stem_to_comp:
        return stem_to_comp[stripped]
    if stripped.lower() in name_to_comp:
        return name_to_comp[stripped.lower()]
```

If the issue is in the caller instead, fix the caller to strip the prefix before calling `_match_target()`. Either way, add the stripping logic.

**Step 4: Run tests — expect PASS**

**Step 5: Run full test suite**

**Step 6: Commit**
```
feat(pipeline): strip test_ prefix in contract matching for flat test layouts
```

---

## Task 7: E2E validation on colorama + final verification

**Files:**
- No new code files — run E2E and verify improvements

**Step 1: Run gap analysis on colorama**
```
/opt/anaconda3/bin/python -m architecture_model gap-analysis projects/colorama/
```

**Step 2: Verify improvements in the generated report:**
- [ ] Relationship types display correctly (e.g., `"realizes"`, not `"None"`)
- [ ] Renamed entities show actual name pairs with similarity scores (not 0 matches)
- [ ] Behaviors > 0 for colorama (library behaviors detected)
- [ ] Layer assignments include `library` or `core` (not all `infra`)
- [ ] Interface names are semantic (e.g., `"AnsiToWin32 API"`, not `"COMP-1 Library API"`)
- [ ] Contract matching > 0 matched (test_ prefix stripped)

**Step 3: Run full test suite — expect baseline (7 failed, ~1500 passed)**

**Step 4: Commit any tracer/report adjustments needed**

**Step 5: Update CONTEXT.md with discoveries and results**

```
docs: update CONTEXT.md with pipeline precision fix results
```

---

## Execution Order & Dependencies

```
Task 1 (rel type bug)  ──→ Task 2 (diff engine) ──→ Task 7 (E2E)
                                                        ↑
Task 3 (behaviors)     ──→ ─────────────────────────────┤
Task 4 (layers + LLM QA) → ─────────────────────────────┤
Task 5 (interface names) → ─────────────────────────────┤
Task 6 (contract match)  → ────────────────────────────-┘
```

Tasks 1-2 are sequential (type fix unblocks accurate diffing). Tasks 3-6 are independent of each other and can be parallelized with subagents. Task 7 depends on all others.

## Key Code References

- `DerivedRelationship.rel_type`: `src/architecture_model/pipeline/relate_types.py:12`
- `diff_stage_outputs()`: `src/architecture_model/pipeline/gap_analysis.py:142-189`
- `_infer_behaviors()`: `src/architecture_model/pipeline/infer.py:575-768`
- `_infer_layer()`: `src/architecture_model/pipeline/allocate.py:454-463`
- Library API naming: `src/architecture_model/pipeline/specify.py:152-187`
- `_match_target()`: `src/architecture_model/pipeline/contract.py:123-174`
- `_evaluate_gates()`: `src/architecture_model/pipeline/coordinator.py:145-198`
- `build_semantic_review_prompt()`: `src/architecture_model/pipeline/stage_review.py`
