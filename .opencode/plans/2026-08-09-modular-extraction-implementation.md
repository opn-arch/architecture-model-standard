# Modular Extraction Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the entangled 15-stage extraction pipeline with 7 independent, domain-universal modules that pursue truth with provenance, emit uncertainties, and learn over time.

**Architecture:** 7 modules (observe, infer, allocate, relate, specify, contract, validate) sharing a uniform Stage protocol. Each produces typed output with quality metrics and explicit uncertainties. A coordinator resolves dependencies and supports recursive decomposition. Project-local learning persists corrections and calibration.

**Tech Stack:** Python 3.11+, dataclasses, Protocol typing, pytest, YAML serialization (existing `ruamel.yaml`)

**Phases:**
- Phase 1: Protocol infrastructure (shared types, coordinator)
- Phase 2: File migrations from opencode-arch
- Phase 3: Module implementations (one at a time, TDD)
- Phase 4: Recursive decomposition + artifact generation
- Phase 5: Learning integration
- Phase 6: opencode-arch cleanup

---

## Phase 1: Protocol Infrastructure

### Task 1.1: Create pipeline package with protocol types

**Files:**
- Create: `src/architecture_model/pipeline/__init__.py`
- Create: `src/architecture_model/pipeline/protocol.py`
- Test: `tests/test_pipeline_protocol.py`

**Step 1: Write the failing test**

```python
# tests/test_pipeline_protocol.py
"""Tests for the pipeline protocol types."""
import pytest
from architecture_model.pipeline.protocol import (
    Evidence, Claim, Uncertainty, Diagnostic,
    QualityMetrics, StageResult, PipelineContext,
)
from pathlib import Path


class TestEvidence:
    def test_create_ast_evidence(self):
        e = Evidence(source="ast", confidence=0.95, raw="def login(): ...")
        assert e.source == "ast"
        assert e.confidence == 0.95

    def test_source_must_be_known_type(self):
        # Valid sources
        for s in ("ast", "documentation", "llm_analysis", "user_confirmation",
                  "git_history", "config", "test", "netlist", "cad", "plc_program",
                  "datasheet", "material_spec", "sil_assessment"):
            Evidence(source=s, confidence=0.5, raw="x")

    def test_confidence_bounds(self):
        with pytest.raises(ValueError):
            Evidence(source="ast", confidence=1.5, raw="x")
        with pytest.raises(ValueError):
            Evidence(source="ast", confidence=-0.1, raw="x")


class TestClaim:
    def test_aggregate_confidence(self):
        c = Claim(
            value="Authentication",
            evidence=[
                Evidence(source="ast", confidence=0.9, raw="route"),
                Evidence(source="documentation", confidence=0.8, raw="README"),
                Evidence(source="test", confidence=0.95, raw="test_auth.py"),
            ]
        )
        # Weighted: ast*1.0=0.9, doc*0.8=0.64, test*0.95=0.9025
        # avg = (0.9 + 0.64 + 0.9025) / 3 ≈ 0.814
        assert 0.7 < c.confidence < 0.9

    def test_empty_evidence_zero_confidence(self):
        c = Claim(value="Unknown", evidence=[])
        assert c.confidence == 0.0

    def test_uncertain_flag(self):
        c = Claim(value="Maybe Auth", evidence=[], uncertain=True)
        assert c.uncertain is True


class TestUncertainty:
    def test_create_uncertainty(self):
        u = Uncertainty(
            category="ambiguous_purpose",
            description="Module utils.py has no clear architectural role",
            context={"file": "src/utils.py"},
            suggested_fallback="ask_user",
            priority="blocking",
        )
        assert u.priority == "blocking"
        assert u.suggested_fallback == "ask_user"


class TestQualityMetrics:
    def test_passes_when_all_above_threshold(self):
        qm = QualityMetrics(
            score=85.0,
            sub_scores={"coverage": 95.0, "density": 4.0},
            thresholds={"coverage": 90.0, "density": 3.0},
        )
        assert qm.passes is True

    def test_fails_when_below_threshold(self):
        qm = QualityMetrics(
            score=60.0,
            sub_scores={"coverage": 80.0},
            thresholds={"coverage": 90.0},
        )
        assert qm.passes is False


class TestStageResult:
    def test_create_result(self):
        r = StageResult(
            output={"modules": []},
            quality=QualityMetrics(score=90, sub_scores={}, thresholds={}),
            diagnostics=[],
            uncertainties=[],
            input_hash="abc123",
            duration_ms=150,
            version="1.0",
        )
        assert r.output == {"modules": []}
        assert r.duration_ms == 150


class TestPipelineContext:
    def test_create_context(self, tmp_path):
        ctx = PipelineContext(
            repo_path=tmp_path,
            output_dir=tmp_path / ".architecture",
            domain="software",
        )
        assert ctx.domain == "software"
        assert ctx.scope == ""

    def test_cache_operations(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        assert ctx.has("observe") is False
        result = StageResult(
            output={}, quality=QualityMetrics(score=90, sub_scores={}, thresholds={}),
            diagnostics=[], uncertainties=[], input_hash="x", duration_ms=0, version="1.0"
        )
        ctx.cache["observe"] = result
        assert ctx.has("observe") is True
        assert ctx.get("observe") is result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'architecture_model.pipeline'`

**Step 3: Write implementation**

```python
# src/architecture_model/pipeline/__init__.py
"""Modular extraction pipeline infrastructure."""
from .protocol import (
    Evidence, Claim, Uncertainty, Diagnostic,
    QualityMetrics, StageResult, PipelineContext, Stage,
)

__all__ = [
    "Evidence", "Claim", "Uncertainty", "Diagnostic",
    "QualityMetrics", "StageResult", "PipelineContext", "Stage",
]
```

```python
# src/architecture_model/pipeline/protocol.py
"""Core protocol types for the modular extraction pipeline.

Every module in the pipeline shares these types:
- Evidence: provenance for a claim (source, confidence, raw data)
- Claim: a model assertion with evidence list
- Uncertainty: something the module couldn't determine
- Diagnostic: an issue/warning/info message
- QualityMetrics: per-stage quality scores with pass/fail thresholds
- StageResult: the complete output of a stage
- PipelineContext: shared state across pipeline stages
- Stage: the protocol (interface) every module implements
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

T = TypeVar("T")

# Valid evidence sources (extensible per domain)
EVIDENCE_SOURCES = frozenset({
    # Software
    "ast", "documentation", "llm_analysis", "user_confirmation",
    "git_history", "config", "test",
    # Electrical
    "netlist", "datasheet", "schematic",
    # Mechanical
    "cad", "material_spec", "drawing",
    # Controls
    "plc_program", "sil_assessment", "io_list",
    # Cross-domain
    "user_correction", "search_result",
})


@dataclass
class Evidence:
    """Provenance for a model claim."""
    source: str
    confidence: float  # 0.0-1.0
    raw: str           # The actual evidence
    location: str = "" # File:line or URL

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")


# Source reliability weights for confidence aggregation
SOURCE_WEIGHTS: dict[str, float] = {
    "ast": 1.0,
    "user_confirmation": 1.0,
    "user_correction": 1.0,
    "test": 0.95,
    "config": 0.9,
    "netlist": 0.95,
    "cad": 0.95,
    "plc_program": 0.95,
    "io_list": 0.9,
    "documentation": 0.8,
    "datasheet": 0.85,
    "material_spec": 0.9,
    "sil_assessment": 0.9,
    "drawing": 0.85,
    "schematic": 0.9,
    "git_history": 0.7,
    "llm_analysis": 0.6,
    "search_result": 0.5,
}


@dataclass
class Claim(Generic[T]):
    """A model assertion with provenance."""
    value: T
    evidence: list[Evidence] = field(default_factory=list)
    uncertain: bool = False

    @property
    def confidence(self) -> float:
        if not self.evidence:
            return 0.0
        total = sum(
            e.confidence * SOURCE_WEIGHTS.get(e.source, 0.5)
            for e in self.evidence
        )
        return min(1.0, total / len(self.evidence))


@dataclass
class Uncertainty:
    """Something the module couldn't determine deterministically."""
    category: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    suggested_fallback: str = "llm_analysis"  # "llm_analysis" | "search_git" | "ask_user" | "search_docs"
    priority: str = "enriching"               # "blocking" | "enriching" | "informational"


@dataclass
class Diagnostic:
    """An issue, warning, or informational message from a stage."""
    severity: str  # "error" | "warning" | "info"
    code: str      # e.g. "OBSERVE-001"
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityMetrics:
    """Per-stage quality scores with pass/fail thresholds."""
    score: float                            # 0-100 composite
    sub_scores: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    llm_prompt: str = ""

    @property
    def passes(self) -> bool:
        return all(
            self.sub_scores.get(k, 0) >= v
            for k, v in self.thresholds.items()
        )


@dataclass
class StageResult(Generic[T]):
    """Complete output of a pipeline stage."""
    output: T
    quality: QualityMetrics
    diagnostics: list[Diagnostic] = field(default_factory=list)
    uncertainties: list[Uncertainty] = field(default_factory=list)
    input_hash: str = ""
    duration_ms: int = 0
    version: str = "1.0"


@dataclass
class PipelineContext:
    """Shared state across pipeline stages."""
    repo_path: Path
    output_dir: Path
    domain: str = "software"
    scope: str = ""                         # "" = root, "COMP-X" = sub-decomposition
    config: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, StageResult] = field(default_factory=dict)
    prior_corrections: list[Evidence] = field(default_factory=list)
    calibration: dict[str, Any] = field(default_factory=dict)

    def has(self, stage_name: str) -> bool:
        return stage_name in self.cache

    def get(self, stage_name: str) -> StageResult | None:
        return self.cache.get(stage_name)


class Stage(Protocol[T]):
    """Protocol that every pipeline module implements."""
    name: str
    version: str
    requires: list[str]

    def run(self, context: PipelineContext) -> StageResult[T]: ...
    def can_run(self, context: PipelineContext) -> bool: ...
    def output_path(self, context: PipelineContext) -> Path: ...
```

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_protocol.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/ tests/test_pipeline_protocol.py
git commit -m "feat(pipeline): add protocol types — Evidence, Claim, Uncertainty, StageResult"
```

---

### Task 1.2: Create the pipeline coordinator

**Files:**
- Create: `src/architecture_model/pipeline/coordinator.py`
- Test: `tests/test_pipeline_coordinator.py`

**Step 1: Write the failing test**

```python
# tests/test_pipeline_coordinator.py
"""Tests for the pipeline coordinator (DAG resolution + execution)."""
import pytest
from pathlib import Path
from architecture_model.pipeline.protocol import (
    PipelineContext, StageResult, QualityMetrics, Stage,
)
from architecture_model.pipeline.coordinator import PipelineCoordinator


class FakeStage:
    """A fake stage for testing coordinator logic."""
    def __init__(self, name: str, requires: list[str], output: str = "done"):
        self.name = name
        self.version = "1.0"
        self.requires = requires
        self._output = output
        self.run_count = 0

    def run(self, context: PipelineContext) -> StageResult:
        self.run_count += 1
        return StageResult(
            output=self._output,
            quality=QualityMetrics(score=90, sub_scores={}, thresholds={}),
            uncertainties=[],
            diagnostics=[],
            input_hash="fake",
            duration_ms=1,
            version=self.version,
        )

    def can_run(self, context: PipelineContext) -> bool:
        return all(context.has(r) for r in self.requires)

    def output_path(self, context: PipelineContext) -> Path:
        return context.output_dir / f"{self.name}.json"


class TestCoordinator:
    def setup_method(self):
        self.observe = FakeStage("observe", [])
        self.infer = FakeStage("infer", ["observe"])
        self.allocate = FakeStage("allocate", ["observe", "infer"])
        self.relate = FakeStage("relate", ["observe", "infer", "allocate"])
        self.specify = FakeStage("specify", ["observe", "allocate"])
        self.contract = FakeStage("contract", ["observe", "allocate"])
        self.validate = FakeStage("validate", ["observe", "infer", "allocate", "relate"])

        self.coordinator = PipelineCoordinator(stages={
            "observe": self.observe,
            "infer": self.infer,
            "allocate": self.allocate,
            "relate": self.relate,
            "specify": self.specify,
            "contract": self.contract,
            "validate": self.validate,
        })

    def test_run_single_stage_no_deps(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        result = self.coordinator.run_stage("observe", ctx)
        assert result.output == "done"
        assert self.observe.run_count == 1

    def test_run_stage_resolves_deps(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        result = self.coordinator.run_stage("allocate", ctx)
        assert self.observe.run_count == 1
        assert self.infer.run_count == 1
        assert self.allocate.run_count == 1

    def test_run_to_target(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        results = self.coordinator.run_to("validate", ctx)
        assert "observe" in results
        assert "infer" in results
        assert "allocate" in results
        assert "relate" in results
        assert "validate" in results
        # specify and contract NOT run (not required by validate)
        assert self.specify.run_count == 0
        assert self.contract.run_count == 0

    def test_skips_cached_stages(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        # Pre-cache observe
        ctx.cache["observe"] = StageResult(
            output="cached", quality=QualityMetrics(score=90, sub_scores={}, thresholds={}),
            diagnostics=[], uncertainties=[], input_hash="x", duration_ms=0, version="1.0"
        )
        self.coordinator.run_stage("infer", ctx)
        assert self.observe.run_count == 0  # skipped
        assert self.infer.run_count == 1

    def test_dependency_resolution_order(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        order = self.coordinator.resolve_order("validate")
        assert order.index("observe") < order.index("infer")
        assert order.index("infer") < order.index("allocate")
        assert order.index("allocate") < order.index("relate")
        assert order.index("relate") < order.index("validate")

    def test_specify_independent_of_infer(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        order = self.coordinator.resolve_order("specify")
        assert "infer" not in order or order.index("infer") < order.index("allocate")
        # specify needs observe + allocate, allocate needs infer
        assert "observe" in order
        assert "allocate" in order

    def test_unknown_stage_raises(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        with pytest.raises(KeyError):
            self.coordinator.run_stage("nonexistent", ctx)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_coordinator.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/architecture_model/pipeline/coordinator.py
"""Pipeline coordinator — resolves dependencies, runs minimum stages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .protocol import PipelineContext, Stage, StageResult


class PipelineCoordinator:
    """Runs pipeline stages with automatic dependency resolution."""

    def __init__(self, stages: dict[str, Stage]):
        self.stages = stages

    def resolve_order(self, target: str) -> list[str]:
        """Topological sort of dependencies needed to reach target."""
        if target not in self.stages:
            raise KeyError(f"Unknown stage: {target}")

        visited: set[str] = set()
        order: list[str] = []

        def _visit(name: str):
            if name in visited:
                return
            visited.add(name)
            stage = self.stages[name]
            for dep in stage.requires:
                if dep in self.stages:
                    _visit(dep)
            order.append(name)

        _visit(target)
        return order

    def run_to(self, target: str, ctx: PipelineContext) -> dict[str, StageResult]:
        """Run minimum stages needed to produce target output."""
        order = self.resolve_order(target)
        results: dict[str, StageResult] = {}

        for stage_name in order:
            if ctx.has(stage_name):
                results[stage_name] = ctx.get(stage_name)
            else:
                result = self.stages[stage_name].run(ctx)
                ctx.cache[stage_name] = result
                results[stage_name] = result

        return results

    def run_stage(self, stage_name: str, ctx: PipelineContext) -> StageResult:
        """Run a single stage, resolving dependencies first."""
        results = self.run_to(stage_name, ctx)
        return results[stage_name]

    def run_all(self, ctx: PipelineContext) -> dict[str, StageResult]:
        """Run all stages in dependency order."""
        results: dict[str, StageResult] = {}
        # Run stages with no unresolved deps first, then work outward
        remaining = set(self.stages.keys())
        while remaining:
            runnable = [
                name for name in remaining
                if all(dep not in remaining for dep in self.stages[name].requires)
            ]
            if not runnable:
                raise RuntimeError(f"Circular dependency detected among: {remaining}")
            for name in runnable:
                if ctx.has(name):
                    results[name] = ctx.get(name)
                else:
                    result = self.stages[name].run(ctx)
                    ctx.cache[name] = result
                    results[name] = result
                remaining.discard(name)
        return results

    def run_recursive(
        self, ctx: PipelineContext, *, max_depth: int = 5, leaf_threshold: int = 5
    ) -> dict[str, Any]:
        """Run full pipeline, then recurse into large components."""
        results = self.run_all(ctx)

        # Get allocate output to find components for recursion
        allocate_result = results.get("allocate")
        if allocate_result is None or max_depth <= 0:
            return results

        # Recurse into large components
        output = allocate_result.output
        if hasattr(output, "components"):
            for comp in output.components:
                if hasattr(comp, "files") and len(comp.files) > leaf_threshold:
                    sub_ctx = PipelineContext(
                        repo_path=ctx.repo_path,
                        output_dir=ctx.output_dir / "subsystems" / comp.id,
                        domain=ctx.domain,
                        scope=comp.id,
                        config=ctx.config,
                        prior_corrections=ctx.prior_corrections,
                        calibration=ctx.calibration,
                    )
                    self.run_recursive(sub_ctx, max_depth=max_depth - 1, leaf_threshold=leaf_threshold)

        return results
```

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_coordinator.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/coordinator.py tests/test_pipeline_coordinator.py
git commit -m "feat(pipeline): add coordinator with DAG resolution and recursive decomposition"
```

---

### Task 1.3: Add learning persistence types

**Files:**
- Create: `src/architecture_model/pipeline/learning.py`
- Test: `tests/test_pipeline_learning.py`

**Step 1: Write the failing test**

```python
# tests/test_pipeline_learning.py
"""Tests for project-local learning persistence."""
import pytest
from pathlib import Path
from architecture_model.pipeline.learning import (
    Correction, ResolutionOutcome, Calibration, QualityTrend,
    LearningStore,
)
from architecture_model.pipeline.protocol import Evidence, Uncertainty


class TestLearningStore:
    def test_save_and_load_correction(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        correction = Correction(
            timestamp="2026-08-09T10:00:00",
            module="allocate",
            entity_id="COMP-UTILS",
            correction_type="split",
            before={"files": ["a.py", "b.py", "c.py"]},
            after={"COMP-LOG": ["a.py"], "COMP-HELP": ["b.py", "c.py"]},
            reason="Logging and helpers are different concerns",
        )
        store.add_correction(correction)
        loaded = store.get_corrections()
        assert len(loaded) == 1
        assert loaded[0].entity_id == "COMP-UTILS"

    def test_corrections_as_evidence(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        store.add_correction(Correction(
            timestamp="2026-08-09", module="allocate", entity_id="COMP-X",
            correction_type="rename", before={"name": "Old"}, after={"name": "New"},
            reason="Better name",
        ))
        evidence = store.corrections_as_evidence()
        assert len(evidence) == 1
        assert evidence[0].source == "user_correction"
        assert evidence[0].confidence == 1.0

    def test_save_and_load_calibration(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        store.set_calibration("allocate", "boundary_coherence_threshold", 50.0,
                             reason="Cross-cutting design intentional")
        cal = store.get_calibration("allocate")
        assert cal["boundary_coherence_threshold"] == 50.0

    def test_record_quality_history(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        store.record_run("2026-08-09", {"observe": 95.0, "allocate": 72.0})
        store.record_run("2026-08-10", {"observe": 95.0, "allocate": 58.0})
        trend = store.get_trend("allocate")
        assert trend.direction == "degrading"

    def test_save_resolution_outcome(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        outcome = ResolutionOutcome(
            uncertainty=Uncertainty(
                category="orphan_file", description="x.py orphaned",
                suggested_fallback="ask_user", priority="blocking",
            ),
            resolution=Evidence(source="user_confirmation", confidence=1.0, raw="It's a script"),
            method="ask_user",
            attempts=1,
            duration_ms=5000,
        )
        store.add_resolution(outcome)
        resolutions = store.get_resolutions(category="orphan_file")
        assert len(resolutions) == 1
        assert resolutions[0].method == "ask_user"
```

**Step 2: Run test to verify fails**

Run: `pytest tests/test_pipeline_learning.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/architecture_model/pipeline/learning.py
"""Project-local learning persistence.

Stores corrections, resolution outcomes, calibration overrides,
and quality history for cross-session learning (Loop 2).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import json

from .protocol import Evidence, Uncertainty


@dataclass
class Correction:
    """A user correction to a module's output."""
    timestamp: str
    module: str
    entity_id: str
    correction_type: str  # rename | split | merge | remove | add | reclassify | reassign
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str


@dataclass
class ResolutionOutcome:
    """Record of how an uncertainty was resolved."""
    uncertainty: Uncertainty
    resolution: Evidence
    method: str       # llm | search | user | escalation
    attempts: int
    duration_ms: int


@dataclass
class Calibration:
    """A project-specific threshold override."""
    module: str
    parameter: str
    value: float
    reason: str
    date: str = ""


@dataclass
class QualityTrend:
    """Quality trend for a metric over time."""
    module: str
    metric: str = "score"
    values: list[tuple[str, float]] = field(default_factory=list)

    @property
    def direction(self) -> str:
        if len(self.values) < 2:
            return "stable"
        recent = [v for _, v in self.values[-3:]]
        if all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)):
            return "degrading"
        if all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1)):
            return "improving"
        return "stable"


class LearningStore:
    """Persists learning data to .architecture/learning/."""

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    # --- Corrections ---

    def add_correction(self, correction: Correction) -> None:
        corrections = self._load_json("corrections.json", [])
        corrections.append(asdict(correction))
        self._save_json("corrections.json", corrections)

    def get_corrections(self, module: str | None = None) -> list[Correction]:
        data = self._load_json("corrections.json", [])
        corrections = [Correction(**d) for d in data]
        if module:
            corrections = [c for c in corrections if c.module == module]
        return corrections

    def corrections_as_evidence(self) -> list[Evidence]:
        return [
            Evidence(
                source="user_correction",
                confidence=1.0,
                raw=f"{c.correction_type} {c.entity_id}: {c.reason}",
            )
            for c in self.get_corrections()
        ]

    # --- Calibration ---

    def set_calibration(self, module: str, parameter: str, value: float, reason: str = "") -> None:
        cal = self._load_json("calibration.json", {})
        if module not in cal:
            cal[module] = {}
        cal[module][parameter] = {"value": value, "reason": reason}
        self._save_json("calibration.json", cal)

    def get_calibration(self, module: str) -> dict[str, float]:
        cal = self._load_json("calibration.json", {})
        module_cal = cal.get(module, {})
        return {k: v["value"] for k, v in module_cal.items()}

    # --- Quality History ---

    def record_run(self, date: str, scores: dict[str, float]) -> None:
        history = self._load_json("history.json", [])
        history.append({"date": date, "scores": scores})
        self._save_json("history.json", history)

    def get_trend(self, module: str) -> QualityTrend:
        history = self._load_json("history.json", [])
        values = [
            (h["date"], h["scores"].get(module, 0.0))
            for h in history
            if module in h.get("scores", {})
        ]
        trend = QualityTrend(module=module, values=values)
        return trend

    # --- Resolutions ---

    def add_resolution(self, outcome: ResolutionOutcome) -> None:
        resolutions = self._load_json("resolutions.json", [])
        resolutions.append({
            "category": outcome.uncertainty.category,
            "description": outcome.uncertainty.description,
            "method": outcome.method,
            "attempts": outcome.attempts,
            "duration_ms": outcome.duration_ms,
            "resolution_source": outcome.resolution.source,
            "resolution_raw": outcome.resolution.raw,
        })
        self._save_json("resolutions.json", resolutions)

    def get_resolutions(self, category: str | None = None) -> list[ResolutionOutcome]:
        data = self._load_json("resolutions.json", [])
        results = []
        for d in data:
            outcome = ResolutionOutcome(
                uncertainty=Uncertainty(
                    category=d["category"],
                    description=d["description"],
                    suggested_fallback="",
                    priority="",
                ),
                resolution=Evidence(
                    source=d["resolution_source"],
                    confidence=1.0,
                    raw=d["resolution_raw"],
                ),
                method=d["method"],
                attempts=d["attempts"],
                duration_ms=d["duration_ms"],
            )
            if category is None or d["category"] == category:
                results.append(outcome)
        return results

    # --- Helpers ---

    def _load_json(self, filename: str, default: Any) -> Any:
        path = self.path / filename
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def _save_json(self, filename: str, data: Any) -> None:
        path = self.path / filename
        path.write_text(json.dumps(data, indent=2, default=str))
```

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_learning.py -v`
Expected: All PASS

**Step 5: Update `__init__.py` and commit**

```bash
git add src/architecture_model/pipeline/learning.py tests/test_pipeline_learning.py
git commit -m "feat(pipeline): add learning store — corrections, calibration, trends, resolutions"
```

---

## Phase 2: File Migrations from opencode-arch

### Task 2.1: Move route_detector.py

**Files:**
- Copy: `../opencode-arch/src/opencode_arch/extract/route_detector.py` → `src/architecture_model/extract/route_detector.py`
- Modify: Fix imports (change `opencode_arch.` → `architecture_model.`)
- Test: `tests/test_route_detector.py` (copy existing tests from opencode-arch if they exist, or write new)

**Step 1: Copy file and fix imports**

Copy `route_detector.py` from opencode-arch. Replace any `from opencode_arch.` imports with `from architecture_model.` equivalents.

**Step 2: Verify existing tests pass or write smoke test**

```python
# tests/test_route_detector.py
from architecture_model.extract.route_detector import detect_routes
from pathlib import Path

def test_detect_routes_empty_dir(tmp_path):
    routes = detect_routes(tmp_path)
    assert routes == []

def test_detect_fastapi_route(tmp_path):
    (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    """List all users."""
    pass
''')
    routes = detect_routes(tmp_path)
    assert len(routes) >= 1
    assert routes[0].method == "GET"
    assert routes[0].path == "/users"
```

**Step 3: Run tests**

Run: `pytest tests/test_route_detector.py -v`

**Step 4: Commit**

```bash
git add src/architecture_model/extract/route_detector.py tests/test_route_detector.py
git commit -m "feat(extract): move route_detector from opencode-arch — pure AST route detection"
```

---

### Task 2.2: Move constraint_detector.py

Same pattern as 2.1. Copy, fix imports, write smoke test, commit.

```bash
git commit -m "feat(extract): move constraint_detector from opencode-arch"
```

---

### Task 2.3: Move from_artifacts.py + table_parser.py

Same pattern. These two are related (from_artifacts uses table_parser).

```bash
git commit -m "feat(extract): move from_artifacts + table_parser from opencode-arch"
```

---

### Task 2.4: Update opencode-arch to import from architecture-model-standard

**Files (in ../opencode-arch):**
- Modify: `src/opencode_arch/extract/__init__.py`
- Modify: Any file importing `route_detector`, `constraint_detector`, `from_artifacts`, `table_parser`

Replace local imports with:
```python
from architecture_model.extract.route_detector import detect_routes
from architecture_model.extract.constraint_detector import detect_constraints
from architecture_model.extract.from_artifacts import extract_from_artifacts
from architecture_model.extract.table_parser import parse_table
```

Delete the moved files from opencode-arch.

```bash
# In opencode-arch repo
git commit -m "refactor: import extract modules from architecture-model-standard"
```

---

## Phase 3: Module Implementations

Each module follows the same pattern:
1. Define output types
2. Write tests against the protocol
3. Implement by refactoring existing code into the new module
4. Verify quality metrics work
5. Commit

### Task 3.1: Implement `observe` module

**Files:**
- Create: `src/architecture_model/pipeline/observe.py`
- Create: `src/architecture_model/pipeline/observe_types.py`
- Test: `tests/test_pipeline_observe.py`

**This is the largest task** — it wraps existing `manifest/generator.py`, `manifest/scanner.py`, `manifest/body_hints.py`, `manifest/multi_scanner.py`, and the newly-moved `extract/route_detector.py` + `extract/constraint_detector.py`.

**Step 1: Define output types**

```python
# src/architecture_model/pipeline/observe_types.py
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionRecord:
    name: str
    signature: str
    body_hint: str
    calls: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    line_number: int = 0


@dataclass
class ClassRecord:
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    method_details: list[FunctionRecord] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    decorators: list[str] = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class ConstantRecord:
    name: str
    value: str
    type: str = ""
    context: str = ""  # class name if class-level


@dataclass
class ImportEdge:
    source: Path
    target: Path
    symbols: list[str] = field(default_factory=list)


@dataclass
class RouteRecord:
    method: str
    path: str
    function_name: str
    file: Path
    docstring: str = ""
    is_authenticated: bool = False
    framework: str = ""


@dataclass
class ConstraintRecord:
    name: str
    value: str
    source: str  # file path where discovered
    constraint_type: str = ""  # "technology" | "version" | "timeout" | ...


@dataclass
class TestFileRecord:
    path: Path
    targets: list[str] = field(default_factory=list)  # module names this tests


@dataclass
class DocRecord:
    path: Path
    title: str = ""
    summary: str = ""  # first paragraph


@dataclass
class ModuleRecord:
    path: Path
    language: str = "python"
    functions: list[FunctionRecord] = field(default_factory=list)
    classes: list[ClassRecord] = field(default_factory=list)
    constants: list[ConstantRecord] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    line_count: int = 0
    docstring: str | None = None


@dataclass
class Inventory:
    """Complete factual record of a codebase. Zero inference."""
    modules: list[ModuleRecord] = field(default_factory=list)
    edges: list[ImportEdge] = field(default_factory=list)
    routes: list[RouteRecord] = field(default_factory=list)
    constraints: list[ConstraintRecord] = field(default_factory=list)
    test_files: list[TestFileRecord] = field(default_factory=list)
    docs: list[DocRecord] = field(default_factory=list)
```

**Step 2: Write test for observe stage**

```python
# tests/test_pipeline_observe.py
import pytest
from pathlib import Path
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext


class TestObserveStage:
    def test_observe_empty_dir(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        assert result.output.modules == []
        assert result.quality.score >= 0

    def test_observe_simple_python_file(self, tmp_path):
        src = tmp_path / "src" / "app"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")
        (src / "main.py").write_text('''
"""Main application module."""
import os

API_VERSION = "1.0"

def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}"

class Config:
    DEBUG = True
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)

        assert len(result.output.modules) >= 1
        main_mod = next(m for m in result.output.modules if "main" in str(m.path))
        assert len(main_mod.functions) == 1
        assert main_mod.functions[0].name == "hello"
        assert main_mod.functions[0].body_hint != ""
        assert len(main_mod.classes) == 1
        assert len(main_mod.constants) >= 1

    def test_observe_discovers_routes(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        assert len(result.output.routes) >= 1

    def test_observe_quality_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        assert "parse_success_rate" in result.quality.sub_scores
        assert "symbol_density" in result.quality.sub_scores

    def test_observe_emits_uncertainties_for_dynamic_imports(self, tmp_path):
        (tmp_path / "loader.py").write_text('''
import importlib
mod = importlib.import_module(name)
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        # Should flag dynamic import as uncertainty
        categories = [u.category for u in result.uncertainties]
        assert "dynamic_import" in categories

    def test_observe_name_and_requires(self):
        stage = ObserveStage()
        assert stage.name == "observe"
        assert stage.requires == []
```

**Step 3: Implement observe stage**

The implementation wraps existing `generate_manifest()` + `detect_routes()` + `detect_constraints()` + body hints into the new protocol. Key: adapt existing `Manifest`/`ModuleInfo` types into the new `Inventory`/`ModuleRecord` types.

(Implementation will be ~200 lines of adapter code calling into existing infrastructure)

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_observe.py -v`

**Step 5: Commit**

```bash
git commit -m "feat(pipeline): implement observe module — wraps manifest+routes+constraints into Inventory"
```

---

### Task 3.2: Implement `infer` module

**Files:**
- Create: `src/architecture_model/pipeline/infer.py`
- Create: `src/architecture_model/pipeline/infer_types.py`
- Test: `tests/test_pipeline_infer.py`

Refactors: `orchestration/capability_inference.py`, `orchestration/use_case_inference.py`, `orchestration/trigger_detection.py`

Key change: **capability-driven** — clusters by purpose (routes, tests, domain), not by imports.

**Tests should verify:**
- Routes grouped by URL prefix → capabilities
- Actors inferred from auth patterns
- Use cases from trigger chains
- Hierarchy depth ≤3
- Quality metrics (capability_coverage, actor_completeness)
- Uncertainties emitted for ambiguous modules

---

### Task 3.3: Implement `allocate` module

**Files:**
- Create: `src/architecture_model/pipeline/allocate.py`
- Create: `src/architecture_model/pipeline/allocate_types.py`
- Test: `tests/test_pipeline_allocate.py`

Refactors: `manifest/grouping.py`, `core/decomposer.py`, `orchestration/full_extraction.py` (component creation)

Key change: **capability-driven** — seed from capabilities, import affinity as tiebreaker.

**Tests should verify:**
- Files seeded to components by capability evidence
- Remaining files assigned by import affinity
- Oversized components split
- Undersized components merged
- File coverage ≥95%
- Boundary coherence computed

---

### Task 3.4: Implement `relate` module

**Files:**
- Create: `src/architecture_model/pipeline/relate.py`
- Create: `src/architecture_model/pipeline/relate_types.py`
- Test: `tests/test_pipeline_relate.py`

Refactors: `orchestration/trigger_detection.py`, `orchestration/behavior_decompose.py`, relationship derivation from `extract/from_code.py`

**Tests should verify:**
- depends-on from cross-component imports
- triggers from call-graph BFS
- realizes from allocation
- contains from hierarchy
- Uncertainties for implicit coupling (event patterns)

---

### Task 3.5: Implement `specify` module

**Files:**
- Create: `src/architecture_model/pipeline/specify.py`
- Create: `src/architecture_model/pipeline/specify_types.py`
- Test: `tests/test_pipeline_specify.py`

Refactors: `orchestration/enrich.py`, `orchestration/auto_enrich.py`

**Tests should verify:**
- Signatures extracted per component
- Body hints from inventory (already observed)
- Constants per component
- Design patterns detected
- Provides/requires interfaces

---

### Task 3.6: Implement `contract` module

**Files:**
- Create: `src/architecture_model/pipeline/contract.py`
- Create: `src/architecture_model/pipeline/contract_types.py`
- Test: `tests/test_pipeline_contract.py`

Refactors: `manifest/test_analyzer.py`, test contract extraction from `orchestration/enrich.py`

**Tests should verify:**
- Test files discovered by naming convention
- Assertions parsed into typed contracts
- Constants derived from test values
- Quality metrics (contract count, function coverage)

---

### Task 3.7: Implement `validate` module

**Files:**
- Create: `src/architecture_model/pipeline/validate.py`
- Test: `tests/test_pipeline_validate.py`

Wraps: `core/validator.py` + `core/representativeness.py`

**Tests should verify:**
- Structural validation (existing 11 checks)
- File coverage against inventory
- Relationship accuracy against edges
- Boundary coherence
- Composite overall score

---

## Phase 4: Recursive Decomposition + Artifact Generation

### Task 4.1: Implement artifact writer

**Files:**
- Create: `src/architecture_model/pipeline/artifacts.py`
- Test: `tests/test_pipeline_artifacts.py`

Produces the uniform file structure at each recursion level:
```
.architecture/
├── inventory.json
├── functional.yaml
├── structure.yaml
├── relationships.yaml
├── validation.json
├── context.md
├── specs/{comp}.yaml
├── contracts/{comp}.yaml
└── subsystems/{comp}/.architecture/
```

---

### Task 4.2: Implement context.md generator

**Files:**
- Create: `src/architecture_model/pipeline/context_gen.py`
- Test: `tests/test_pipeline_context_gen.py`

Generates the LLM-readable summary from functional + structural + relationship models.

---

### Task 4.3: Wire recursive decomposition in coordinator

Enhance `coordinator.run_recursive()` to:
1. Run all stages at current level
2. Write artifacts
3. For each component > leaf_threshold, create sub-context and recurse
4. Generate context.md at each level

---

## Phase 5: Learning Integration

### Task 5.1: Wire learning store into coordinator

**Modify:** `src/architecture_model/pipeline/coordinator.py`

Before running stages:
1. Load corrections → inject as prior evidence into context
2. Load calibration → override thresholds in stage configs
3. After running, record quality scores to history

---

### Task 5.2: Add CLI commands

**Modify:** `src/architecture_model/cli/main.py`

Add commands:
- `architecture-model observe <path>` — run observe, print quality
- `architecture-model infer <path>` — run observe+infer
- `architecture-model allocate <path>` — run observe+infer+allocate
- `architecture-model pipeline <path>` — run all stages recursively
- `architecture-model status <path>` — show quality trends from learning store

---

## Phase 6: opencode-arch Cleanup

### Task 6.1: Replace MCP tools with thin wrappers

Each MCP tool becomes ~20 lines: parse params → create PipelineContext → call coordinator.run_stage() → format response.

### Task 6.2: Delete moved files

Remove from opencode-arch:
- `extract/route_detector.py`
- `extract/constraint_detector.py`
- `extract/from_artifacts.py`
- `extract/table_parser.py`
- `extract/from_code.py` (duplicate)

### Task 6.3: Add uncertainty resolution to MCP layer

Implement `agent/resolution.py` — the `UncertaintyResolver` that dispatches to LLM/search/user.

---

## Execution Order & Dependencies

```
Phase 1 (no deps, pure new code):
  1.1 → 1.2 → 1.3

Phase 2 (requires Phase 1 for protocol types):
  2.1 → 2.2 → 2.3 → 2.4

Phase 3 (requires Phase 1 + 2):
  3.1 (observe) → 3.2 (infer) → 3.3 (allocate) → 3.4 (relate)
                                  3.3 → 3.5 (specify)
                                  3.3 → 3.6 (contract)
  3.4 + 3.5 + 3.6 → 3.7 (validate)

Phase 4 (requires Phase 3):
  4.1 → 4.2 → 4.3

Phase 5 (requires Phase 3 + 4):
  5.1 → 5.2

Phase 6 (requires all above):
  6.1 → 6.2 → 6.3
```

**Estimated effort:** ~20 tasks, each 15-60 minutes. Total: ~2-3 days of focused work.

**Test command throughout:** `pytest tests/ -v --ignore=tests/test_config_loader.py`
