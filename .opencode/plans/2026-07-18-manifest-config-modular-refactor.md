# Manifest + Config Modular Refactor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor `manifest/` and `config/` modules to embody the architecture-model-standard's own principles — proper functional decomposition with typed interfaces, structured logging, metrics/success criteria, and observability at every function boundary.

**Architecture:** Replace all raw `dict` returns with typed dataclasses. Add structured logging via Python's `logging` module. Introduce report dataclasses (`ScanReport`, `DiscoveryReport`) returned alongside results so callers can inspect success/failure metrics. Extract duplicated file-discovery logic into a shared `utils/` module.

**Tech Stack:** Python dataclasses, Python `logging`, existing test infrastructure (`pytest`)

---

## Phase 0: Shared Utils Extraction

### Task 1: Create `src/architecture_model/utils/` with shared file discovery

**Files:**
- Create: `src/architecture_model/utils/__init__.py`
- Create: `src/architecture_model/utils/discovery.py`
- Create: `tests/test_utils/__init__.py`
- Create: `tests/test_utils/test_discovery.py`

**Context:** Currently duplicated across 4 files:
- `manifest/scanner.py`: `_collect_py_files()` (excludes `__pycache__` only)
- `config/loader.py`: `_get_code_subdirectories()`, `_find_source_root()` (excludes 14+ dirs)
- `core/merger.py`: `_discover_source_files()`, `_discover_test_files()`, `_is_source_file()`, `_is_test_file()`, `_EXCLUDED_DIRS`
- `core/decomposer.py`: `_discover_source_files()`, `_discover_test_files()`, `_is_excluded()`, `_EXCLUDED_DIRS`

**Step 1: Write failing tests**

```python
# tests/test_utils/test_discovery.py
import pytest
from pathlib import Path

from architecture_model.utils.discovery import (
    collect_py_files,
    discover_source_files,
    discover_test_files,
    is_excluded_dir,
    EXCLUDED_DIRS,
)


def test_excluded_dirs_contains_common_patterns():
    for d in ("__pycache__", ".git", "venv", ".venv", "node_modules", ".tox", ".eggs"):
        assert d in EXCLUDED_DIRS


def test_collect_py_files_excludes_pycache(tmp_path):
    (tmp_path / "good.py").write_text("x = 1")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "bad.cpython-311.pyc").write_text("")
    result = collect_py_files(tmp_path)
    assert len(result) == 1
    assert result[0].name == "good.py"


def test_collect_py_files_recursive(tmp_path):
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("x = 1")
    (tmp_path / "top.py").write_text("x = 1")
    result = collect_py_files(tmp_path, recursive=True)
    assert len(result) == 2


def test_is_excluded_dir():
    assert is_excluded_dir(Path("__pycache__")) is True
    assert is_excluded_dir(Path(".git")) is True
    assert is_excluded_dir(Path("mypackage")) is False


def test_discover_source_files_skips_tests(tmp_path):
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "mod.py").write_text("x = 1")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("x = 1")
    result = discover_source_files(tmp_path)
    assert all("test_" not in f.name for f in result)


def test_discover_test_files(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("x = 1")
    (tests / "helper.py").write_text("x = 1")
    result = discover_test_files(tmp_path)
    assert len(result) == 1
    assert result[0].name == "test_mod.py"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_utils/test_discovery.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/utils/__init__.py
"""Shared utilities for architecture-model-standard."""

# src/architecture_model/utils/discovery.py
"""Shared file discovery and exclusion logic.

Consolidates duplicated file-discovery patterns from manifest/scanner,
config/loader, core/merger, and core/decomposer.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXCLUDED_DIRS: frozenset[str] = frozenset({
    "__pycache__", ".git", ".hg", ".svn",
    "venv", ".venv", "env", ".env",
    "node_modules",
    ".eggs", ".tox", ".nox", ".mypy_cache", ".pytest_cache",
    "htmlcov", "build", "dist", ".build",
    "alembic",
})


def is_excluded_dir(path: Path) -> bool:
    """Check if a directory path should be excluded from scanning."""
    name = path.name
    return name in EXCLUDED_DIRS or name.startswith(".")


def collect_py_files(
    directory: Path,
    recursive: bool = True,
    exclude_init: bool = False,
) -> list[Path]:
    """Collect Python files from a directory.

    Args:
        directory: Directory to scan.
        recursive: Whether to recurse into subdirectories.
        exclude_init: Whether to exclude __init__.py files.

    Returns:
        Sorted list of .py file paths.
    """
    if not directory.is_dir():
        logger.debug("Directory does not exist: %s", directory)
        return []

    glob_fn = directory.rglob if recursive else directory.glob
    files = sorted(
        p for p in glob_fn("*.py")
        if not any(part in EXCLUDED_DIRS for part in p.parts)
        and (not exclude_init or p.name != "__init__.py")
    )
    logger.debug("Collected %d .py files from %s (recursive=%s)", len(files), directory, recursive)
    return files


def discover_source_files(project_root: Path) -> list[Path]:
    """Discover all source (non-test) Python files in a project."""
    all_py = collect_py_files(project_root, recursive=True)
    sources = [f for f in all_py if not _is_test_file(f, project_root)]
    logger.info("Discovered %d source files (of %d total .py)", len(sources), len(all_py))
    return sources


def discover_test_files(project_root: Path) -> list[Path]:
    """Discover all test Python files in a project."""
    all_py = collect_py_files(project_root, recursive=True)
    tests = [f for f in all_py if _is_test_file(f, project_root)]
    logger.info("Discovered %d test files", len(tests))
    return tests


def _is_test_file(path: Path, project_root: Path) -> bool:
    """Check if a file is a test file by name or location."""
    rel = path.relative_to(project_root)
    parts = rel.parts
    if any(p in ("tests", "test") for p in parts):
        return True
    return path.name.startswith("test_") or path.name.endswith("_test.py")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_utils/test_discovery.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/architecture_model/utils/ tests/test_utils/
git commit -m "refactor: extract shared file discovery utils from 4 modules"
```

---

## Phase 1: Manifest Scanner Typed Outputs

### Task 2: Define scanner dataclasses in `manifest/types.py`

**Files:**
- Create: `src/architecture_model/manifest/types.py`
- Create: `tests/test_manifest_types.py`

**Context:** `scanner.py` currently returns raw `dict` from `_scan_file()` with keys: `file`, `name`, `docstring`, `functions`, `imports`, `line_count`, `status`, `classes`, `exports`, `decorated_functions`, `imports_detailed`, `module_constants`, `module_assignments`. These need typed dataclasses.

**Step 1: Write failing tests**

```python
# tests/test_manifest_types.py
from architecture_model.manifest.types import (
    ModuleInfo,
    ClassInfo,
    FunctionInfo,
    ImportDetail,
    DecoratedFunction,
    InterfaceEdge,
    BlockManifest,
    SubFunctionEntry,
    ScanReport,
    MetricsResult,
    Manifest,
    ModuleStatus,
)


def test_module_info_creation():
    m = ModuleInfo(
        file="src/foo.py",
        name="Foo Module",
        docstring="Does foo things",
        functions=[FunctionInfo(name="bar", signature="bar(x: int) -> str")],
        imports=["os", "sys"],
        line_count=100,
        status=ModuleStatus.ACTIVE,
        classes=[],
        exports=["bar"],
        decorated_functions=[],
        imports_detailed=[],
        module_constants={"FOO": "'bar'"},
        module_assignments={},
    )
    assert m.file == "src/foo.py"
    assert m.status == ModuleStatus.ACTIVE
    assert len(m.functions) == 1


def test_module_status_thresholds():
    assert ModuleStatus.ACTIVE.value == "active"
    assert ModuleStatus.DORMANT.value == "dormant"
    assert ModuleStatus.MISSING.value == "missing"


def test_scan_report_tracks_metrics():
    r = ScanReport()
    r.files_attempted = 10
    r.files_succeeded = 9
    r.files_failed = 1
    r.parse_errors = ["syntax error in bad.py"]
    assert r.success_rate == 0.9


def test_interface_edge_creation():
    e = InterfaceEdge(source="a/b.py", target="c/d.py", import_path="c.d")
    assert e.source == "a/b.py"


def test_manifest_creation():
    m = Manifest(
        generated_at="2026-07-18T00:00:00",
        project_root="/tmp/test",
        metrics=MetricsResult(values={"total_python_files": 10}),
        functional_blocks={},
        modules=[],
        interfaces=[],
        scan_report=ScanReport(),
    )
    assert m.metrics.values["total_python_files"] == 10


def test_manifest_to_dict_backward_compat():
    """Manifest.to_dict() must produce the same shape as the old raw dict."""
    m = Manifest(
        generated_at="2026-07-18T00:00:00",
        project_root="/tmp/test",
        metrics=MetricsResult(values={"total_python_files": 10}),
        functional_blocks={},
        modules=[],
        interfaces=[],
        scan_report=ScanReport(),
    )
    d = m.to_dict()
    assert "generated_at" in d
    assert "metrics" in d
    assert isinstance(d["metrics"], dict)
    assert "scan_report" not in d  # internal, not serialized to legacy format
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_manifest_types.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/manifest/types.py
"""Typed dataclasses for manifest generation outputs.

Every function in the manifest pipeline should accept and return
typed objects, not raw dicts. This module defines those types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModuleStatus(str, Enum):
    """Status of a scanned module based on line count."""
    ACTIVE = "active"
    DORMANT = "dormant"
    MISSING = "missing"


@dataclass
class FunctionInfo:
    """A public function extracted from AST."""
    name: str
    signature: str


@dataclass
class ClassInfo:
    """A class extracted from AST."""
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    is_abstract: bool = False
    decorators: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class ImportDetail:
    """A detailed import statement."""
    module: str
    symbols: list[str] = field(default_factory=list)
    is_relative: bool = False


@dataclass
class DecoratedFunction:
    """A function with non-trivial decorators."""
    name: str
    decorators: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: str | None = None


@dataclass
class ModuleInfo:
    """Complete metadata for a single scanned Python file."""
    file: str
    name: str
    docstring: str | None
    functions: list[FunctionInfo]
    imports: list[str]
    line_count: int
    status: ModuleStatus
    classes: list[ClassInfo]
    exports: list[str] = field(default_factory=list)
    decorated_functions: list[DecoratedFunction] = field(default_factory=list)
    imports_detailed: list[ImportDetail] = field(default_factory=list)
    module_constants: dict[str, str] = field(default_factory=dict)
    module_assignments: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for backward compatibility."""
        return {
            "file": self.file,
            "name": self.name,
            "docstring": self.docstring,
            "functions": [{"name": f.name, "signature": f.signature} for f in self.functions],
            "imports": self.imports,
            "line_count": self.line_count,
            "status": self.status.value,
            "classes": [
                {
                    "name": c.name, "bases": c.bases, "methods": c.methods,
                    "is_abstract": c.is_abstract, "decorators": c.decorators,
                    "attributes": c.attributes,
                }
                for c in self.classes
            ],
            "exports": self.exports,
            "decorated_functions": [
                {"name": d.name, "decorators": d.decorators,
                 "is_method": d.is_method, "class_name": d.class_name}
                for d in self.decorated_functions
            ],
            "imports_detailed": [
                {"module": i.module, "symbols": i.symbols, "is_relative": i.is_relative}
                for i in self.imports_detailed
            ],
            "module_constants": self.module_constants,
            "module_assignments": self.module_assignments,
        }


@dataclass
class InterfaceEdge:
    """A directed dependency between two modules."""
    source: str
    target: str
    import_path: str

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "target": self.target, "import_path": self.import_path}


@dataclass
class SubFunctionEntry:
    """A file-level entry within a functional block."""
    id: str
    name: str
    file: str
    functions: list[str]
    inputs: list[str]
    outputs: list[str]
    status: str
    line_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "file": self.file,
            "functions": self.functions, "inputs": self.inputs,
            "outputs": self.outputs, "status": self.status,
            "line_count": self.line_count,
        }


@dataclass
class BlockManifest:
    """Manifest data for a single functional block."""
    name: str
    status: str
    description_source: str
    sub_functions: list[SubFunctionEntry] = field(default_factory=list)
    sub_blocks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "status": self.status,
            "description_source": self.description_source,
            "sub_functions": [sf.to_dict() for sf in self.sub_functions],
            "sub_blocks": self.sub_blocks,
        }


@dataclass
class MetricsResult:
    """Project-level metrics from glob counting."""
    values: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, int]:
        return dict(self.values)


@dataclass
class ScanReport:
    """Observability report for a manifest scan operation."""
    files_attempted: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    parse_errors: list[str] = field(default_factory=list)
    functions_extracted: int = 0
    classes_extracted: int = 0
    constants_extracted: int = 0
    interfaces_derived: int = 0
    blocks_processed: int = 0
    unclaimed_files: int = 0

    @property
    def success_rate(self) -> float:
        if self.files_attempted == 0:
            return 1.0
        return self.files_succeeded / self.files_attempted

    def log_summary(self) -> None:
        logger.info(
            "Scan complete: %d/%d files (%.1f%%), %d funcs, %d classes, "
            "%d constants, %d interfaces, %d blocks, %d unclaimed, %d errors",
            self.files_succeeded, self.files_attempted, self.success_rate * 100,
            self.functions_extracted, self.classes_extracted,
            self.constants_extracted, self.interfaces_derived,
            self.blocks_processed, self.unclaimed_files, len(self.parse_errors),
        )


@dataclass
class Manifest:
    """Complete reality manifest with typed fields and observability."""
    generated_at: str
    project_root: str
    metrics: MetricsResult
    functional_blocks: dict[str, BlockManifest]
    modules: list[ModuleInfo]
    interfaces: list[InterfaceEdge]
    scan_report: ScanReport = field(default_factory=ScanReport)

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for JSON serialization."""
        return {
            "generated_at": self.generated_at,
            "project_root": self.project_root,
            "metrics": self.metrics.to_dict(),
            "functional_blocks": {k: v.to_dict() for k, v in self.functional_blocks.items()},
            "modules": [m.to_dict() for m in self.modules],
            "interfaces": [i.to_dict() for i in self.interfaces],
        }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_manifest_types.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/architecture_model/manifest/types.py tests/test_manifest_types.py
git commit -m "feat: add typed dataclasses for manifest pipeline outputs"
```

---

### Task 3: Refactor `scanner.py` to return typed objects

**Files:**
- Modify: `src/architecture_model/manifest/scanner.py`
- Create: `tests/test_scanner_typed.py`

**Context:** `_scan_file()` currently returns a raw `dict`. Refactor to return `ModuleInfo`. Replace `_collect_py_files()` with delegation to `utils.discovery.collect_py_files()`. Add logging throughout.

**Step 1: Write failing tests**

```python
# tests/test_scanner_typed.py
import pytest
from pathlib import Path
from architecture_model.manifest.types import ModuleInfo, ModuleStatus


def test_scan_file_returns_module_info(tmp_path):
    f = tmp_path / "example.py"
    f.write_text('"""Example module."""\n\ndef hello(name: str) -> str:\n    return f"hi {name}"\n')
    from architecture_model.manifest.scanner import scan_file
    result = scan_file(tmp_path, f)
    assert isinstance(result, ModuleInfo)
    assert result.status == ModuleStatus.DORMANT
    assert len(result.functions) == 1
    assert result.functions[0].name == "hello"


def test_scan_file_parse_error(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def broken(\n")
    from architecture_model.manifest.scanner import scan_file
    result = scan_file(tmp_path, f)
    assert result.status == ModuleStatus.MISSING


def test_scan_file_extracts_constants(tmp_path):
    f = tmp_path / "consts.py"
    f.write_text('FOO = "bar"\nBAZ = 42\n')
    from architecture_model.manifest.scanner import scan_file
    result = scan_file(tmp_path, f)
    assert "FOO" in result.module_constants
    assert "BAZ" in result.module_constants


def test_scan_file_backward_compat(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('"""Module."""\nx = 1\n')
    from architecture_model.manifest.scanner import scan_file
    d = scan_file(tmp_path, f).to_dict()
    required_keys = {"file", "name", "docstring", "functions", "imports",
                     "line_count", "status", "classes", "exports",
                     "decorated_functions", "imports_detailed",
                     "module_constants", "module_assignments"}
    assert required_keys.issubset(d.keys())
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scanner_typed.py -v`
Expected: FAIL (`scan_file` not found — currently named `_scan_file`)

**Step 3: Refactor scanner.py**

Key changes:
1. Rename `_scan_file` → `scan_file` (make public — it's used by 3 other modules)
2. Return `ModuleInfo` instead of `dict`
3. Add `import logging; logger = logging.getLogger(__name__)`
4. Replace `_collect_py_files` body with delegation to `utils.discovery.collect_py_files`
5. Keep `_collect_py_files` as a thin deprecated wrapper for existing callers
6. Internal extraction functions return typed objects:
   - `_extract_public_functions` → returns `list[FunctionInfo]`
   - `_extract_classes` → returns `list[ClassInfo]`
   - `_extract_imports_detailed` → returns `list[ImportDetail]`
   - `_extract_decorated_functions_from_tree` → returns `list[DecoratedFunction]`
7. Log: file scanned, parse errors, extraction counts

**Step 4: Run ALL tests**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: New tests PASS. Existing tests may need `.to_dict()` calls where they expect raw dicts.

**Step 5: Commit**

```bash
git add src/architecture_model/manifest/scanner.py tests/test_scanner_typed.py
git commit -m "refactor: scanner returns typed ModuleInfo instead of raw dict"
```

---

### Task 4: Refactor `interfaces.py` to return typed objects + logging

**Files:**
- Modify: `src/architecture_model/manifest/interfaces.py`
- Create: `tests/test_interfaces_typed.py`

**Context:** `_derive_interfaces()` returns `list[dict]`. Refactor to accept `list[ModuleInfo]` and return `list[InterfaceEdge]`.

**Step 1: Write failing tests**

```python
# tests/test_interfaces_typed.py
from architecture_model.manifest.types import ModuleInfo, ModuleStatus, InterfaceEdge


def test_derive_interfaces_returns_typed():
    from architecture_model.manifest.interfaces import derive_interfaces
    from pathlib import Path

    modules = [
        ModuleInfo(
            file="pkg/a.py", name="A", docstring=None,
            functions=[], imports=["pkg.b"], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
        ModuleInfo(
            file="pkg/b.py", name="B", docstring=None,
            functions=[], imports=[], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
    ]
    result = derive_interfaces(modules, Path("/fake"))
    assert all(isinstance(e, InterfaceEdge) for e in result)
    assert len(result) >= 1
```

**Step 2-5:** Implement, verify pass, commit.

```bash
git commit -m "refactor: interfaces returns typed InterfaceEdge list"
```

---

### Task 5: Refactor `metrics.py` to return `MetricsResult` + logging

**Files:**
- Modify: `src/architecture_model/manifest/metrics.py`
- Create: `tests/test_metrics_typed.py`

**Step 1-5:** Same TDD pattern. `_compute_metrics()` → `compute_metrics()` returning `MetricsResult`. Add logging of each metric computed.

```bash
git commit -m "refactor: metrics returns typed MetricsResult with logging"
```

---

### Task 6: Refactor `blocks.py` to return `BlockManifest` + logging

**Files:**
- Modify: `src/architecture_model/manifest/blocks.py`
- Create: `tests/test_blocks_typed.py`

**Key changes:**
1. `_process_block()` → `process_block()` returning `BlockManifest`
2. Remove module-level `FUNCTIONAL_BLOCKS` constant (import-time side effect)
3. Remove `_get_functional_blocks()` / `_load_blocks_from_config()` (replaced by `config.fblock_dict`)
4. Add logging: files per block, sub-blocks discovered, unclaimed files

**Step 1-5:** Same TDD pattern.

```bash
git commit -m "refactor: blocks returns typed BlockManifest, remove import-time side effects"
```

---

### Task 7: Refactor `generator.py` to return `Manifest` + `ScanReport`

**Files:**
- Modify: `src/architecture_model/manifest/generator.py`
- Create: `tests/test_generator_typed.py`

**Key changes:**
1. `generate_manifest()` returns `Manifest` dataclass
2. Accumulates `ScanReport` throughout the pipeline
3. `load_or_generate_manifest()` calls `manifest.to_dict()` for JSON serialization
4. Logging at each pipeline stage

**Step 1: Write failing tests**

```python
# tests/test_generator_typed.py
from pathlib import Path
from architecture_model.manifest.types import Manifest, ScanReport


def test_generate_manifest_returns_manifest(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""My package."""\n')
    (pkg / "core.py").write_text('"""Core module."""\ndef hello(): pass\n')

    from architecture_model.manifest.generator import generate_manifest
    result = generate_manifest(tmp_path)
    assert isinstance(result, Manifest)
    assert isinstance(result.scan_report, ScanReport)
    assert result.scan_report.files_attempted > 0


def test_generate_manifest_to_dict_backward_compat(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("x = 1\n")

    from architecture_model.manifest.generator import generate_manifest
    manifest = generate_manifest(tmp_path)
    d = manifest.to_dict()
    assert "generated_at" in d
    assert "metrics" in d
    assert isinstance(d["metrics"], dict)
    assert "modules" in d
    assert isinstance(d["modules"], list)
```

**Step 2-5:** Implement, verify, commit.

```bash
git commit -m "refactor: generator returns typed Manifest with ScanReport"
```

---

### Task 8: Update `slicers.py` to accept typed `Manifest`

**Files:**
- Modify: `src/architecture_model/manifest/slicers.py`

**Context:** All `_slice_*` functions take `manifest: dict`. Update to accept `Manifest` dataclass. Access typed attributes instead of dict keys.

No new tests — existing slicer tests should continue to pass.

**Step 1:** Update function signatures and attribute access.
**Step 2:** Run existing tests: `pytest tests/ -v --ignore=tests/test_config_loader.py`
**Step 3:** Commit.

```bash
git commit -m "refactor: slicers accept typed Manifest instead of raw dict"
```

---

## Phase 2: Config Loader Typed Outputs + Observability

### Task 9: Define `DiscoveryReport` dataclass

**Files:**
- Modify: `src/architecture_model/config/schema.py`
- Create: `tests/test_discovery_report.py`

**Step 1: Write failing tests**

```python
# tests/test_discovery_report.py
from architecture_model.config.schema import DiscoveryReport, DiscoveryCandidate


def test_discovery_report_tracks_candidates():
    r = DiscoveryReport()
    r.add_candidate("source_root", "/src/pkg", accepted=True, reason="src-layout detected")
    r.add_candidate("source_root", "/lib/pkg", accepted=False, reason="checked after src-layout match")
    assert len(r.candidates) == 2
    assert r.candidates[0].accepted is True
    assert r.candidates[1].accepted is False


def test_discovery_report_summary():
    r = DiscoveryReport()
    r.layout_detected = "src-layout"
    r.blocks_discovered = 5
    r.layers_discovered = 3
    r.metrics_discovered = 2
    r.files_total = 100
    r.files_claimed = 85
    s = r.summary()
    assert "src-layout" in s
    assert "5 blocks" in s
```

**Step 2: Implement**

```python
# Add to config/schema.py

@dataclass
class DiscoveryCandidate:
    """A candidate evaluated during config discovery."""
    category: str
    path: str
    accepted: bool
    reason: str


@dataclass
class DiscoveryReport:
    """Observability report for config discovery."""
    layout_detected: str = "unknown"
    blocks_discovered: int = 0
    layers_discovered: int = 0
    metrics_discovered: int = 0
    sub_blocks_discovered: int = 0
    files_total: int = 0
    files_claimed: int = 0
    files_unclaimed: int = 0
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_candidate(self, category: str, path: str, accepted: bool, reason: str) -> None:
        self.candidates.append(DiscoveryCandidate(category, path, accepted, reason))

    @property
    def claim_rate(self) -> float:
        if self.files_total == 0:
            return 1.0
        return self.files_claimed / self.files_total

    def summary(self) -> str:
        return (
            f"Layout: {self.layout_detected}, "
            f"{self.blocks_discovered} blocks, {self.layers_discovered} layers, "
            f"{self.metrics_discovered} metrics, "
            f"{self.files_claimed}/{self.files_total} files claimed "
            f"({self.claim_rate:.0%})"
        )
```

**Step 3-5:** Verify, commit.

```bash
git commit -m "feat: add DiscoveryReport for config discovery observability"
```

---

### Task 10: Refactor `config/loader.py` to return `(ProjectConfig, DiscoveryReport)`

**Files:**
- Modify: `src/architecture_model/config/loader.py`
- Create: `tests/test_config_discovery_typed.py`

**Key changes:**
1. `discover_config(root)` → returns `tuple[ProjectConfig, DiscoveryReport]`
2. `_find_source_root()` logs all candidates into report
3. `_discover_layers()` logs each heuristic checked
4. `_discover_functional_blocks()` logs per-block stats
5. `_discover_sub_blocks()` populates `files` list (BUG FIX: currently always `files=[]`)
6. `_get_code_subdirectories()` includes `_`-prefixed dirs (BUG FIX: currently excluded)
7. Add `import logging; logger = logging.getLogger(__name__)`
8. `get_config()` returns `tuple[ProjectConfig, DiscoveryReport | None]`
9. Replace file discovery with `utils.discovery` calls

**Step 1: Write failing tests**

```python
# tests/test_config_discovery_typed.py
from pathlib import Path


def test_discover_config_returns_report(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""My package."""\n')
    sub = pkg / "core"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "engine.py").write_text("x = 1\n")

    from architecture_model.config.loader import discover_config
    config, report = discover_config(tmp_path)
    assert config.name == tmp_path.name
    assert report.layout_detected in ("src-layout", "flat-layout", "lib-layout", "fallback")
    assert report.blocks_discovered >= 1
    assert len(report.candidates) > 0


def test_discover_config_includes_underscore_dirs(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    internal = pkg / "_internal"
    internal.mkdir()
    (internal / "__init__.py").write_text("")
    (internal / "helpers.py").write_text("x = 1\n")

    from architecture_model.config.loader import discover_config
    config, report = discover_config(tmp_path)
    block_dirs = [d for b in config.functional_blocks for d in b.dirs]
    assert any("_internal" in d for d in block_dirs)


def test_sub_blocks_have_files(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    sub = pkg / "feature"
    sub.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (sub / "__init__.py").write_text("")
    (sub / "handler.py").write_text("x = 1\n")

    from architecture_model.config.loader import discover_config
    config, report = discover_config(tmp_path)
    for block in config.functional_blocks:
        for sb in block.sub_blocks:
            if sb.dirs:
                assert len(sb.files) > 0, f"Sub-block {sb.id} has dirs but no files"
```

**Step 2-5:** Implement, verify, commit.

```bash
git commit -m "refactor: discover_config returns DiscoveryReport, fixes _prefixed dir and sub-block file bugs"
```

---

### Task 11: Update callers of refactored APIs

**Files:**
- Modify: `src/architecture_model/cli/main.py` (`_cmd_init`, `_cmd_manifest`, `_cmd_coverage`)
- Modify: `src/architecture_model/core/merger.py` (replace duplicated discovery with `utils.discovery`)
- Modify: `src/architecture_model/core/decomposer.py` (replace duplicated discovery with `utils.discovery`)
- Modify: `src/architecture_model/manifest/__init__.py` (re-export new types)

**Key changes:**
1. `_cmd_init`: unpack `(config, report)` from `discover_config()`, print report summary
2. `_cmd_manifest`: `generate_manifest()` returns `Manifest`, call `.to_dict()` for JSON, print scan report
3. `merger.py`: replace `_discover_source_files`, `_discover_test_files`, `_is_source_file`, `_is_test_file`, `_EXCLUDED_DIRS` with `utils.discovery` imports
4. `decomposer.py`: same replacements
5. `_cmd_coverage`: handle `Manifest` type, call `.to_dict()` where `coverage_report()` expects dict

**Step 1: Make changes**
**Step 2: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: ALL existing tests pass (402+), all new tests pass

**Step 3: Commit**

```bash
git commit -m "refactor: update all callers to use typed APIs, deduplicate discovery logic"
```

---

## Phase 3: Documentation Update

### Task 12: Update deep-dive docs and CONTEXT.md

**Files:**
- Modify: `docs/se/cap-f2-deep-dive.md`
- Modify: `docs/se/cap-init-config-deep-dive.md`
- Modify: `CONTEXT.md`

**Changes:**
1. Add "Modularity Principles" section to both deep-dives stating: every function should have (1) typed I/O, (2) success metrics, (3) logging, (4) defined improvement criteria
2. Write inline responses to all comments in both docs
3. Update CONTEXT.md package structure to include `utils/` and remove non-existent `integrations/` and `extract/`

```bash
git commit -m "docs: update deep-dives with modularity responses, fix CONTEXT.md"
```

---

## Summary of Changes

| Phase | Tasks | New Files | Modified Files | New Tests |
|-------|-------|-----------|----------------|-----------|
| 0 — Shared Utils | 1 | 3 | 0 | 1 file |
| 1 — Manifest Types | 2-8 | 6 test files, 1 types file | 6 manifest files | 6 files |
| 2 — Config Observability | 9-11 | 2 test files | 3 config/cli files, 2 core files | 2 files |
| 3 — Docs | 12 | 0 | 3 docs | 0 |

**Total:** ~12 tasks, ~9 new test files, ~11 modified source files

**Key outcomes:**
1. Every manifest function returns typed dataclasses, not raw dicts
2. `ScanReport` provides observability for every scan operation
3. `DiscoveryReport` provides observability for every config discovery
4. Python `logging` integrated throughout manifest + config modules
5. Duplicated file discovery consolidated in `utils/discovery.py`
6. Bug fixes: `_`-prefixed dirs included, sub-block files populated
7. Backward compat maintained via `to_dict()` methods
8. All 402+ existing tests continue to pass

---

## Phase 4: Self-Modeling (Eat Our Own Dogfood)

### Task 13: Generate this repo's own architecture model

**Files:**
- Create (via CLI): `.architecture-model.yaml`
- Modify: generated model to fill gaps

**Context:** This repo defines the architecture-model-standard but has no architecture model of itself. The standard should model itself to prove universality and serve as the reference implementation.

**Step 1: Run init on this repo**

```bash
architecture-model init .
```

Review the generated `.architecture-model.yaml`. Verify it discovers:
- Source root: `src/architecture_model/`
- F-blocks: cli, config, core, manifest, spec, utils (after Phase 0)
- Layers: derived from F-blocks (no web/service/data heuristics match)
- Metrics: total_python_files

**Step 2: Validate the generated model**

```bash
architecture-model validate .architecture-model.yaml
```

Target: 100/100 validation score.

**Step 3: Run coverage**

```bash
architecture-model coverage .architecture-model.yaml
```

Review model-vs-manifest alignment. Identify missing components, relationships, capabilities.

**Step 4: Enrich the model manually**

Add missing entities:
- **Capabilities:** CAP-F1 (Validation), CAP-F2 (Manifest Generation), CAP-F3 (Model Parsing), CAP-F4 (Context Formatting), CAP-F5 (Config Discovery)
- **Behaviors:** BEH-INIT (bootstrap), BEH-SCAN (AST scan), BEH-VALIDATE (model check), BEH-SLICE (context slicing)
- **Constraints:** CON-PYTHON-ONLY (Python AST limitation), CON-BACKWARD-COMPAT (to_dict compatibility)
- **Interfaces:** IF-CLI (CLI entry), IF-MCP (MCP server integration), IF-MANIFEST-JSON (manifest output format)
- **Relationships:** realizes, depends_on, exposes between all entities

**Step 5: Re-validate and verify**

```bash
architecture-model validate .architecture-model.yaml
architecture-model coverage .architecture-model.yaml
```

Target: 100/100 validation, >80% coverage.

**Step 6: Commit**

```bash
git add .architecture-model.yaml
git commit -m "feat: add self-model — architecture-model-standard models itself"
```

---

## Phase 5: Domain Profiles System

### Task 14: Define profile schema and dataclass

**Files:**
- Create: `src/architecture_model/profiles/`
- Create: `src/architecture_model/profiles/__init__.py`
- Create: `src/architecture_model/profiles/schema.py`
- Create: `src/architecture_model/profiles/profile-schema.json`
- Create: `tests/test_profiles/__init__.py`
- Create: `tests/test_profiles/test_profile_schema.py`

**Context:** Domain profiles allow the standard to work for controls, mechanical, electrical — not just software. A profile declares additional enum values, entity extensions (extra fields), and conditional validation rules.

**Step 1: Write failing tests**

```python
# tests/test_profiles/test_profile_schema.py
import pytest
from architecture_model.profiles.schema import (
    DomainProfile,
    EnumExtension,
    EntityExtension,
    ConditionalRule,
    load_profile,
    BUILTIN_PROFILES,
)


def test_domain_profile_creation():
    p = DomainProfile(
        domain="controls",
        extends_schema="1.4",
        enum_extensions=[
            EnumExtension(enum_name="component_kind", values=["sensor", "actuator", "controller"]),
        ],
        entity_extensions=[
            EntityExtension(
                entity_type="component",
                properties={
                    "signal_type": {"type": "string", "enum": ["analog", "digital", "fieldbus"]},
                    "sampling_rate_hz": {"type": "number"},
                },
            ),
        ],
        validation_rules=[
            ConditionalRule(
                entity_type="component",
                when={"kind": "sensor"},
                require=["signal_type"],
                message="Sensors must declare signal_type",
            ),
        ],
    )
    assert p.domain == "controls"
    assert len(p.enum_extensions) == 1
    assert "sensor" in p.enum_extensions[0].values


def test_builtin_profiles_exist():
    assert "software" in BUILTIN_PROFILES
    assert "controls" in BUILTIN_PROFILES
    assert "mechanical" in BUILTIN_PROFILES
    assert "electrical" in BUILTIN_PROFILES


def test_load_builtin_profile():
    p = load_profile("controls")
    assert p.domain == "controls"
    assert any(e.enum_name == "component_kind" for e in p.enum_extensions)


def test_load_custom_profile(tmp_path):
    import yaml
    profile_data = {
        "domain": "custom",
        "extends_schema": "1.4",
        "enum_extensions": [
            {"enum_name": "component_kind", "values": ["widget", "gadget"]},
        ],
        "entity_extensions": [],
        "validation_rules": [],
    }
    pf = tmp_path / "custom.yaml"
    pf.write_text(yaml.dump(profile_data))
    p = load_profile(str(pf))
    assert p.domain == "custom"
    assert "widget" in p.enum_extensions[0].values
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_profiles/test_profile_schema.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/profiles/__init__.py
"""Domain profiles for cross-domain architecture modeling."""

# src/architecture_model/profiles/schema.py
"""Domain profile schema and loading logic.

A domain profile extends the base architecture-model schema with:
- Additional enum values (ComponentKind, InterfaceType, etc.)
- Additional entity fields (validated via JSON Schema fragments)
- Conditional validation rules (e.g., "sensors must have signal_type")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).parent / "builtins"


@dataclass
class EnumExtension:
    """Additional values for an existing enum."""
    enum_name: str          # e.g., "component_kind", "interface_type"
    values: list[str] = field(default_factory=list)


@dataclass
class EntityExtension:
    """Additional properties for an entity type."""
    entity_type: str        # e.g., "component", "interface"
    properties: dict[str, Any] = field(default_factory=dict)  # JSON Schema fragment


@dataclass
class ConditionalRule:
    """A validation rule that applies when conditions are met."""
    entity_type: str
    when: dict[str, str] = field(default_factory=dict)     # field: value match
    require: list[str] = field(default_factory=list)        # required fields
    message: str = ""


@dataclass
class DomainProfile:
    """A domain-specific extension to the architecture-model schema."""
    domain: str
    extends_schema: str = "1.4"
    enum_extensions: list[EnumExtension] = field(default_factory=list)
    entity_extensions: list[EntityExtension] = field(default_factory=list)
    validation_rules: list[ConditionalRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainProfile:
        return cls(
            domain=data["domain"],
            extends_schema=data.get("extends_schema", "1.4"),
            enum_extensions=[
                EnumExtension(**e) for e in data.get("enum_extensions", [])
            ],
            entity_extensions=[
                EntityExtension(**e) for e in data.get("entity_extensions", [])
            ],
            validation_rules=[
                ConditionalRule(**r) for r in data.get("validation_rules", [])
            ],
        )

    def get_extended_values(self, enum_name: str) -> list[str]:
        """Get all extended values for a given enum."""
        for ext in self.enum_extensions:
            if ext.enum_name == enum_name:
                return ext.values
        return []


BUILTIN_PROFILES: dict[str, str] = {
    "software": "software.yaml",
    "controls": "controls.yaml",
    "mechanical": "mechanical.yaml",
    "electrical": "electrical.yaml",
}


def load_profile(name_or_path: str) -> DomainProfile:
    """Load a domain profile by name (builtin) or file path.

    Args:
        name_or_path: Either a builtin name ("controls") or a file path.

    Returns:
        Parsed DomainProfile.

    Raises:
        FileNotFoundError: If profile not found.
    """
    if name_or_path in BUILTIN_PROFILES:
        path = PROFILES_DIR / BUILTIN_PROFILES[name_or_path]
    else:
        path = Path(name_or_path)

    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    profile = DomainProfile.from_dict(data)
    logger.info("Loaded domain profile: %s (%d enum extensions, %d entity extensions, %d rules)",
                profile.domain, len(profile.enum_extensions),
                len(profile.entity_extensions), len(profile.validation_rules))
    return profile
```

**Step 4: Run tests — they'll fail because builtin YAML files don't exist yet (Task 18)**

Temporarily skip the `test_load_builtin_profile` test.

**Step 5: Commit**

```bash
git add src/architecture_model/profiles/ tests/test_profiles/
git commit -m "feat: add domain profile schema and loading infrastructure"
```

---

### Task 15: Open up enums in `core/types.py`

**Files:**
- Modify: `src/architecture_model/core/types.py`
- Modify: `src/architecture_model/core/parser.py`
- Create: `tests/test_open_enums.py`

**Context:** Currently, parsing a component with `kind: sensor` raises a ValueError because `sensor` isn't in `ComponentKind`. Open enums should accept unknown values gracefully.

**Step 1: Write failing tests**

```python
# tests/test_open_enums.py
from architecture_model.core.types import ComponentKind, InterfaceType, BehaviorPattern


def test_component_kind_accepts_unknown():
    """Unknown kinds should be accepted as string values, not raise."""
    result = ComponentKind.parse("sensor")
    assert result == "sensor"  # string fallback, not enum member


def test_component_kind_known_returns_enum():
    result = ComponentKind.parse("service")
    assert result == ComponentKind.SERVICE


def test_interface_type_accepts_unknown():
    result = InterfaceType.parse("fieldbus")
    assert result == "fieldbus"


def test_behavior_pattern_accepts_unknown():
    result = BehaviorPattern.parse("feedback-loop")
    assert result == "feedback-loop"


def test_parser_accepts_unknown_kind():
    """The parser should not crash on unknown component kinds."""
    import yaml
    from architecture_model.core.parser import _parse_raw

    raw = yaml.safe_load("""
    meta:
      project: test
      schema_version: '1.4'
    entities:
      components:
        - id: COMP-1
          name: Temperature Sensor
          status: ACTIVE
          kind: sensor
          layer: field-layer
          f_block: F1
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.entities.components[0].kind == "sensor"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_open_enums.py -v`
Expected: FAIL (no `parse` method on enums)

**Step 3: Implement open enum pattern**

Add a `parse` classmethod to each extensible enum:

```python
# In core/types.py, on each open enum:

class ComponentKind(str, Enum):
    SERVICE = "service"
    LIBRARY = "library"
    # ... existing values ...

    @classmethod
    def parse(cls, value: str) -> ComponentKind | str:
        """Parse a kind value, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value  # unknown domain-specific kind
```

Update `parser.py` to use `.parse()` instead of direct enum construction for `ComponentKind`, `InterfaceType`, `BehaviorPattern`, `ConstraintType`, `ActorType`, `RelationType`.

**Step 4: Run ALL tests**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: All pass (existing tests use known enum values, so no breakage)

**Step 5: Commit**

```bash
git add src/architecture_model/core/types.py src/architecture_model/core/parser.py tests/test_open_enums.py
git commit -m "feat: open enums accept unknown domain-specific values"
```

---

### Task 16: Profile-aware parsing in `core/parser.py`

**Files:**
- Modify: `src/architecture_model/core/parser.py`
- Modify: `src/architecture_model/core/types.py` (add `domain_profile` to `ModelMeta`)
- Create: `tests/test_profile_parsing.py`

**Context:** When a model declares `domain_profile: controls` in its meta, the parser should load the profile and use it to validate extended fields.

**Step 1: Write failing tests**

```python
# tests/test_profile_parsing.py
import yaml
from pathlib import Path
from architecture_model.core.parser import _parse_raw


def test_meta_includes_domain_profile():
    raw = yaml.safe_load("""
    meta:
      project: factory
      schema_version: '1.4'
      domain_profile: controls
    entities:
      components: []
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "controls"


def test_meta_domain_profile_defaults_to_software():
    raw = yaml.safe_load("""
    meta:
      project: webapp
      schema_version: '1.4'
    entities:
      components: []
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "software"
```

**Step 2-5:** Add `domain_profile: str = "software"` to `ModelMeta`, update `_parse_meta`, verify, commit.

```bash
git commit -m "feat: parser reads domain_profile from model meta"
```

---

### Task 17: Profile-aware validation in `core/validator.py`

**Files:**
- Modify: `src/architecture_model/core/validator.py`
- Create: `tests/test_profile_validation.py`

**Context:** When validating a model with `domain_profile: controls`, load the profile and apply its conditional rules (e.g., "sensors must have signal_type").

**Step 1: Write failing tests**

```python
# tests/test_profile_validation.py
import yaml
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model


def test_profile_validation_catches_missing_required_field():
    """A controls sensor without signal_type should get a validation warning."""
    raw = yaml.safe_load("""
    meta:
      project: factory
      schema_version: '1.4'
      domain_profile: controls
    entities:
      components:
        - id: COMP-1
          name: Temp Sensor
          status: ACTIVE
          kind: sensor
          layer: field-layer
          f_block: F1
    relationships: []
    """)
    model = _parse_raw(raw)
    result = validate_model(model)
    # Should have a warning about missing signal_type
    profile_issues = [i for i in result.issues if "signal_type" in i.message]
    assert len(profile_issues) > 0


def test_profile_validation_passes_with_required_field():
    """A controls sensor WITH signal_type should pass."""
    raw = yaml.safe_load("""
    meta:
      project: factory
      schema_version: '1.4'
      domain_profile: controls
    entities:
      components:
        - id: COMP-1
          name: Temp Sensor
          status: ACTIVE
          kind: sensor
          layer: field-layer
          f_block: F1
          extensions:
            signal_type: analog
    relationships: []
    """)
    model = _parse_raw(raw)
    result = validate_model(model)
    profile_issues = [i for i in result.issues if "signal_type" in i.message]
    assert len(profile_issues) == 0
```

**Step 2: Implement**

Add `_check_domain_profile(model, result)` to `validate_model()`:
1. Load profile via `load_profile(model.meta.domain_profile)`
2. For each `ConditionalRule` in the profile:
   - Find entities matching `entity_type` and `when` conditions
   - Check that `require` fields exist (in entity fields or `extensions`)
   - Emit WARNING if missing

**Step 3-5:** Verify, commit.

```bash
git commit -m "feat: profile-aware validation with conditional rules"
```

---

### Task 18: Create 4 built-in domain profiles

**Files:**
- Create: `src/architecture_model/profiles/builtins/software.yaml`
- Create: `src/architecture_model/profiles/builtins/controls.yaml`
- Create: `src/architecture_model/profiles/builtins/mechanical.yaml`
- Create: `src/architecture_model/profiles/builtins/electrical.yaml`
- Create: `tests/test_profiles/test_builtin_profiles.py`

**Step 1: Write tests**

```python
# tests/test_profiles/test_builtin_profiles.py
import pytest
from architecture_model.profiles.schema import load_profile, BUILTIN_PROFILES


@pytest.mark.parametrize("name", list(BUILTIN_PROFILES.keys()))
def test_builtin_profile_loads(name):
    p = load_profile(name)
    assert p.domain == name
    assert p.extends_schema == "1.4"


def test_controls_profile_has_sensor_kind():
    p = load_profile("controls")
    kinds = p.get_extended_values("component_kind")
    assert "sensor" in kinds
    assert "actuator" in kinds
    assert "controller" in kinds


def test_mechanical_profile_has_assembly_kind():
    p = load_profile("mechanical")
    kinds = p.get_extended_values("component_kind")
    assert "part" in kinds
    assert "assembly" in kinds


def test_electrical_profile_has_pcb_kind():
    p = load_profile("electrical")
    kinds = p.get_extended_values("component_kind")
    assert "pcb" in kinds
    assert "connector" in kinds


def test_software_profile_is_base():
    p = load_profile("software")
    # Software profile should have no extensions (it IS the base)
    assert len(p.enum_extensions) == 0
```

**Step 2: Create profile YAML files**

```yaml
# builtins/software.yaml
domain: software
extends_schema: "1.4"
enum_extensions: []
entity_extensions: []
validation_rules: []

# builtins/controls.yaml
domain: controls
extends_schema: "1.4"
enum_extensions:
  - enum_name: component_kind
    values: [sensor, actuator, controller, hmi, plc-program, drive, relay, safety-controller]
  - enum_name: interface_type
    values: [fieldbus, signal, analog-io, digital-io, modbus, profinet, ethercat, opc-ua]
  - enum_name: behavior_pattern
    values: [feedback-loop, interlock, motion-profile, fault-tolerance, cascade-control]
  - enum_name: constraint_type
    values: [safety, timing, control-accuracy, availability]
entity_extensions:
  - entity_type: component
    properties:
      signal_type:
        type: string
        enum: [analog, digital, fieldbus, discrete]
      sampling_rate_hz:
        type: number
      safety_integrity_level:
        type: integer
        minimum: 0
        maximum: 4
      io_address:
        type: string
validation_rules:
  - entity_type: component
    when: {kind: sensor}
    require: [signal_type]
    message: "Sensors must declare signal_type (analog, digital, fieldbus, discrete)"
  - entity_type: component
    when: {kind: actuator}
    require: [signal_type]
    message: "Actuators must declare signal_type"

# builtins/mechanical.yaml
domain: mechanical
extends_schema: "1.4"
enum_extensions:
  - enum_name: component_kind
    values: [part, assembly, subassembly, fastener, fixture, bearing, gear, shaft, housing, frame]
  - enum_name: interface_type
    values: [mechanical, bolt-pattern, press-fit, weld, adhesive, threaded, keyed, splined]
  - enum_name: behavior_pattern
    values: [motion-profile, kinematic-chain, load-transfer, thermal-cycle, fatigue-cycle]
  - enum_name: constraint_type
    values: [material, load, tolerance, thermal, fatigue, weight, clearance]
  - enum_name: relationship_type
    values: [mounts-to, attaches-to, encloses, mates-with]
entity_extensions:
  - entity_type: component
    properties:
      material:
        type: string
      mass_kg:
        type: number
      dimensions_mm:
        type: object
        properties:
          length: {type: number}
          width: {type: number}
          height: {type: number}
      tolerance_class:
        type: string
        enum: [IT6, IT7, IT8, IT9, IT10, IT11, IT12]
validation_rules:
  - entity_type: component
    when: {kind: part}
    require: [material]
    message: "Parts must declare material"

# builtins/electrical.yaml
domain: electrical
extends_schema: "1.4"
enum_extensions:
  - enum_name: component_kind
    values: [pcb, connector, harness, power-supply, ic, resistor, capacitor, inductor, transformer, relay, fuse]
  - enum_name: interface_type
    values: [wire, bus, connector-pin, spi, i2c, uart, can, ethernet, usb, power-rail]
  - enum_name: behavior_pattern
    values: [power-sequencing, fault-detection, brownout-recovery, hot-swap]
  - enum_name: constraint_type
    values: [emc, thermal, power, voltage-rating, current-rating, impedance]
entity_extensions:
  - entity_type: component
    properties:
      voltage_rating_v:
        type: number
      current_rating_a:
        type: number
      power_dissipation_w:
        type: number
      package_type:
        type: string
      pin_count:
        type: integer
validation_rules:
  - entity_type: component
    when: {kind: pcb}
    require: [power_dissipation_w]
    message: "PCBs must declare power_dissipation_w for thermal analysis"
```

**Step 3: Run tests**

Run: `pytest tests/test_profiles/ -v`
Expected: ALL pass

**Step 4: Commit**

```bash
git add src/architecture_model/profiles/builtins/ tests/test_profiles/
git commit -m "feat: add 4 built-in domain profiles (software, controls, mechanical, electrical)"
```

---

## Phase 6: Integration Tests + Validation Extensions

### Task 19: End-to-end profile integration tests

**Files:**
- Create: `tests/test_profiles/test_e2e_profiles.py`

**Context:** Verify that a complete model using a domain profile can be parsed, validated, sliced, and formatted.

**Step 1: Write integration tests**

```python
# tests/test_profiles/test_e2e_profiles.py
import yaml
import pytest
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model
from architecture_model.core.slicer import slice_by_fblock


CONTROLS_MODEL = """
meta:
  project: factory-line-3
  schema_version: '1.4'
  domain_profile: controls
entities:
  actors:
    - id: ACT-1
      name: Plant Operator
      status: ACTIVE
      type: human
  capabilities:
    - id: CAP-F1
      name: Temperature Monitoring
      status: ACTIVE
      f_block: F1
      priority: high
  layers:
    - id: field-layer
      name: Field Layer
      status: ACTIVE
      order: 1
    - id: control-layer
      name: Control Layer
      status: ACTIVE
      order: 2
  components:
    - id: COMP-1
      name: Temperature Sensor
      status: ACTIVE
      kind: sensor
      layer: field-layer
      f_block: F1
      extensions:
        signal_type: analog
        sampling_rate_hz: 1000
    - id: COMP-2
      name: PID Controller
      status: ACTIVE
      kind: controller
      layer: control-layer
      f_block: F1
relationships:
  - type: realizes
    from: COMP-1
    to: CAP-F1
  - type: depends-on
    from: COMP-2
    to: COMP-1
"""


def test_controls_model_parses():
    raw = yaml.safe_load(CONTROLS_MODEL)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "controls"
    assert model.entities.components[0].kind == "sensor"
    assert model.entities.components[1].kind == "controller"


def test_controls_model_validates():
    raw = yaml.safe_load(CONTROLS_MODEL)
    model = _parse_raw(raw)
    result = validate_model(model)
    assert result.is_valid
    assert result.score >= 90


def test_controls_model_slices():
    raw = yaml.safe_load(CONTROLS_MODEL)
    model = _parse_raw(raw)
    sliced = slice_by_fblock(model, "F1")
    assert len(sliced.entities.components) == 2


MECHANICAL_MODEL = """
meta:
  project: robotic-arm
  schema_version: '1.4'
  domain_profile: mechanical
entities:
  capabilities:
    - id: CAP-F1
      name: 6-DOF Motion
      status: ACTIVE
      f_block: F1
      priority: high
  layers:
    - id: structure-layer
      name: Structural Frame
      status: ACTIVE
      order: 1
  components:
    - id: COMP-1
      name: Base Housing
      status: ACTIVE
      kind: housing
      layer: structure-layer
      f_block: F1
      extensions:
        material: aluminum-6061
        mass_kg: 12.5
    - id: COMP-2
      name: Shoulder Joint
      status: ACTIVE
      kind: assembly
      layer: structure-layer
      f_block: F1
      extensions:
        material: steel-4140
        mass_kg: 8.3
relationships:
  - type: realizes
    from: COMP-1
    to: CAP-F1
  - type: contains
    from: COMP-1
    to: COMP-2
"""


def test_mechanical_model_parses():
    raw = yaml.safe_load(MECHANICAL_MODEL)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "mechanical"
    assert model.entities.components[0].extensions["material"] == "aluminum-6061"


def test_mechanical_model_validates():
    raw = yaml.safe_load(MECHANICAL_MODEL)
    model = _parse_raw(raw)
    result = validate_model(model)
    assert result.is_valid
```

**Step 2: Run tests**

Run: `pytest tests/test_profiles/test_e2e_profiles.py -v`
Expected: ALL pass

**Step 3: Commit**

```bash
git add tests/test_profiles/test_e2e_profiles.py
git commit -m "test: end-to-end integration tests for controls and mechanical domain profiles"
```

---

### Task 20: Update documentation and CONTEXT.md for profiles

**Files:**
- Modify: `CONTEXT.md`
- Modify: `docs/se/cap-f2-deep-dive.md` (add modularity principles section)
- Modify: `docs/se/cap-init-config-deep-dive.md` (add modularity principles section)

**Changes:**
1. Add Domain Profiles section to CONTEXT.md explaining the profile system
2. Update package structure to include `profiles/`
3. Add "Modularity Principles" section to both deep-dives
4. Document the 4 built-in profiles with their enum extensions and validation rules
5. Add note about `domain_profile` field in model meta
6. Remove references to non-existent `integrations/` and `extract/` directories

```bash
git commit -m "docs: document domain profiles, update package structure, add modularity principles"
```

---

## Updated Summary of All Changes

| Phase | Tasks | New Files | Modified Files | Description |
|-------|-------|-----------|----------------|-------------|
| 0 — Shared Utils | 1 | 3 | 0 | Deduplicate file discovery from 4 modules |
| 1 — Manifest Types | 2-8 | 7 | 6 | Typed dataclasses + logging for manifest pipeline |
| 2 — Config Observability | 9-11 | 2 | 5 | DiscoveryReport + bug fixes |
| 3 — Docs (interim) | 12 | 0 | 3 | Deep-dive responses, CONTEXT.md fixes |
| 4 — Self-Modeling | 13 | 1 | 0 | This repo's own architecture model |
| 5 — Domain Profiles | 14-18 | 11 | 3 | Profile system + 4 built-in profiles |
| 6 — Integration | 19-20 | 1 | 3 | E2E tests + final docs |

**Total:** 20 tasks, ~25 new files, ~20 modified files

**Key outcomes:**
1. Every manifest function returns typed dataclasses, not raw dicts
2. `ScanReport` + `DiscoveryReport` provide full pipeline observability
3. Python `logging` integrated throughout manifest + config
4. Duplicated file discovery consolidated in `utils/discovery.py`
5. Bug fixes: `_`-prefixed dirs included, sub-block files populated
6. This repo models itself (eats its own dogfood)
7. Domain profiles enable controls, mechanical, electrical systems modeling
8. Open enums accept unknown domain-specific values without crashing
9. Profile-aware validation with conditional rules
10. 4 built-in domain profiles with enum extensions and validation rules
11. Backward compat maintained via `to_dict()` methods
12. All existing tests continue to pass
