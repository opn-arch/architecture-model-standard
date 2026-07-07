# Blind Regen Fidelity Boost Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise blind regen fidelity from 65% (15/23) to 85%+ by fixing test-to-source mapping for package-level imports and injecting rich dependency context into blind prompts.

**Architecture:** Two independent improvements — (A) fix `_map_tests_to_sources()` in merger.py to trace `__init__.py` re-exports, and (B) replace stub `_build_dependency_context()` in regen_loop.py with rich API surface extraction from the model.

**Tech Stack:** Python AST parsing, architecture-model-standard types, opencode-arch CLI

---

## Part A: Fix Test-to-Source Mapping (architecture-model-standard)

### Problem

`from tqdm import tqdm` → merger splits to parts `["tqdm"]` → "tqdm" is NOT a file stem (it's a directory/package) → 0 test contracts mapped. Same for `from tqdm.contrib import tenumerate` → `"contrib"` is a sub-package, not a file.

### Solution

When an import references a package (directory with `__init__.py`), parse that `__init__.py` to find re-exported modules and trace to actual source files.

---

### Task 1: Write failing test for __init__.py re-export tracing

**Files:**
- Create: `tests/test_init_reexport_mapping.py`

**Step 1: Write the failing test**

```python
"""Tests for __init__.py re-export tracing in test-to-source mapping."""
import ast
import tempfile
from pathlib import Path

import pytest

from architecture_model.core.merger import _map_tests_to_sources


@pytest.fixture
def package_repo(tmp_path):
    """Create a repo with package-level imports (like tqdm)."""
    # Package structure: mylib/__init__.py re-exports from .core and .utils
    pkg = tmp_path / "mylib"
    pkg.mkdir()

    # __init__.py re-exports from submodules
    (pkg / "__init__.py").write_text(
        "from .core import MyClass, helper\n"
        "from .utils import format_value\n"
        "__all__ = ['MyClass', 'helper', 'format_value']\n"
    )
    (pkg / "core.py").write_text(
        "class MyClass:\n    pass\n\ndef helper():\n    return 1\n"
    )
    (pkg / "utils.py").write_text(
        "def format_value(x):\n    return str(x)\n"
    )

    # Test file imports from package level
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mylib.py").write_text(
        "from mylib import MyClass, helper, format_value\n\n"
        "def test_my_class():\n    assert MyClass() is not None\n"
    )

    return tmp_path


def test_package_import_traces_to_submodules(package_repo):
    """from mylib import X should map to core.py and utils.py, not just __init__."""
    test_files = list((package_repo / "tests").glob("test_*.py"))
    source_stems = {"__init__", "core", "utils"}

    mapping = _map_tests_to_sources(test_files, source_stems, package_repo)

    # Should map to both core and utils (the actual implementation files)
    assert "core" in mapping, "Should trace re-export to core.py"
    assert "utils" in mapping, "Should trace re-export to utils.py"


def test_subpackage_import_traces_through_init(tmp_path):
    """from mylib.sub import X should trace sub/__init__.py re-exports."""
    pkg = tmp_path / "mylib"
    sub = pkg / "sub"
    sub.mkdir(parents=True)

    (pkg / "__init__.py").write_text("")
    (sub / "__init__.py").write_text("from .impl import do_thing\n")
    (sub / "impl.py").write_text("def do_thing(): pass\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sub.py").write_text(
        "from mylib.sub import do_thing\n\n"
        "def test_do_thing():\n    assert do_thing() is None\n"
    )

    test_files = [tests_dir / "test_sub.py"]
    source_stems = {"__init__", "impl"}

    mapping = _map_tests_to_sources(test_files, source_stems, tmp_path)

    assert "impl" in mapping, "Should trace sub/__init__.py re-export to impl.py"


def test_direct_submodule_import_still_works(tmp_path):
    """from mylib.core import X should still directly map to core.py."""
    pkg = tmp_path / "mylib"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Foo: pass\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_core.py").write_text(
        "from mylib.core import Foo\n\n"
        "def test_foo():\n    assert Foo()\n"
    )

    test_files = [tests_dir / "test_core.py"]
    source_stems = {"__init__", "core"}

    mapping = _map_tests_to_sources(test_files, source_stems, tmp_path)

    assert "core" in mapping


def test_no_false_positives_from_stdlib(tmp_path):
    """Importing 'os.path' should NOT map to a local 'path.py'."""
    pkg = tmp_path / "mylib"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "path.py").write_text("def resolve(): pass\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_path.py").write_text(
        "import os.path\n"
        "from mylib.path import resolve\n\n"
        "def test_resolve():\n    assert resolve() is None\n"
    )

    test_files = [tests_dir / "test_path.py"]
    source_stems = {"__init__", "path"}

    mapping = _map_tests_to_sources(test_files, source_stems, tmp_path)

    # 'path' should be mapped (from mylib.path import), but the test
    # should not double-map from 'os.path'
    assert "path" in mapping
    # Only one test file should be in the mapping for 'path'
    assert len(mapping["path"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_init_reexport_mapping.py -v --ignore=tests/test_config_loader.py`
Expected: FAIL on `test_package_import_traces_to_submodules` and `test_subpackage_import_traces_through_init`

---

### Task 2: Implement __init__.py re-export tracing

**Files:**
- Modify: `src/architecture_model/core/merger.py` (the `_map_tests_to_sources` function)

**Step 1: Add helper function to trace re-exports**

Add above `_map_tests_to_sources`:

```python
def _trace_init_reexports(init_path: Path) -> set[str]:
    """Parse __init__.py and return stems of modules it re-exports from.

    Handles patterns like:
        from .core import MyClass       -> {"core"}
        from .utils import helper       -> {"utils"}
        from .sub.impl import thing     -> {"impl"}
    """
    try:
        source = init_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(init_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()

    stems: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0 and node.module:
            # Relative import: from .core import X -> module="core"
            # from .sub.impl import X -> module="sub.impl"
            parts = node.module.split(".")
            # The last part is the actual module file
            stem = parts[-1]
            # Skip if it's just re-exporting from __init__ of a sub-package
            # (we'll handle that recursively if needed)
            if stem != "__init__":
                stems.add(stem)
        elif isinstance(node, ast.ImportFrom) and node.level > 0 and not node.module:
            # from . import something -> names are the module stems
            for alias in node.names:
                stems.add(alias.name)
    return stems
```

**Step 2: Modify `_map_tests_to_sources` to use re-export tracing**

Replace the existing function body with logic that:
1. When a part matches a package directory name (not a file stem), find its `__init__.py`
2. Trace re-exports to get the actual implementation module stems
3. Add those stems to the mapping

```python
def _map_tests_to_sources(
    test_files: list[Path],
    source_stems: set[str],
    project_root: Path,
) -> dict[str, list[Path]]:
    """Map source file stems to the test files that cover them.

    Parses each test file's imports to find which source modules it tests.
    Handles package-level imports by tracing __init__.py re-exports.
    Returns: {source_stem: [test_file_paths]}
    """
    mapping: dict[str, list[Path]] = {}

    # Build a set of package directory names for re-export tracing
    package_dirs: dict[str, Path] = {}  # {package_name: __init__.py path}
    for init_file in project_root.rglob("__init__.py"):
        rel = init_file.relative_to(project_root)
        parts = rel.parent.parts
        if parts and "test" not in parts[0].lower():
            # Register the package name -> __init__.py
            pkg_name = parts[-1] if len(parts) > 0 else ""
            if pkg_name:
                package_dirs[pkg_name] = init_file
            # Also register dotted path: mylib.sub -> sub/__init__.py
            if len(parts) > 1:
                dotted = ".".join(parts)
                package_dirs[dotted] = init_file

    for test_file in test_files:
        try:
            source = test_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(test_file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        # Extract imported module names
        imported_stems: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                for part in parts:
                    if part in source_stems:
                        imported_stems.add(part)
                    elif part in package_dirs:
                        # This is a package-level import — trace re-exports
                        init_path = package_dirs[part]
                        reexported = _trace_init_reexports(init_path)
                        imported_stems.update(reexported & source_stems)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    for part in parts:
                        if part in source_stems:
                            imported_stems.add(part)
                        elif part in package_dirs:
                            init_path = package_dirs[part]
                            reexported = _trace_init_reexports(init_path)
                            imported_stems.update(reexported & source_stems)

        for stem in imported_stems:
            mapping.setdefault(stem, []).append(test_file)

    return mapping
```

**Step 3: Run tests to verify they pass**

Run: `pytest tests/test_init_reexport_mapping.py -v --ignore=tests/test_config_loader.py`
Expected: ALL PASS

**Step 4: Run full test suite to verify no regressions**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: No new failures

**Step 5: Commit**

```bash
git add tests/test_init_reexport_mapping.py src/architecture_model/core/merger.py
git commit -m "feat: trace __init__.py re-exports in test-to-source mapping"
```

---

## Part B: Rich Dependency Context (opencode-arch)

### Problem

`_build_dependency_context()` only outputs "Depends on subsystem 'foo'" — useless for blind regen. The agent needs the actual API surface (classes, functions, constants) of upstream modules to produce correct imports and usage.

### Solution

Replace with a function that loads the model and extracts the public API surface of each dependency subsystem's components.

---

### Task 3: Write failing test for rich dependency context

**Files:**
- Create: `/Users/baigm2/Documents/Projects/opencode-arch/tests/test_dependency_context.py`

**Step 1: Write the failing test**

```python
"""Tests for rich dependency context in blind regen prompts."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _make_subsystem(name: str, source_files: list, dependencies: list):
    """Create a mock subsystem with given deps."""
    sub = MagicMock()
    sub.name = name
    sub.source_files = [Path(f) for f in source_files]
    sub.dependencies = dependencies
    return sub


def test_dependency_context_includes_signatures(tmp_path):
    """Dependency context should include function signatures from upstream."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    # Create a minimal model file with a component that has signatures
    model_yaml = tmp_path / ".architecture-model.yaml"
    model_yaml.write_text("""\
meta:
  project: test
  schema_version: '1.4'
entities:
  components:
    - id: comp-utils
      name: utils
      status: ACTIVE
      kind: module
      files: ["mylib/utils.py"]
      signatures:
        - name: format_value
          params: ["x: Any", "precision: int = 2"]
          returns: "str"
          body_hint: "return f'{x:.{precision}f}'"
        - name: validate
          params: ["data: dict"]
          returns: "bool"
      constants:
        - name: MAX_SIZE
          value: "1024"
          type: int
    - id: comp-core
      name: core
      status: ACTIVE
      kind: module
      files: ["mylib/core.py"]
      signatures:
        - name: process
          params: ["items: list"]
          returns: "list"
relationships: []
""")

    subsystem = _make_subsystem(
        name="stdlib",
        source_files=["mylib/stdlib.py"],
        dependencies=["utils"],
    )

    context = _build_dependency_context(subsystem, tmp_path)

    # Should include function signatures
    assert "format_value" in context
    assert "validate" in context
    # Should include constants
    assert "MAX_SIZE" in context
    assert "1024" in context
    # Should NOT include unrelated subsystem (core)
    assert "process" not in context


def test_dependency_context_includes_class_info(tmp_path):
    """Dependency context should include class names and members."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    model_yaml = tmp_path / ".architecture-model.yaml"
    model_yaml.write_text("""\
meta:
  project: test
  schema_version: '1.4'
entities:
  components:
    - id: comp-base
      name: _base
      status: ACTIVE
      kind: module
      files: ["structlog/_base.py"]
      symbols:
        - name: BoundLoggerBase
          kind: class
          supers: ["object"]
          members: ["bind", "unbind", "try_unbind", "new", "_logger"]
      signatures:
        - name: get_context
          params: ["self"]
          returns: "dict[str, Any]"
      constants: []
relationships: []
""")

    subsystem = _make_subsystem(
        name="stdlib",
        source_files=["structlog/stdlib.py"],
        dependencies=["_base"],
    )

    context = _build_dependency_context(subsystem, tmp_path)

    assert "BoundLoggerBase" in context
    assert "bind" in context
    assert "get_context" in context


def test_dependency_context_empty_when_no_deps(tmp_path):
    """No dependencies should produce empty string."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    subsystem = _make_subsystem(
        name="utils",
        source_files=["mylib/utils.py"],
        dependencies=[],
    )

    context = _build_dependency_context(subsystem, tmp_path)
    assert context == ""


def test_dependency_context_fallback_without_model(tmp_path):
    """Without model file, should still list dependency names."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    subsystem = _make_subsystem(
        name="core",
        source_files=["mylib/core.py"],
        dependencies=["utils", "config"],
    )

    context = _build_dependency_context(subsystem, tmp_path)

    # Should at least mention the dependency names
    assert "utils" in context
    assert "config" in context
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_dependency_context.py -v` (from opencode-arch)
Expected: FAIL — current `_build_dependency_context` doesn't include signatures/classes

---

### Task 4: Implement rich dependency context

**Files:**
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/cli/regen_loop.py`

**Step 1: Replace `_build_dependency_context`**

Replace the existing implementation (lines 594-602) with:

```python
def _build_dependency_context(subsystem, repo_path: Path) -> str:
    """Build rich dependency context: API surfaces of upstream subsystems.

    For each dependency, extracts from the model:
    - Module-level constants (name = value)
    - Class definitions (name, bases, public members)
    - Function signatures (name, params, return type)

    This gives the agent enough info to produce correct imports and usage
    in blind mode where it cannot read source files.
    """
    if not subsystem.dependencies:
        return ""

    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        # Fallback: just names
        return "\n".join(f"- Depends on module '{d}'" for d in subsystem.dependencies)

    try:
        from architecture_model.core.parser import load_model

        model = load_model(model_file)
    except Exception:
        return "\n".join(f"- Depends on module '{d}'" for d in subsystem.dependencies)

    parts = []
    for dep_name in subsystem.dependencies:
        # Find components matching this dependency subsystem
        dep_comps = []
        for comp in model.entities.components:
            comp_files = getattr(comp, "files", [])
            comp_stems = {Path(f).stem for f in comp_files} if comp_files else set()
            if dep_name in comp_stems or comp.name == dep_name:
                dep_comps.append(comp)

        if not dep_comps:
            parts.append(f"#### {dep_name}\n# (no model data available)")
            continue

        section_lines = [f"#### Module: {dep_name}"]

        for comp in dep_comps:
            # Constants
            for const in getattr(comp, "constants", []) or []:
                const_name = getattr(const, "name", str(const))
                const_value = getattr(const, "value", "")
                const_type = getattr(const, "type", "")
                type_ann = f": {const_type}" if const_type else ""
                section_lines.append(f"  {const_name}{type_ann} = {const_value}")

            # Class symbols with members
            for sym in getattr(comp, "symbols", []) or []:
                sym_name = getattr(sym, "name", str(sym))
                sym_kind = getattr(sym, "kind", "")
                if sym_kind == "class" or (hasattr(sym, "supers") and sym.supers):
                    supers = getattr(sym, "supers", []) or []
                    members = getattr(sym, "members", []) or []
                    bases_str = f"({', '.join(supers)})" if supers else ""
                    section_lines.append(f"  class {sym_name}{bases_str}:")
                    for member in members[:15]:  # Cap at 15 members
                        section_lines.append(f"    .{member}")

            # Function signatures (interface only — no body_hint for deps)
            for sig in getattr(comp, "signatures", []) or []:
                sig_name = getattr(sig, "name", str(sig))
                params = getattr(sig, "params", []) or []
                returns = getattr(sig, "returns", "")
                params_str = ", ".join(params)
                ret_str = f" -> {returns}" if returns else ""
                section_lines.append(f"  def {sig_name}({params_str}){ret_str}")

        parts.append("\n".join(section_lines))

    return "\n\n".join(parts)
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_dependency_context.py -v` (from opencode-arch)
Expected: ALL PASS

**Step 3: Run full test suite**

Run: `pytest tests/ -v` (from opencode-arch)
Expected: No new failures

**Step 4: Commit**

```bash
git add src/opencode_arch/cli/regen_loop.py tests/test_dependency_context.py
git commit -m "feat: rich dependency context with API surface for blind regen"
```

---

## Part C: Integration Test — Verify tqdm Gets Contracts

### Task 5: Verify tqdm mapping improvement

**Step 1: Run compose_enriched_model on tqdm and check contract counts**

```python
# Quick verification script (not committed)
from architecture_model.core.merger import compose_enriched_model
from pathlib import Path

model = compose_enriched_model(Path("/tmp/test-repos/tqdm"))
for comp in model.entities.components:
    contracts = getattr(comp, "test_contracts", []) or []
    if contracts:
        print(f"{comp.name}: {len(contracts)} contracts")
```

Expected: Components like `std`, `utils`, `cli` should now have test contracts mapped from `tests_tqdm.py`.

**Step 2: Re-run blind regen on a tqdm subsystem that previously had 0 contracts**

This validates the full pipeline improvement end-to-end.

---

## Execution Order

1. Task 1-2 (Part A) — independent, architecture-model-standard only
2. Task 3-4 (Part B) — independent, opencode-arch only
3. Task 5 (Part C) — depends on Part A completion

Parts A and B can be executed in parallel.
