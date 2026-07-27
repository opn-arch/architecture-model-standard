# Model Coverage Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `coverage` command that compares the architecture model against a fresh manifest scan to report how accurately the model represents the actual codebase.

**Architecture:** New `core/coverage.py` module with a `coverage_report(model, manifest)` function that performs 5 coverage checks (components, relationships, capabilities, interfaces, staleness). CLI command `coverage` wires it together. The manifest is generated on-the-fly if not provided.

**Tech Stack:** Python dataclasses, pathlib, hashlib (for manifest hash comparison)

---

### Task 1: CoverageResult Dataclass + Skeleton

**Files:**
- Create: `src/architecture_model/core/coverage.py`
- Test: `tests/test_coverage.py`

**Step 1: Write the failing test**

```python
"""Tests for model coverage analysis."""
from architecture_model.core.coverage import CoverageResult, CoverageCheck, coverage_report
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Capability,
    Interface, Relationship, RelationType, Status, InterfaceType,
    Layer, Constraint,
)


def _minimal_model():
    """Model with 2 components, 1 capability, 1 interface, 1 depends-on."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.4", project="test", source_artifacts=["test"]),
        entities=Entities(
            components=[
                Component(id="COMP-CORE", name="core", status=Status.ACTIVE),
                Component(id="COMP-CLI", name="cli", status=Status.ACTIVE),
            ],
            capabilities=[
                Capability(id="CAP-F1", name="Parsing", status=Status.ACTIVE, f_block="F1"),
            ],
            interfaces=[
                Interface(id="IF-API", name="Parser API", status=Status.ACTIVE, type=InterfaceType.REST),
            ],
            layers=[
                Layer(id="L-APP", name="Application", status=Status.ACTIVE),
            ],
            constraints=[
                Constraint(id="CON-1", name="Schema", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.REALIZES, from_id="COMP-CORE", to_id="CAP-F1"),
            Relationship(type=RelationType.EXPOSES, from_id="COMP-CORE", to_id="IF-API"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-CLI", to_id="COMP-CORE"),
            Relationship(type=RelationType.CONTAINS, from_id="L-APP", to_id="COMP-CORE"),
            Relationship(type=RelationType.CONTAINS, from_id="L-APP", to_id="COMP-CLI"),
            Relationship(type=RelationType.CONSTRAINED_BY, from_id="COMP-CORE", to_id="CON-1"),
        ],
    )


def _minimal_manifest():
    """Manifest with 3 modules (core, cli, config) and import edges."""
    return {
        "generated_at": "2026-07-11T00:00:00Z",
        "project_root": "/tmp/test",
        "metrics": {"total_files": 3},
        "modules": [
            {"file": "src/pkg/core.py", "name": "core", "functions": ["load", "parse"], "imports": ["config"], "line_count": 200, "classes": [], "exports": ["load", "parse"]},
            {"file": "src/pkg/cli.py", "name": "cli", "functions": ["main"], "imports": ["core"], "line_count": 50, "classes": [], "exports": ["main"]},
            {"file": "src/pkg/config.py", "name": "config", "functions": ["discover"], "imports": [], "line_count": 80, "classes": [], "exports": ["discover"]},
        ],
        "functional_blocks": {
            "F1": {"sub_functions": [{"file": "src/pkg/core.py"}]},
            "F2": {"sub_functions": [{"file": "src/pkg/config.py"}]},
        },
        "interfaces": [
            {"source": "src/pkg/cli.py", "target": "src/pkg/core.py", "import_path": "pkg.core"},
            {"source": "src/pkg/core.py", "target": "src/pkg/config.py", "import_path": "pkg.config"},
        ],
    }


class TestCoverageResult:
    def test_result_has_checks(self):
        result = CoverageResult(checks=[], overall_score=100.0)
        assert result.overall_score == 100.0
        assert result.checks == []

    def test_check_dataclass(self):
        check = CoverageCheck(
            name="component_coverage",
            score=80.0,
            matched=4,
            total=5,
            missing=["config"],
            extra=[],
        )
        assert check.score == 80.0
        assert check.missing == ["config"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_coverage.py -v --ignore=tests/test_config_loader.py`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

```python
"""Coverage analysis: compare architecture model against code reality (manifest)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CoverageCheck:
    """Result of a single coverage check."""
    name: str
    score: float  # 0-100
    matched: int
    total: int
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    details: str = ""


@dataclass
class CoverageResult:
    """Aggregate coverage report."""
    checks: list[CoverageCheck] = field(default_factory=list)
    overall_score: float = 0.0

    def summary(self) -> str:
        lines = ["Model Coverage Report", "=" * 40]
        for c in self.checks:
            status = "✓" if c.score == 100 else "△" if c.score >= 80 else "✗"
            lines.append(f"  {status} {c.name}: {c.matched}/{c.total} ({c.score:.0f}%)")
            for m in c.missing:
                lines.append(f"      ⚠ Missing: {m}")
            for e in c.extra:
                lines.append(f"      ⊕ Extra (not in code): {e}")
        lines.append(f"\nOverall accuracy: {self.overall_score:.0f}%")
        return "\n".join(lines)


def coverage_report(model, manifest: dict) -> CoverageResult:
    """Compare model against manifest and return coverage analysis."""
    raise NotImplementedError("Task 2+")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_coverage.py -v --ignore=tests/test_config_loader.py`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/architecture_model/core/coverage.py tests/test_coverage.py
git commit -m "feat: add CoverageResult/CoverageCheck dataclasses for model accuracy analysis"
```

---

### Task 2: Component Coverage Check

**Files:**
- Modify: `src/architecture_model/core/coverage.py`
- Modify: `tests/test_coverage.py`

**Step 1: Write the failing test**

Add to `tests/test_coverage.py`:

```python
class TestComponentCoverage:
    def test_full_coverage(self):
        """All manifest modules have matching model components."""
        model = _minimal_model()
        model.entities.components.append(
            Component(id="COMP-CONFIG", name="config", status=Status.ACTIVE)
        )
        manifest = _minimal_manifest()
        result = coverage_report(model, manifest)
        comp_check = next(c for c in result.checks if c.name == "component_coverage")
        assert comp_check.score == 100.0
        assert comp_check.matched == 3
        assert comp_check.missing == []

    def test_missing_component(self):
        """Manifest has 'config' module not in model."""
        model = _minimal_model()
        manifest = _minimal_manifest()
        result = coverage_report(model, manifest)
        comp_check = next(c for c in result.checks if c.name == "component_coverage")
        assert comp_check.score < 100.0
        assert "config" in comp_check.missing

    def test_extra_component(self):
        """Model has component not in manifest."""
        model = _minimal_model()
        model.entities.components.append(
            Component(id="COMP-EXTRA", name="extra", status=Status.ACTIVE)
        )
        manifest = _minimal_manifest()
        result = coverage_report(model, manifest)
        comp_check = next(c for c in result.checks if c.name == "component_coverage")
        assert "extra" in comp_check.extra
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_coverage.py::TestComponentCoverage -v`
Expected: FAIL (NotImplementedError)

**Step 3: Implement component coverage check**

```python
from pathlib import Path
from .types import ArchitectureModel


def _check_component_coverage(model: ArchitectureModel, manifest: dict) -> CoverageCheck:
    """Check that manifest modules are represented as model components."""
    manifest_modules = set()
    for mod in manifest.get("modules", []):
        stem = Path(mod["file"]).stem
        if stem != "__init__":
            manifest_modules.add(stem)

    model_components = {}
    for comp in model.entities.components:
        model_components[comp.name.lower()] = comp.id

    matched, missing = [], []
    for mod_name in sorted(manifest_modules):
        if mod_name.lower() in model_components:
            matched.append(mod_name)
        else:
            missing.append(mod_name)

    extra = [n for n in sorted(model_components) if n not in {m.lower() for m in manifest_modules}]
    total = len(manifest_modules)
    score = (len(matched) / total * 100) if total else 100.0

    return CoverageCheck(name="component_coverage", score=score, matched=len(matched),
                         total=total, missing=missing, extra=extra)


def coverage_report(model: ArchitectureModel, manifest: dict) -> CoverageResult:
    checks = [_check_component_coverage(model, manifest)]
    overall = sum(c.score for c in checks) / len(checks) if checks else 0.0
    return CoverageResult(checks=checks, overall_score=overall)
```

**Step 4: Run tests, Step 5: Commit**

---

### Task 3: Relationship Accuracy Check (Import Graph)

**Files:**
- Modify: `src/architecture_model/core/coverage.py`
- Modify: `tests/test_coverage.py`

**Step 1: Write the failing test**

```python
class TestRelationshipAccuracy:
    def test_matching_dependencies(self):
        model = _minimal_model()  # CLI->CORE dependency
        manifest = _minimal_manifest()  # cli.py imports core.py
        result = coverage_report(model, manifest)
        rel_check = next(c for c in result.checks if c.name == "relationship_accuracy")
        assert rel_check.matched >= 1

    def test_missing_dependency(self):
        model = _minimal_model()  # no CORE->CONFIG dependency
        manifest = _minimal_manifest()  # core.py imports config.py
        result = coverage_report(model, manifest)
        rel_check = next(c for c in result.checks if c.name == "relationship_accuracy")
        assert any("config" in m.lower() for m in rel_check.missing)
```

**Step 3: Implement**

```python
def _check_relationship_accuracy(model: ArchitectureModel, manifest: dict) -> CoverageCheck:
    from .types import RelationType

    manifest_edges: set[tuple[str, str]] = set()
    for iface in manifest.get("interfaces", []):
        src, tgt = Path(iface["source"]).stem, Path(iface["target"]).stem
        if src != "__init__" and tgt != "__init__":
            manifest_edges.add((src.lower(), tgt.lower()))

    id_to_name = {c.id: c.name.lower() for c in model.entities.components}
    model_edges: set[tuple[str, str]] = set()
    for rel in model.relationships:
        if rel.type == RelationType.DEPENDS_ON:
            src, tgt = id_to_name.get(rel.from_id), id_to_name.get(rel.to_id)
            if src and tgt:
                model_edges.add((src, tgt))

    matched = sorted(manifest_edges & model_edges)
    missing = sorted(manifest_edges - model_edges)
    extra = sorted(model_edges - manifest_edges)
    total = len(manifest_edges)
    score = (len(matched) / total * 100) if total else 100.0

    return CoverageCheck(name="relationship_accuracy", score=score, matched=len(matched),
                         total=total, missing=[f"{s} → {t}" for s, t in missing],
                         extra=[f"{s} → {t}" for s, t in extra])
```

---

### Task 4: Capability Coverage Check

**Step 1: Test**

```python
class TestCapabilityCoverage:
    def test_all_fblocks_covered(self):
        model = _minimal_model()
        model.entities.capabilities.append(
            Capability(id="CAP-F2", name="Config", status=Status.ACTIVE, f_block="F2"))
        manifest = _minimal_manifest()
        result = coverage_report(model, manifest)
        cap_check = next(c for c in result.checks if c.name == "capability_coverage")
        assert cap_check.score == 100.0

    def test_missing_fblock(self):
        model = _minimal_model()
        manifest = _minimal_manifest()
        result = coverage_report(model, manifest)
        cap_check = next(c for c in result.checks if c.name == "capability_coverage")
        assert "F2" in cap_check.missing
```

**Step 3: Implement**

```python
def _check_capability_coverage(model: ArchitectureModel, manifest: dict) -> CoverageCheck:
    manifest_fblocks = set(manifest.get("functional_blocks", {}).keys())
    model_fblocks = {cap.f_block for cap in model.entities.capabilities if cap.f_block}
    matched = sorted(manifest_fblocks & model_fblocks)
    missing = sorted(manifest_fblocks - model_fblocks)
    total = len(manifest_fblocks)
    score = (len(matched) / total * 100) if total else 100.0
    return CoverageCheck(name="capability_coverage", score=score, matched=len(matched),
                         total=total, missing=missing, extra=sorted(model_fblocks - manifest_fblocks))
```

---

### Task 5: Interface Coverage Check

**Step 1: Test**

```python
class TestInterfaceCoverage:
    def test_module_with_exports_but_no_interface(self):
        model = _minimal_model()
        model.relationships = [r for r in model.relationships if r.type != RelationType.EXPOSES]
        model.entities.interfaces = []
        manifest = _minimal_manifest()
        result = coverage_report(model, manifest)
        iface_check = next(c for c in result.checks if c.name == "interface_coverage")
        assert iface_check.score < 100.0
```

**Step 3: Implement** — Check modules with `exports` have corresponding component with `exposes` relationship.

---

### Task 6: Staleness Check

**Step 1: Test**

```python
import hashlib, json

class TestStalenessCheck:
    def test_current_hash(self):
        manifest = _minimal_manifest()
        h = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
        model = _minimal_model()
        model.meta.manifest_hash = h
        result = coverage_report(model, manifest)
        stale = next(c for c in result.checks if c.name == "staleness")
        assert stale.score == 100.0

    def test_stale_hash(self):
        model = _minimal_model()
        model.meta.manifest_hash = "old_hash"
        result = coverage_report(model, _minimal_manifest())
        stale = next(c for c in result.checks if c.name == "staleness")
        assert stale.score == 0.0
```

---

### Task 7: CLI Command

Add `coverage` subparser to `cli/main.py`. Handler generates manifest on-the-fly if `--manifest` not provided, runs `coverage_report`, prints `result.summary()`, returns 0 if score >= 80, else 1.

---

### Task 8: Export + Full Test Suite

Add `coverage_report, CoverageResult` to `__init__.py`. Run full suite: `pytest tests/ -v --ignore=tests/test_config_loader.py`. Run on own model: `architecture-model coverage .architecture-model.yaml`.

---

### Task 9: Update CONTEXT.md

Add coverage command to CLI list, add `coverage_report` to Key APIs, update test count.
