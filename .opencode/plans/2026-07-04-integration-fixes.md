# Five Integration Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 bugs discovered during integration testing against fastapi-realworld-example-app.

**Architecture:** All fixes target the extraction pipeline (`extract/route_detector.py` and `extract/from_code.py`) and naming heuristics (`config/loader.py`). Each fix is independent and TDD: write failing test → fix → verify no regressions.

**Tech Stack:** Python 3.11+, AST module, pytest

**Test command:** `pytest --tb=short -q` (212 tests must pass after each fix)

---

### Task 1: Fix auth detection for `Depends(factory_func())`

**Problem:** `_is_auth_call` in `route_detector.py:181` only handles `Depends(Name)` — when the argument is a Call node like `Depends(get_current_user_authorizer())`, `_get_node_name` returns `""` and auth goes undetected. Also missing: route-level `dependencies=[Depends(auth)]` kwarg on the decorator.

**Files:**
- Modify: `src/architecture_model/extract/route_detector.py:181-195` (`_is_auth_call`)
- Modify: `src/architecture_model/extract/route_detector.py:144-157` (`_has_auth_dependency`)
- Test: `tests/test_route_detector.py`

**Step 1: Write failing tests**

```python
# In tests/test_route_detector.py — add new test source and tests

FASTAPI_FACTORY_AUTH_SOURCE = textwrap.dedent("""\
    from fastapi import APIRouter, Depends
    from app.auth import get_current_user_authorizer

    router = APIRouter()

    @router.get("/me")
    async def get_profile(
        user=Depends(get_current_user_authorizer()),
    ):
        \"\"\"Get current user profile.\"\"\"
        ...

    @router.post("/articles", dependencies=[Depends(get_current_user_authorizer())])
    async def create_article(payload: dict):
        \"\"\"Create article (auth on decorator).\"\"\"
        ...
""")


def test_fastapi_factory_auth_detected():
    """Depends(factory_func()) should be detected as auth."""
    tree = ast.parse(FASTAPI_FACTORY_AUTH_SOURCE)
    routes = _extract_fastapi_routes(tree, "app/api/users.py")
    assert len(routes) == 2
    assert routes[0].is_authenticated is True  # Depends(factory())
    assert routes[1].is_authenticated is True  # dependencies kwarg


def test_fastapi_route_level_dependencies_kwarg():
    """dependencies=[Depends(auth)] on decorator should trigger auth."""
    tree = ast.parse(FASTAPI_FACTORY_AUTH_SOURCE)
    routes = _extract_fastapi_routes(tree, "app/api/users.py")
    article_route = [r for r in routes if r.function_name == "create_article"][0]
    assert article_route.is_authenticated is True
```

**Step 2: Run tests — expect FAIL** (2 new tests fail)

```bash
pytest tests/test_route_detector.py::test_fastapi_factory_auth_detected tests/test_route_detector.py::test_fastapi_route_level_dependencies_kwarg -v
```

**Step 3: Fix `_is_auth_call`** — handle Call node arg inside Depends:

```python
def _is_auth_call(node: ast.expr) -> bool:
    """Check if a Call node is Depends(auth...) or Security(...)."""
    if not isinstance(node, ast.Call):
        return False
    func_name = _get_call_name(node)
    if func_name == "Security":
        return True
    if func_name == "Depends":
        if node.args:
            arg = node.args[0]
            # Direct name: Depends(get_current_user)
            arg_name = _get_node_name(arg)
            if arg_name and _is_auth_name(arg_name):
                return True
            # Factory call: Depends(get_current_user_authorizer())
            if isinstance(arg, ast.Call):
                call_name = _get_call_name(arg)
                if call_name and _is_auth_name(call_name):
                    return True
    return False
```

**Step 4: Fix `_has_auth_dependency`** — also check decorator `dependencies` kwarg:

```python
def _has_auth_dependency(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function has auth-related Depends() or Security() parameters."""
    # Check function parameter annotations
    for arg in _all_function_args(node):
        if arg.annotation is None:
            continue
        if _is_auth_annotation(arg.annotation):
            return True
    # Check function parameter defaults
    defaults = _collect_defaults(node)
    for default in defaults:
        if _is_auth_call(default):
            return True
    # Check route decorator dependencies=[Depends(...)] kwarg
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            for kw in decorator.keywords:
                if kw.arg == "dependencies" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if _is_auth_call(elt):
                            return True
    return False
```

**Step 5: Run full test suite**

```bash
pytest --tb=short -q
```

Expected: all 214+ tests pass (212 existing + 2 new)

**Step 6: Commit**

```bash
git add src/architecture_model/extract/route_detector.py tests/test_route_detector.py
git commit -m "fix: detect Depends(factory()) and route-level dependencies kwarg as auth"
```

---

### Task 2: Fix interface provider/consumer direction

**Problem:** In `from_code.py:430-431`, `source_block` (the importer) is set as `provider`, but semantically the importee provides the interface and the importer consumes it.

Context: In `manifest/interfaces.py`, `source` = the file doing the importing, `target` = the file being imported.

**Files:**
- Modify: `src/architecture_model/extract/from_code.py:417-433`
- Modify: `tests/test_extract_from_code.py`

**Step 1: Write failing test**

```python
# Add to tests/test_extract_from_code.py

def test_interface_direction_importer_is_consumer(sample_project):
    """The importer should be consumer, importee should be provider."""
    model = extract_from_code(sample_project)
    # In sample_project: app/api imports from app/models
    # So F1 (api) is the consumer, F2 (models) is the provider
    internal_ifaces = [i for i in model.entities.interfaces if i.type == InterfaceType.INTERNAL]
    assert len(internal_ifaces) > 0
    for iface in internal_ifaces:
        if "F1" in iface.id and "F2" in iface.id:
            # target_block (importee=F2) should be provider
            assert iface.provider == "CAP-F2", f"Expected provider=CAP-F2, got {iface.provider}"
            assert iface.consumer == "CAP-F1", f"Expected consumer=CAP-F1, got {iface.consumer}"
            break
    else:
        pytest.fail("Expected an internal interface between F1 and F2")
```

**Step 2: Run test — expect FAIL** (provider/consumer are currently swapped)

```bash
pytest tests/test_extract_from_code.py::test_interface_direction_importer_is_consumer -v
```

**Step 3: Swap provider and consumer in `_derive_interfaces`**

Replace lines 417-433:

```python
        if source_block and target_block and source_block != target_block:
            # source_block = importer (consumer), target_block = importee (provider)
            pair = (target_block, source_block)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            interfaces.append(
                Interface(
                    id=f"IFC-{target_block}-{source_block}",
                    name=f"{target_block} → {source_block}",
                    status=Status.ACTIVE,
                    description=f"Interface: {target_block} provides to {source_block}",
                    type=InterfaceType.INTERNAL,
                    provider=f"CAP-{target_block}",
                    consumer=f"CAP-{source_block}",
                )
            )
```

**Step 4: Fix any existing tests** that assert on old interface IDs or provider/consumer values.

Search for patterns like `IFC-F1-F2` in test files — these may need to become `IFC-F2-F1`.

**Step 5: Run full test suite**

```bash
pytest --tb=short -q
```

**Step 6: Commit**

```bash
git add src/architecture_model/extract/from_code.py tests/test_extract_from_code.py
git commit -m "fix: correct interface provider/consumer direction (importee=provider)"
```

---

### Task 3: Behavior naming uses function_name instead of path slug

**Problem:** `_derive_route_behaviors` (from_code.py:251) generates behavior IDs like `BEH-GET-articles-slug` from the URL path. Should prefer `route.function_name` for semantic clarity: `BEH-GET-get_article`.

**Files:**
- Modify: `src/architecture_model/extract/from_code.py:249-260`
- Modify: `tests/test_extract_from_code.py`

**Step 1: Write failing test**

```python
def test_behavior_id_uses_function_name(sample_project):
    """Behavior IDs should use function_name, not path slugs."""
    model = extract_from_code(sample_project)
    behavior_ids = [b.id for b in model.entities.behaviors]
    # Should contain function-name-based IDs
    # The sample_project fixture has routes with function names like "get_articles", "create_article"
    assert any("get_articles" in bid or "create_article" in bid for bid in behavior_ids), \
        f"Expected function-name-based IDs, got: {behavior_ids}"
```

**Step 2: Run test — expect FAIL**

```bash
pytest tests/test_extract_from_code.py::test_behavior_id_uses_function_name -v
```

**Step 3: Change ID generation to prefer function_name**

Replace lines 249-260:

```python
    for route in routes:
        # Prefer function name for semantic IDs
        name_slug = _slugify(route.function_name) if route.function_name else ""
        if not name_slug:
            name_slug = _slugify(route.path) if route.path else "unknown"

        behavior_id = f"BEH-{route.method}-{name_slug}"

        # Deduplicate
        if behavior_id in seen_ids:
            continue
        seen_ids.add(behavior_id)
```

**Step 4: Update existing tests** that assert on old behavior ID format.

**Step 5: Run full test suite**

```bash
pytest --tb=short -q
```

**Step 6: Commit**

```bash
git add src/architecture_model/extract/from_code.py tests/test_extract_from_code.py
git commit -m "fix: use function_name for behavior IDs instead of path slugs"
```

---

### Task 4: Better F-block naming from imports

**Problem:** `_discover_functional_blocks` (loader.py:267) produces raw "Api", "Db" from directory names when no docstring is available. Should use import-based heuristics for common patterns.

**Files:**
- Modify: `src/architecture_model/config/loader.py:260-267` (main discovery)
- Modify: `src/architecture_model/config/loader.py:409` (fallback discovery)
- Test: `tests/test_config_loader.py` (create if needed)

**Step 1: Write failing test**

```python
# In tests/test_config_loader.py (create if doesn't exist)

from architecture_model.config.loader import _discover_functional_blocks

def test_fblock_naming_from_imports(tmp_path):
    """F-blocks with common import patterns should get semantic names."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    api_dir = pkg / "api"
    api_dir.mkdir()
    (api_dir / "__init__.py").write_text("")
    (api_dir / "routes.py").write_text("from fastapi import APIRouter\nrouter = APIRouter()\n")

    db_dir = pkg / "db"
    db_dir.mkdir()
    (db_dir / "__init__.py").write_text("")
    (db_dir / "models.py").write_text("from sqlalchemy import Column, Integer\n")

    blocks = _discover_functional_blocks(tmp_path)
    names = {b.name for b in blocks}
    # Should NOT be raw title-cased dir names
    assert "Api" not in names, f"Got raw name 'Api' in {names}"
    assert "Db" not in names, f"Got raw name 'Db' in {names}"
```

**Step 2: Run test — expect FAIL**

```bash
pytest tests/test_config_loader.py::test_fblock_naming_from_imports -v
```

**Step 3: Add `_infer_block_name_from_imports` helper**

Add to `config/loader.py` before `_discover_functional_blocks`:

```python
def _infer_block_name_from_imports(package_dir: Path) -> str:
    """Infer a semantic block name from characteristic imports in the package."""
    import ast as _ast

    imports: set[str] = set()
    for py_file in package_dir.rglob("*.py"):
        try:
            tree = _ast.parse(py_file.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, _ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])

    # Heuristic mapping: characteristic imports → semantic names
    if imports & {"fastapi", "flask", "django", "starlette"}:
        return "REST API Endpoints"
    if imports & {"sqlalchemy", "tortoise"} and any(
        kw in package_dir.name.lower() for kw in ("model", "db", "database")
    ):
        return "Database Models"
    if imports & {"sqlalchemy", "asyncpg", "psycopg2", "databases"}:
        return "Database Access"
    if imports & {"pydantic"} and "schema" in package_dir.name.lower():
        return "Data Schemas"
    if imports & {"celery", "dramatiq", "rq"}:
        return "Background Tasks"
    return ""
```

**Step 4: Use the helper in `_discover_functional_blocks`**

Replace lines 264-267:

```python
        # Use docstring as name if it's short enough
        if description and len(description) < 40:
            block_name = description
        else:
            # Try import-based semantic naming, fall back to title-cased dir
            block_name = _infer_block_name_from_imports(subdir) or \
                         subdir.name.replace("_", " ").replace("-", " ").title()
```

**Step 5: Apply same logic in `_fblocks_from_top_level_dirs`** (line 409):

```python
        dir_name = _infer_block_name_from_imports(child) or \
                   child.name.replace("_", " ").replace("-", " ").title()
```

**Step 6: Run full test suite**

```bash
pytest --tb=short -q
```

**Step 7: Commit**

```bash
git add src/architecture_model/config/loader.py tests/test_config_loader.py
git commit -m "fix: infer semantic F-block names from import analysis"
```

---

### Task 5: Layer depends-on derived from cross-layer imports

**Problem:** Lines 553-564 of `from_code.py` hardcode layer dependency as sequential order. Should derive from actual cross-layer interfaces instead.

**Files:**
- Modify: `src/architecture_model/extract/from_code.py:553-564`
- Add helper: `_cap_to_layer` function in same file
- Test: `tests/test_extract_from_code.py`

**Step 1: Write failing test**

```python
def test_layer_depends_on_from_imports_not_ordering(sample_project):
    """Layer depends-on should derive from cross-layer imports, not sequential ordering."""
    model = extract_from_code(sample_project)
    layer_deps = [
        r for r in model.relationships
        if r.type == RelationType.DEPENDS_ON
        and r.from_id.endswith("-layer")
        and r.to_id.endswith("-layer")
    ]
    # Should have at least one layer dependency
    assert len(layer_deps) > 0
    # No circular dependencies (if A→B exists, B→A should NOT)
    for dep in layer_deps:
        reverse = next(
            (d for d in layer_deps if d.from_id == dep.to_id and d.to_id == dep.from_id),
            None,
        )
        assert reverse is None, f"Circular layer dep: {dep.from_id} <-> {dep.to_id}"
    # data-layer should not depend on web-layer (no upward deps in clean arch)
    upward_deps = [d for d in layer_deps if d.from_id == "data-layer" and d.to_id == "web-layer"]
    assert len(upward_deps) == 0, "data-layer should not depend on web-layer"
```

**Step 2: Run test — might pass with current sequential logic, adjust test if needed**

```bash
pytest tests/test_extract_from_code.py::test_layer_depends_on_from_imports_not_ordering -v
```

**Step 3: Add `_cap_to_layer` helper**

```python
def _cap_to_layer(cap_id: str, config: ProjectConfig) -> str | None:
    """Map a capability ID (CAP-F1) back to its layer ID."""
    block_id = cap_id.replace("CAP-", "")
    for block in config.functional_blocks:
        if block.id == block_id:
            for layer in config.layers:
                for bdir in block.dirs:
                    if bdir in layer.dirs or any(
                        bdir.startswith(ld + "/") or ld.startswith(bdir + "/")
                        for ld in layer.dirs
                    ):
                        return layer.id
    return None
```

**Step 4: Replace hardcoded sequential logic**

Replace lines 553-564 with:

```python
    # depends-on: layer-to-layer from cross-layer interfaces (import-derived)
    layer_dep_pairs: set[tuple[str, str]] = set()
    for iface in interfaces:
        if iface.type == InterfaceType.INTERNAL and iface.provider and iface.consumer:
            consumer_layer = _cap_to_layer(iface.consumer, config)
            provider_layer = _cap_to_layer(iface.provider, config)
            if consumer_layer and provider_layer and consumer_layer != provider_layer:
                layer_dep_pairs.add((consumer_layer, provider_layer))

    for from_layer, to_layer in sorted(layer_dep_pairs):
        relationships.append(
            Relationship(
                type=RelationType.DEPENDS_ON,
                from_id=from_layer,
                to_id=to_layer,
                description=f"{from_layer} depends on {to_layer}",
                strength=Strength.STRONG,
            )
        )
```

**Step 5: Run full test suite**

```bash
pytest --tb=short -q
```

**Step 6: Commit**

```bash
git add src/architecture_model/extract/from_code.py tests/test_extract_from_code.py
git commit -m "fix: derive layer depends-on from cross-layer imports instead of ordering"
```

---

### Task 6: Integration verification

**Step 1:** Re-run extract against fastapi-realworld:

```bash
architecture-model extract --from-code /tmp/test-arch-model/fastapi-realworld/ -o /tmp/test-arch-model/fastapi-realworld/code-model-v2.yaml
```

**Step 2:** Validate:

```bash
architecture-model validate /tmp/test-arch-model/fastapi-realworld/code-model-v2.yaml
architecture-model stats /tmp/test-arch-model/fastapi-realworld/code-model-v2.yaml
```

**Step 3:** Verify assertions:
- Auth routes detected (expect 10+ authenticated routes, ACT-USER present)
- Interface direction correct (api=consumer, models=provider)
- Behavior IDs semantic (function names)
- F-block names descriptive
- Layer deps import-derived, no circular deps

**Step 4:** Run full test suite one final time:

```bash
pytest --tb=short -q
```

Expected: all tests pass, 0 failures
