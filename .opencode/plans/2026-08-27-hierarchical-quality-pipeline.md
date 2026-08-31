# Hierarchical Quality + Per-Stage LLM Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make quality a cross-cutting concern at every pipeline level (system → component → module) with configurable hard/soft quality gates, per-stage LLM review, and end-to-end validation on python-dotenv.

**Architecture:** Extend `QualityMetrics` with hierarchical `component_scores`, add `QualityGate` with hard/soft thresholds to the coordinator, inject LLM review after every stage via coordinator hook, and validate the full chain by extracting python-dotenv stage-by-stage.

**Tech Stack:** Python dataclasses, existing pipeline protocol, quality subsystem modules

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
**Pre-existing failures (7):** test_includes_confidence, test_includes_components, test_real_logs_db, test_name_version_requires, test_schema_json_has_all_relationship_types, + 2 manifest tests.
**Current baseline:** 7 failed, 1394 passed, 98 skipped.

---

## Phase 1: Protocol Extensions (Tasks 1-3)

### Task 1: Add `component_scores` to QualityMetrics

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py:89-101`
- Test: `tests/test_pipeline_protocol.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_pipeline_protocol.py

class TestHierarchicalQuality:
    def test_component_scores_default_empty(self):
        qm = QualityMetrics(score=90)
        assert qm.component_scores == {}

    def test_component_scores_nested(self):
        child = QualityMetrics(score=85, sub_scores={"complexity": 3.0})
        qm = QualityMetrics(score=90, component_scores={"COMP-1": child})
        assert qm.component_scores["COMP-1"].score == 85
        assert qm.component_scores["COMP-1"].sub_scores["complexity"] == 3.0

    def test_passes_ignores_component_scores(self):
        """Top-level passes only checks top-level thresholds."""
        child = QualityMetrics(score=10, sub_scores={"x": 5}, thresholds={"x": 50})
        qm = QualityMetrics(score=90, thresholds={"y": 80}, sub_scores={"y": 90},
                            component_scores={"COMP-1": child})
        assert qm.passes  # parent passes even though child fails

    def test_worst_component_score(self):
        qm = QualityMetrics(
            score=90,
            component_scores={
                "COMP-1": QualityMetrics(score=85),
                "COMP-2": QualityMetrics(score=60),
            },
        )
        assert qm.worst_component == ("COMP-2", 60)

    def test_worst_component_empty(self):
        qm = QualityMetrics(score=90)
        assert qm.worst_component is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_protocol.py::TestHierarchicalQuality -v`
Expected: FAIL — `component_scores` not a field, `worst_component` not defined

**Step 3: Implement**

In `protocol.py`, update `QualityMetrics`:

```python
@dataclass
class QualityMetrics:
    """Per-stage quality scores with optional per-component breakdown."""

    score: float
    sub_scores: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    component_scores: dict[str, "QualityMetrics"] = field(default_factory=dict)
    llm_prompt: str = ""

    @property
    def passes(self) -> bool:
        return all(self.sub_scores.get(k, 0.0) >= v for k, v in self.thresholds.items())

    @property
    def worst_component(self) -> tuple[str, float] | None:
        if not self.component_scores:
            return None
        worst = min(self.component_scores.items(), key=lambda kv: kv[1].score)
        return (worst[0], worst[1].score)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline_protocol.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git commit -m "feat(protocol): add hierarchical component_scores to QualityMetrics"
```

---

### Task 2: Add `QualityGate` with hard/soft thresholds

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py`
- Test: `tests/test_pipeline_protocol.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_pipeline_protocol.py
from architecture_model.pipeline.protocol import QualityGate, GateSeverity

class TestQualityGate:
    def test_soft_gate_warns_on_failure(self):
        gate = QualityGate(
            metric="parse_success_rate",
            threshold=90.0,
            severity=GateSeverity.SOFT,
        )
        qm = QualityMetrics(score=50, sub_scores={"parse_success_rate": 70.0})
        result = gate.evaluate(qm)
        assert result.passed is False
        assert result.blocks is False  # soft = warn only
        assert "parse_success_rate" in result.message

    def test_hard_gate_blocks_on_failure(self):
        gate = QualityGate(
            metric="parse_success_rate",
            threshold=90.0,
            severity=GateSeverity.HARD,
        )
        qm = QualityMetrics(score=50, sub_scores={"parse_success_rate": 70.0})
        result = gate.evaluate(qm)
        assert result.passed is False
        assert result.blocks is True

    def test_gate_passes(self):
        gate = QualityGate(
            metric="parse_success_rate",
            threshold=90.0,
            severity=GateSeverity.HARD,
        )
        qm = QualityMetrics(score=95, sub_scores={"parse_success_rate": 95.0})
        result = gate.evaluate(qm)
        assert result.passed is True
        assert result.blocks is False

    def test_gate_missing_metric_fails_soft(self):
        gate = QualityGate(metric="unknown", threshold=50.0, severity=GateSeverity.HARD)
        qm = QualityMetrics(score=90)
        result = gate.evaluate(qm)
        assert result.passed is False
        assert result.blocks is True  # metric missing = threshold unmet

    def test_lte_direction_for_error_count(self):
        gate = QualityGate(metric="error_count", threshold=0.0, severity=GateSeverity.HARD, direction="lte")
        qm_good = QualityMetrics(score=90, sub_scores={"error_count": 0.0})
        qm_bad = QualityMetrics(score=50, sub_scores={"error_count": 3.0})
        assert gate.evaluate(qm_good).passed is True
        assert gate.evaluate(qm_bad).blocks is True
```

**Step 2: Implement**

```python
from enum import Enum

class GateSeverity(Enum):
    SOFT = "soft"    # warn and continue
    HARD = "hard"    # block pipeline progression

@dataclass
class GateResult:
    passed: bool
    blocks: bool
    message: str
    metric: str
    actual: float
    threshold: float

@dataclass
class QualityGate:
    metric: str
    threshold: float
    severity: GateSeverity = GateSeverity.SOFT
    direction: str = "gte"  # "gte" = actual >= threshold is good; "lte" = actual <= threshold is good

    def evaluate(self, quality: QualityMetrics) -> GateResult:
        actual = quality.sub_scores.get(self.metric, 0.0)
        if self.direction == "lte":
            passed = actual <= self.threshold
        else:
            passed = actual >= self.threshold
        blocks = (not passed) and (self.severity == GateSeverity.HARD)
        verb = "PASS" if passed else ("BLOCKED" if blocks else "WARN")
        message = f"{verb}: {self.metric} = {actual:.1f} (threshold: {self.threshold:.1f})"
        return GateResult(
            passed=passed, blocks=blocks, message=message,
            metric=self.metric, actual=actual, threshold=self.threshold,
        )

class QualityGateError(Exception):
    """Raised when a hard quality gate blocks pipeline progression."""
    def __init__(self, message: str, gate_results: list[GateResult] | None = None):
        super().__init__(message)
        self.gate_results = gate_results or []
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(protocol): add QualityGate with hard/soft severity and direction"
```

---

### Task 3: Add `StageQualityReview` + `review_log` to PipelineContext

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py:118-134`
- Test: `tests/test_pipeline_protocol.py`

**Step 1: Write the failing test**

```python
class TestStageQualityReview:
    def test_review_dataclass(self):
        from architecture_model.pipeline.protocol import StageQualityReview
        review = StageQualityReview(
            stage="observe",
            quality=QualityMetrics(score=90),
            gate_results=[],
            llm_review="Looks good",
            suggestions=["Add docstrings"],
        )
        assert review.stage == "observe"
        assert review.llm_review == "Looks good"

    def test_pipeline_context_has_review_log(self):
        from pathlib import Path
        ctx = PipelineContext(repo_path=Path("."), output_dir=Path("."))
        assert ctx.review_log == []
```

**Step 2: Implement**

```python
@dataclass
class StageQualityReview:
    """Record of quality review after a stage completes."""
    stage: str
    quality: QualityMetrics
    gate_results: list[GateResult]
    llm_review: str = ""
    suggestions: list[str] = field(default_factory=list)
    component_reviews: dict[str, str] = field(default_factory=dict)
```

Add to `PipelineContext`:
```python
    review_log: list[StageQualityReview] = field(default_factory=list)
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(protocol): add StageQualityReview and review_log to PipelineContext"
```

---

## Phase 2: Per-Stage Quality Enrichment (Tasks 4-8)

### Task 4: Observe stage — per-module quality scores

**Files:**
- Modify: `src/architecture_model/pipeline/observe.py:103-145`
- Modify: `src/architecture_model/pipeline/observe_types.py` (add `quality_score` to ModuleRecord)
- Test: `tests/test_pipeline_observe.py`

**Step 1: Write the failing test**

```python
class TestObservePerModuleQuality:
    def test_module_record_has_quality_score(self):
        from architecture_model.pipeline.observe_types import ModuleRecord
        from pathlib import Path
        mr = ModuleRecord(path=Path("test.py"), quality_score=75)
        assert mr.quality_score == 75

    def test_observe_quality_has_component_scores(self, tmp_path):
        """After observe, quality.component_scores keyed by module path."""
        # Create a small Python file
        (tmp_path / "mod.py").write_text("def foo():\n    return 1\n")
        stage = ObserveStage()
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".out")
        result = stage.run(ctx)
        assert isinstance(result.quality.component_scores, dict)
```

**Step 2: Implement**

In `observe_types.py`, add to `ModuleRecord`:
```python
    quality_score: int = 0  # 0-100 from code_review.analyze_source
```

In `observe.py`, replace the current aggregate code_quality_avg with per-module tracking:
```python
        # Code quality scoring — per-module
        module_scores: dict[str, QualityMetrics] = {}
        try:
            from architecture_model.quality.code_review import analyze_source
            for mod in modules:
                try:
                    mod_path = Path(mod.path) if not isinstance(mod.path, Path) else mod.path
                    if mod_path.exists():
                        analysis = analyze_source(mod_path.read_text(), filename=str(mod_path))
                        mod.quality_score = analysis.score
                        fn_count = max(len(analysis.functions), 1)
                        module_scores[str(mod_path)] = QualityMetrics(
                            score=analysis.score,
                            sub_scores={
                                "complexity_avg": sum(f.complexity for f in analysis.functions) / fn_count,
                                "docstring_coverage": sum(1 for f in analysis.functions if f.has_docstring) / fn_count * 100,
                                "type_hint_coverage": sum(1 for f in analysis.functions if f.has_type_hints) / fn_count * 100,
                                "issue_count": float(len(analysis.issues)),
                            },
                        )
                except Exception:
                    pass
        except ImportError:
            pass

        code_quality_avg = sum(qm.score for qm in module_scores.values()) / max(len(module_scores), 1)
```

Then set `component_scores=module_scores` on the QualityMetrics constructor.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(observe): per-module quality scores with complexity, docstrings, type hints"
```

---

### Task 5: Allocate stage — per-component quality from module aggregation

**Files:**
- Modify: `src/architecture_model/pipeline/allocate.py`
- Test: `tests/test_pipeline_allocate.py`

**Step 1: Write the failing test**

```python
class TestAllocatePerComponentQuality:
    def test_allocate_propagates_module_quality(self):
        """After allocate, component_scores keyed by component ID, each containing module scores."""
        from architecture_model.pipeline.protocol import QualityMetrics, StageResult, PipelineContext
        from architecture_model.pipeline.observe_types import Inventory
        from pathlib import Path

        # Simulate observe result with per-module quality
        observe_quality = QualityMetrics(
            score=85,
            component_scores={
                "src/a.py": QualityMetrics(score=80, sub_scores={"complexity_avg": 3.0}),
                "src/b.py": QualityMetrics(score=60, sub_scores={"complexity_avg": 8.0}),
            },
        )
        # ... build context with cached observe result, run allocate
        # Assert component_scores has entries keyed by component ID
```

**Step 2: Implement**

After allocation, aggregate per-module quality from observe into per-component:
```python
        observe_result = ctx.cache.get("observe")
        module_quality = observe_result.quality.component_scores if observe_result else {}
        comp_quality: dict[str, QualityMetrics] = {}
        for comp in components:
            comp_mod_scores = []
            comp_mod_details: dict[str, QualityMetrics] = {}
            for f in comp.files:
                key = str(f)
                if key in module_quality:
                    comp_mod_scores.append(module_quality[key].score)
                    comp_mod_details[key] = module_quality[key]
            if comp_mod_scores:
                comp_quality[comp.id] = QualityMetrics(
                    score=sum(comp_mod_scores) / len(comp_mod_scores),
                    sub_scores={
                        "module_count": float(len(comp.files)),
                        "worst_module": min(comp_mod_scores),
                        "best_module": max(comp_mod_scores),
                    },
                    component_scores=comp_mod_details,
                )
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(allocate): aggregate per-module quality into per-component scores"
```

---

### Task 6: Relate/Specify/Contract — per-component quality propagation

**Files:**
- Modify: `src/architecture_model/pipeline/relate.py`
- Modify: `src/architecture_model/pipeline/specify.py`
- Modify: `src/architecture_model/pipeline/contract.py`
- Test: `tests/test_pipeline_stages.py`

**Step 1: Write tests** — verify component_scores are propagated from allocate and enriched with stage-specific per-component metrics.

**Step 2: Implement** — each stage reads allocate's `component_scores`, copies them, and adds its own per-component sub_scores:
- **relate**: `relationship_count` per component
- **specify**: `interface_count` per component  
- **contract**: `test_coverage` per component (1.0 if has tests, 0.0 if not)

**Step 3: Run tests, commit**

```bash
git commit -m "feat(relate,specify,contract): propagate and enrich per-component quality"
```

---

### Task 7: Validate stage — per-component validation issues

**Files:**
- Modify: validation quality metrics construction (inside the validate stage or coordinator)
- Test: `tests/test_pipeline_stages.py`

**Step 1: Write test** — after validate, component_scores should show issue counts per component.

**Step 2: Implement** — group validation issues by entity_id → component mapping (from allocate), produce per-component issue counts and scores.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(validate): per-component validation issue tracking"
```

---

### Task 8: Decompose/Synthesize — per-subsystem quality rollup

**Files:**
- Modify: `src/architecture_model/pipeline/decompose.py`
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_decompose.py`, `tests/test_pipeline_synthesize.py`

**Step 1: Write tests** — after decompose, component_scores keyed by system ID.

**Step 2: Implement** — aggregate component quality into system-level quality. After synthesize, collect sub-pipeline quality.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(decompose,synthesize): per-subsystem quality rollup"
```

---

## Phase 3: Coordinator Quality Gates + LLM Review (Tasks 9-12)

### Task 9: Default quality gates per stage

**Files:**
- Create: `src/architecture_model/pipeline/gates.py`
- Test: `tests/test_pipeline_gates.py`

**Step 1: Write the failing test**

```python
from architecture_model.pipeline.gates import DEFAULT_GATES, get_gates_for_stage
from architecture_model.pipeline.protocol import GateSeverity

class TestDefaultGates:
    def test_observe_has_hard_parse_gate(self):
        gates = get_gates_for_stage("observe")
        parse_gate = next(g for g in gates if g.metric == "parse_success_rate")
        assert parse_gate.severity == GateSeverity.HARD
        assert parse_gate.threshold == 90.0

    def test_allocate_has_soft_coherence_gate(self):
        gates = get_gates_for_stage("allocate")
        coherence_gate = next(g for g in gates if g.metric == "boundary_coherence")
        assert coherence_gate.severity == GateSeverity.SOFT

    def test_validate_error_gate_is_lte(self):
        gates = get_gates_for_stage("validate")
        error_gate = next(g for g in gates if g.metric == "error_count")
        assert error_gate.direction == "lte"
        assert error_gate.severity == GateSeverity.HARD

    def test_unknown_stage_returns_empty(self):
        assert get_gates_for_stage("nonexistent") == []
```

**Step 2: Implement**

```python
"""Default quality gates per pipeline stage."""
from architecture_model.pipeline.protocol import QualityGate, GateSeverity

DEFAULT_GATES: dict[str, list[QualityGate]] = {
    "observe": [
        QualityGate("parse_success_rate", 90.0, GateSeverity.HARD),
        QualityGate("code_quality_avg", 30.0, GateSeverity.SOFT),
    ],
    "infer": [
        QualityGate("capability_coverage", 60.0, GateSeverity.SOFT),
    ],
    "allocate": [
        QualityGate("file_coverage", 95.0, GateSeverity.HARD),
        QualityGate("boundary_coherence", 50.0, GateSeverity.SOFT),
    ],
    "contract": [
        QualityGate("test_coverage_ratio", 50.0, GateSeverity.SOFT),
    ],
    "validate": [
        QualityGate("error_count", 0.0, GateSeverity.HARD, direction="lte"),
    ],
}

def get_gates_for_stage(stage_name: str) -> list[QualityGate]:
    return DEFAULT_GATES.get(stage_name, [])
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(pipeline): default quality gates per stage with hard/soft severity"
```

---

### Task 10: Coordinator enforces quality gates

**Files:**
- Modify: `src/architecture_model/pipeline/coordinator.py:77-132`
- Test: `tests/test_pipeline_coordinator.py`

**Step 1: Write the failing test**

```python
class TestCoordinatorQualityGates:
    def test_hard_gate_failure_raises(self):
        """A hard gate failure should raise QualityGateError."""
        from architecture_model.pipeline.protocol import QualityGateError
        # Create a mock stage returning quality below hard threshold
        # Expect QualityGateError on run_all()

    def test_soft_gate_failure_continues(self):
        """A soft gate failure should log a review but continue."""
        # Stage with quality below soft threshold
        # Pipeline should complete without error
        # ctx.review_log should contain the soft warning

    def test_gate_results_in_review_log(self):
        """After each stage, gate results appear in ctx.review_log."""
        # Run pipeline, check review_log entries match stage count
```

**Step 2: Implement** — in coordinator's `run_to()` and `run_all()`, after `stage.run(ctx)`:

```python
    from architecture_model.pipeline.gates import get_gates_for_stage

    result = stage.run(ctx)
    ctx.cache[name] = result

    # Quality gates
    gates = get_gates_for_stage(name)
    gate_results = [g.evaluate(result.quality) for g in gates]
    review = StageQualityReview(stage=name, quality=result.quality, gate_results=gate_results)
    ctx.review_log.append(review)

    blockers = [gr for gr in gate_results if gr.blocks]
    if blockers:
        raise QualityGateError(
            f"Stage '{name}' blocked: " + "; ".join(gr.message for gr in blockers),
            gate_results=blockers,
        )
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(coordinator): enforce quality gates between stages"
```

---

### Task 11: Per-stage LLM review in coordinator

**Files:**
- Create: `src/architecture_model/pipeline/stage_review.py`
- Modify: `src/architecture_model/pipeline/coordinator.py`
- Test: `tests/test_stage_review.py`

**Step 1: Write the failing test**

```python
from architecture_model.pipeline.stage_review import build_review_prompt, parse_review_response

class TestStageReview:
    def test_build_review_prompt_includes_quality(self):
        qm = QualityMetrics(score=70, sub_scores={"parse_success_rate": 85.0})
        prompt = build_review_prompt("observe", qm, summary="Found 50 modules")
        assert "observe" in prompt
        assert "70" in prompt
        assert "parse_success_rate" in prompt

    def test_build_review_prompt_includes_component_scores(self):
        child = QualityMetrics(score=45, sub_scores={"complexity_avg": 12.0})
        qm = QualityMetrics(score=70, component_scores={"parser.py": child})
        prompt = build_review_prompt("observe", qm, summary="")
        assert "parser.py" in prompt
        assert "45" in prompt

    def test_parse_review_response(self):
        response = "QUALITY: 7/10\nSUGGESTIONS:\n- Reduce complexity in parser.py\n- Add docstrings"
        result = parse_review_response(response)
        assert len(result.suggestions) == 2

    def test_parse_empty_response(self):
        result = parse_review_response("")
        assert result.suggestions == []
        assert result.rating == 0
```

**Step 2: Implement** `stage_review.py` with `build_review_prompt()` and `parse_review_response()`.

**Step 3: Wire into coordinator** — after gate evaluation, if `ctx.llm_callback` exists, call `build_review_prompt()`, invoke LLM, parse response, attach to `StageQualityReview`.

**Step 4: Run tests, commit**

```bash
git commit -m "feat(pipeline): per-stage LLM review with component-level feedback"
```

---

### Task 12: Quality dashboard accepts pipeline results

**Files:**
- Modify: `src/architecture_model/quality/dashboard.py`
- Test: `tests/test_quality_dashboard.py`

**Step 1: Write the failing test**

```python
def test_dashboard_with_pipeline_results():
    model = _make_model()
    pipeline_results = {
        "observe": StageResult(output=None, quality=QualityMetrics(score=90)),
        "allocate": StageResult(output=None, quality=QualityMetrics(score=85)),
    }
    report = quality_report(model, pipeline_results=pipeline_results)
    assert report.pipeline_quality is not None
    assert report.pipeline_quality["observe"] == 90
```

**Step 2: Implement** — add optional `pipeline_results` and `review_log` params. Add `pipeline_quality: dict[str, float] | None = None` to `QualityReport`.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(dashboard): integrate pipeline stage results into quality report"
```

---

## Phase 4: End-to-End Validation on python-dotenv (Tasks 13-14)

### Task 13: Clone python-dotenv + run pipeline with quality

**Files:**
- Create: `tests/e2e/test_e2e_python_dotenv.py`

**Step 1: Write the test**

```python
"""E2E: python-dotenv pipeline with quality gates and per-component quality."""
import pytest
import subprocess
from pathlib import Path
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.protocol import PipelineContext

@pytest.fixture(scope="module")
def dotenv_repo(tmp_path_factory):
    dest = tmp_path_factory.mktemp("dotenv")
    subprocess.run(
        ["git", "clone", "--depth=1", "https://github.com/theskumar/python-dotenv.git", str(dest / "repo")],
        check=True, capture_output=True,
    )
    return dest / "repo"

class TestE2EPythonDotenv:
    def test_pipeline_with_quality_gates(self, dotenv_repo):
        from architecture_model.pipeline.observe import ObserveStage
        from architecture_model.pipeline.infer import InferStage
        from architecture_model.pipeline.allocate import AllocateStage
        from architecture_model.pipeline.relate import RelateStage
        from architecture_model.pipeline.specify import SpecifyStage
        from architecture_model.pipeline.contract import ContractStage

        ctx = PipelineContext(repo_path=dotenv_repo, output_dir=dotenv_repo / ".arch")
        stages = {
            "observe": ObserveStage(), "infer": InferStage(),
            "allocate": AllocateStage(), "relate": RelateStage(),
            "specify": SpecifyStage(), "contract": ContractStage(),
        }
        coord = PipelineCoordinator(stages)
        results = coord.run_all(ctx)

        # Per-stage quality
        for name, result in results.items():
            assert result.quality.score >= 0

        # Review log populated
        assert len(ctx.review_log) >= len(stages)

        # Per-component quality after allocate
        assert len(results["allocate"].quality.component_scores) > 0

        # No hard gate failures
        for review in ctx.review_log:
            assert not any(gr.blocks for gr in review.gate_results)
```

**Step 2: Run, commit**

```bash
pytest tests/e2e/test_e2e_python_dotenv.py -v --timeout=120
git commit -m "test(e2e): python-dotenv pipeline with hierarchical quality"
```

---

### Task 14: Quality loop + SE docs + update summary on python-dotenv

**Files:**
- Add to: `tests/e2e/test_e2e_python_dotenv.py`

**Step 1: Write the tests**

```python
    def test_quality_loop(self, dotenv_repo):
        from architecture_model.quality.orchestrator import quality_loop
        # Load model from pipeline output, run quality_loop
        # Verify report, feedbacks, diff

    def test_se_doc_generation(self, dotenv_repo):
        from architecture_model.docs.se.generator import generate_se_docs
        # Generate SE docs, verify no errors, >=5 docs generated

    def test_update_summary(self, dotenv_repo):
        from architecture_model.quality.update_summary import subsystem_summary
        # Generate summary, verify structure
```

**Step 2: Run, commit**

```bash
git commit -m "test(e2e): quality loop, SE docs, update summary on python-dotenv"
```

---

## Phase 5: Full Suite Verification (Task 15)

### Task 15: Run full test suite + push

```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py
# Expected: 7 pre-existing failures, 0 regressions, ~1420+ passed
git push
```

---

## Execution Summary

| Task | Phase | What | Complexity | Est. |
|------|-------|------|-----------|------|
| 1 | Protocol | `component_scores` on QualityMetrics | Low | 10 min |
| 2 | Protocol | `QualityGate` with hard/soft + direction | Medium | 15 min |
| 3 | Protocol | `StageQualityReview` + `review_log` | Low | 10 min |
| 4 | Stages | Observe per-module quality | Medium | 20 min |
| 5 | Stages | Allocate per-component aggregation | Medium | 20 min |
| 6 | Stages | Relate/Specify/Contract propagation | Medium | 25 min |
| 7 | Stages | Validate per-component issues | Medium | 15 min |
| 8 | Stages | Decompose/Synthesize per-subsystem rollup | Medium | 20 min |
| 9 | Gates | Default gates per stage | Low | 15 min |
| 10 | Gates | Coordinator enforcement | High | 25 min |
| 11 | Review | Per-stage LLM review | High | 30 min |
| 12 | Dashboard | Pipeline results integration | Medium | 15 min |
| 13 | E2E | python-dotenv pipeline | High | 30 min |
| 14 | E2E | Quality loop + SE docs + summary | Medium | 20 min |
| 15 | Verify | Full suite + push | Low | 10 min |
| **Total** | | **15 tasks, 5 phases** | | **~4.5 hours** |

## Dependency Graph

```
Task 1 (component_scores) ──→ Task 4 (observe) ──→ Task 5 (allocate) ──→ Task 6 (relate/specify/contract)
                                                                      ──→ Task 7 (validate) ──→ Task 8 (decompose/synth)
Task 2 (QualityGate) ──→ Task 9 (default gates) ──→ Task 10 (coordinator)
Task 3 (StageQualityReview) ──→ Task 10 ──→ Task 11 (LLM review)
Task 10 + Task 8 ──→ Task 12 (dashboard) ──→ Task 13 (E2E) ──→ Task 14 (quality+docs) ──→ Task 15 (verify)
```
