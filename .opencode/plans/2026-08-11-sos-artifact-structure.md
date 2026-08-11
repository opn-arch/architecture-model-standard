# System-of-Systems Artifact Structure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the modular extraction pipeline with 3 new stages (decompose, synthesize, emit) that produce a System-of-Systems artifact structure with per-system sub-models, pipeline reports, and accumulated lessons.

**Architecture:** The existing 7-stage pipeline (observe → validate) produces per-stage results. Three new stages consume those results: `decompose` identifies system boundaries, `synthesize` builds per-system sub-models + SoS top-level model by re-running the pipeline scoped to each system's files, and `emit` writes the final artifact structure to disk including pipeline-report.md and lessons.md. The `init` CLI command is removed — the `pipeline` command is the single entry point.

**Tech Stack:** Python 3.11+, dataclasses, YAML, pytest. No new dependencies.

---

## Design Decisions

### System-of-Systems Approach
- The top-level model describes the **system-of-systems**: constituent systems, inter-system interfaces, emergent capabilities, cross-system behaviors, actors
- Each subsystem is an **autonomous system** with its own complete 7-entity-type model (actors, capabilities, behaviors, interfaces, components, constraints)
- System boundary detection uses existing `SYSTEM_THRESHOLD` logic from `core/decomposer.py`

### Adaptive Sub-system Pipeline Depth
- Large systems (complexity > threshold): full 7-stage pipeline re-run
- Small systems (below threshold): abbreviated pass (observe + infer only)
- Threshold: reuse `leaf_threshold` from `run_recursive` (default 5 files)

### Three Documentation Layers
1. **pipeline-report.md** — run log: what happened at each stage this run (deterministic findings + LLM calls + uncertainties)
2. **lessons.md** — accumulated learning summary: what the pipeline has learned across runs
3. **Learning store** (JSON) — structured backing data (corrections, calibration, history)

### Pipeline as Single Entry Point
- `architecture-model init` is removed
- `architecture-model pipeline .` runs full 10-stage pipeline
- `architecture-model pipeline . --stage decompose` runs to specific stage
- MCP orchestrator calls stages individually with LLM enrichment between them

---

## Phase 1: New Stage Types + Decompose Stage

### Task 1.1: DecomposeStage types

**Files:**
- Create: `src/architecture_model/pipeline/decompose_types.py`
- Test: `tests/test_pipeline_decompose.py`

**Step 1: Write the failing test**

```python
"""Tests for decompose stage types."""
from architecture_model.pipeline.decompose_types import (
    SystemBoundary, DecomposeResult,
)

def test_system_boundary_fields():
    sb = SystemBoundary(
        system_id="SYS-core",
        name="Core",
        component_ids=["COMP-1", "COMP-2"],
        files=["src/core/parser.py"],
        complexity=15.0,
        is_full_system=True,
    )
    assert sb.system_id == "SYS-core"
    assert sb.is_full_system is True

def test_decompose_result():
    sb = SystemBoundary(
        system_id="SYS-core", name="Core",
        component_ids=["COMP-1"], files=["a.py"],
        complexity=15.0, is_full_system=True,
    )
    inline = SystemBoundary(
        system_id="SYS-utils", name="Utils",
        component_ids=["COMP-5"], files=["u.py"],
        complexity=3.0, is_full_system=False,
    )
    dr = DecomposeResult(
        systems=[sb], inline_components=[inline],
        inter_system_edges=[("SYS-core", "SYS-utils", "depends-on")],
    )
    assert len(dr.systems) == 1
    assert len(dr.inline_components) == 1
    assert dr.inter_system_edges[0][2] == "depends-on"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_decompose.py -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

```python
"""Output types for the decompose pipeline stage."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class SystemBoundary:
    """A detected system boundary — either autonomous system or inline component."""
    system_id: str
    name: str
    component_ids: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    complexity: float = 0.0
    is_full_system: bool = True  # False = inline component (too small for own system)

@dataclass
class DecomposeResult:
    """Complete system boundary detection output."""
    systems: list[SystemBoundary] = field(default_factory=list)
    inline_components: list[SystemBoundary] = field(default_factory=list)
    inter_system_edges: list[tuple[str, str, str]] = field(default_factory=list)  # (from_sys, to_sys, rel_type)
```

**Step 4: Run test, verify pass**

**Step 5: Commit** — `feat(pipeline): add decompose stage types`

---

### Task 1.2: DecomposeStage implementation

**Files:**
- Create: `src/architecture_model/pipeline/decompose.py`
- Modify: `tests/test_pipeline_decompose.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from architecture_model.pipeline.decompose import DecomposeStage
from architecture_model.pipeline.protocol import PipelineContext, StageResult
from architecture_model.pipeline.allocate_types import AllocationResult, ComponentAllocation
from architecture_model.pipeline.relate_types import RelationshipResult, InferredRelationship
from architecture_model.pipeline.observe_types import ObservationResult, ModuleInfo
from architecture_model.pipeline.decompose_types import DecomposeResult

def _make_ctx(tmp_path) -> PipelineContext:
    """Build a context with allocate + relate results for 3 components."""
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / "out")
    # Fake allocate result: 2 large components, 1 small
    alloc = AllocationResult(components=[
        ComponentAllocation(id="COMP-1", name="Core", files=[
            Path(f"src/core/f{i}.py") for i in range(10)
        ]),
        ComponentAllocation(id="COMP-2", name="Manifest", files=[
            Path(f"src/manifest/f{i}.py") for i in range(8)
        ]),
        ComponentAllocation(id="COMP-3", name="Utils", files=[
            Path("src/utils/helpers.py"),
        ]),
    ])
    ctx.cache["allocate"] = StageResult(
        output=alloc, quality=_q(), diagnostics=[], uncertainties=[]
    )
    # Fake relate result with cross-component edges
    rels = RelationshipResult(relationships=[
        InferredRelationship(from_id="COMP-1", to_id="COMP-3", rel_type="depends-on"),
        InferredRelationship(from_id="COMP-2", to_id="COMP-1", rel_type="depends-on"),
    ])
    ctx.cache["relate"] = StageResult(
        output=rels, quality=_q(), diagnostics=[], uncertainties=[]
    )
    return ctx

def _q():
    from architecture_model.pipeline.protocol import QualityMetrics
    return QualityMetrics(score=100.0)

def test_decompose_identifies_systems(tmp_path):
    ctx = _make_ctx(tmp_path)
    stage = DecomposeStage()
    result = stage.run(ctx)
    dr: DecomposeResult = result.output
    # Core (10 files) and Manifest (8 files) should be systems
    sys_names = {s.name for s in dr.systems}
    assert "Core" in sys_names
    assert "Manifest" in sys_names
    # Utils (1 file) should be inline
    inline_names = {s.name for s in dr.inline_components}
    assert "Utils" in inline_names

def test_decompose_inter_system_edges(tmp_path):
    ctx = _make_ctx(tmp_path)
    stage = DecomposeStage()
    result = stage.run(ctx)
    dr: DecomposeResult = result.output
    # COMP-2 (Manifest) depends on COMP-1 (Core) → inter-system edge
    edge_pairs = [(e[0], e[1]) for e in dr.inter_system_edges]
    # Find the edge between the systems containing COMP-2 and COMP-1
    assert len(dr.inter_system_edges) >= 1
```

**Step 2: Run test to verify it fails**

**Step 3: Implement DecomposeStage**

```python
"""Decompose stage — detect system boundaries from allocated components."""
from __future__ import annotations
from architecture_model.pipeline.protocol import Stage, StageResult, PipelineContext, QualityMetrics, Diagnostic
from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.allocate_types import AllocationResult
from architecture_model.pipeline.relate_types import RelationshipResult

FULL_SYSTEM_FILE_THRESHOLD = 5  # components with >= this many files become autonomous systems

class DecomposeStage:
    name = "decompose"
    version = "1.0"
    requires = ["allocate", "relate"]

    def can_run(self, ctx: PipelineContext) -> bool:
        return ctx.has("allocate") and ctx.has("relate")

    def output_path(self, ctx: PipelineContext):
        return ctx.output_dir / "decompose.yaml"

    def run(self, ctx: PipelineContext) -> StageResult[DecomposeResult]:
        import time
        t0 = time.monotonic()

        alloc: AllocationResult = ctx.get("allocate").output
        rels: RelationshipResult = ctx.get("relate").output

        systems, inlines = [], []
        comp_to_sys: dict[str, str] = {}

        for comp in alloc.components:
            is_full = len(comp.files) >= FULL_SYSTEM_FILE_THRESHOLD
            sys_id = f"SYS-{comp.name.lower().replace(' ', '-')}"
            sb = SystemBoundary(
                system_id=sys_id,
                name=comp.name,
                component_ids=[comp.id],
                files=[str(f) for f in comp.files],
                complexity=float(len(comp.files)),
                is_full_system=is_full,
            )
            if is_full:
                systems.append(sb)
            else:
                inlines.append(sb)
            comp_to_sys[comp.id] = sys_id

        # Build inter-system edges from cross-component relationships
        inter_edges = []
        for rel in rels.relationships:
            from_sys = comp_to_sys.get(rel.from_id)
            to_sys = comp_to_sys.get(rel.to_id)
            if from_sys and to_sys and from_sys != to_sys:
                inter_edges.append((from_sys, to_sys, rel.rel_type))

        result = DecomposeResult(
            systems=systems,
            inline_components=inlines,
            inter_system_edges=inter_edges,
        )

        duration = int((time.monotonic() - t0) * 1000)
        diagnostics = []
        if not systems:
            diagnostics.append(Diagnostic(
                severity="warning", code="NO_SYSTEMS",
                message="No components large enough to be autonomous systems",
            ))

        quality = QualityMetrics(
            score=100.0 if systems else 50.0,
            sub_scores={"system_count": len(systems), "inline_count": len(inlines)},
        )

        return StageResult(
            output=result, quality=quality,
            diagnostics=diagnostics, uncertainties=[],
            duration_ms=duration,
        )
```

**Step 4: Run tests, verify pass**

**Step 5: Commit** — `feat(pipeline): add decompose stage for system boundary detection`

---

## Phase 2: LLM Call Tracking + Pipeline Report Generation

### Task 2.0: LLM Call Record type (arch-std, protocol layer)

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py`
- Test: `tests/test_pipeline_protocol.py` (extend)

The pipeline protocol defines the **LLMCallRecord** dataclass. This lives in arch-std (not opencode-arch) because the report generator needs it and the report generator is deterministic code.

The MCP orchestrator (opencode-arch) populates these records; the pipeline report generator (arch-std) renders them.

```python
@dataclass
class LLMCallRecord:
    """Record of a single LLM invocation during pipeline execution."""
    # Identity
    stage: str                          # which pipeline stage triggered this
    purpose: str                        # e.g. "capability_naming", "behavior_synthesis", "uncertainty_resolution"
    timestamp: str = ""                 # ISO 8601

    # Input
    files_sent: list[str] = field(default_factory=list)       # file paths included in context
    slices_sent: list[str] = field(default_factory=list)      # slice IDs (e.g. "F1", "COMP-3")
    prompt_template: str = ""                                  # template name or first 200 chars
    prompt_tokens: int = 0                                     # token count of full prompt
    context_tokens: int = 0                                    # tokens from file/slice content only

    # Output
    completion_tokens: int = 0
    total_tokens: int = 0              # prompt_tokens + completion_tokens
    model: str = ""                    # e.g. "claude-sonnet-4-20250514"
    duration_ms: int = 0
    cached: bool = False               # served from LLM cache

    # Quality
    output_used: bool = True           # was the LLM output actually used (vs fallback)
    confidence: float = 0.0            # agent's confidence in the output
    items_produced: int = 0            # e.g. "3 capabilities renamed"
    notes: str = ""                    # free-form quality note

    @property
    def compression_ratio(self) -> float:
        """How much context was compressed vs raw file tokens."""
        if self.context_tokens == 0:
            return 0.0
        # Estimate raw file tokens (rough: 4 chars per token, read file sizes)
        return self.context_tokens / max(self.prompt_tokens, 1)
```

**Test:**

```python
def test_llm_call_record():
    from architecture_model.pipeline.protocol import LLMCallRecord
    rec = LLMCallRecord(
        stage="infer", purpose="capability_naming",
        files_sent=["src/core/parser.py", "src/core/validator.py"],
        slices_sent=["COMP-1"],
        prompt_tokens=1200, context_tokens=800,
        completion_tokens=350, total_tokens=1550,
        model="claude-sonnet-4-20250514", duration_ms=2300,
        items_produced=5, confidence=0.91,
    )
    assert rec.total_tokens == 1550
    assert rec.stage == "infer"
    assert len(rec.files_sent) == 2
```

**Commit** — `feat(protocol): add LLMCallRecord for pipeline observability`

---

### Task 2.1: Report types + generator

**Files:**
- Create: `src/architecture_model/pipeline/report.py`
- Test: `tests/test_pipeline_report.py`

**Step 1: Write the failing test**

```python
"""Tests for pipeline report generation."""
from architecture_model.pipeline.report import generate_pipeline_report, StageReport
from architecture_model.pipeline.protocol import (
    StageResult, QualityMetrics, Diagnostic, Uncertainty, LLMCallRecord,
)

def test_stage_report_with_llm_calls():
    llm_calls = [
        LLMCallRecord(
            stage="infer", purpose="capability_naming",
            files_sent=["src/core/parser.py", "src/core/validator.py"],
            slices_sent=["COMP-1"],
            prompt_tokens=1200, context_tokens=800,
            completion_tokens=350, total_tokens=1550,
            model="claude-sonnet-4-20250514", duration_ms=2300,
            items_produced=5, confidence=0.91,
        ),
        LLMCallRecord(
            stage="infer", purpose="uncertainty_resolution",
            files_sent=["src/core/types.py"],
            prompt_tokens=600, completion_tokens=150, total_tokens=750,
            model="claude-sonnet-4-20250514", duration_ms=1100,
            items_produced=1, confidence=0.75,
            notes="Resolved ambiguous module categorization",
        ),
    ]
    sr = StageReport(
        stage_name="infer",
        duration_ms=3500,
        score=88.0,
        deterministic_findings=["Inferred 12 capabilities from public APIs"],
        llm_calls=llm_calls,
        diagnostics=[Diagnostic(severity="warning", code="W1", message="low confidence capability")],
        uncertainties=[],
    )
    md = sr.to_markdown()
    assert "## Stage: infer" in md
    assert "### LLM Calls (2)" in md
    assert "capability_naming" in md
    assert "src/core/parser.py" in md
    assert "1,550 tokens" in md or "1550" in md
    assert "claude-sonnet" in md
    assert "uncertainty_resolution" in md

def test_report_llm_summary_totals():
    """Report should include aggregate LLM token usage."""
    llm_calls = [
        LLMCallRecord(stage="infer", purpose="naming",
            prompt_tokens=1200, completion_tokens=350, total_tokens=1550,
            model="claude-sonnet-4-20250514", duration_ms=2000),
        LLMCallRecord(stage="specify", purpose="contract_summary",
            prompt_tokens=800, completion_tokens=200, total_tokens=1000,
            model="claude-sonnet-4-20250514", duration_ms=1500),
    ]
    results = {
        "infer": StageResult(
            output=None, quality=QualityMetrics(score=88.0),
            diagnostics=[], uncertainties=[], duration_ms=50,
        ),
        "specify": StageResult(
            output=None, quality=QualityMetrics(score=92.0),
            diagnostics=[], uncertainties=[], duration_ms=30,
        ),
    }
    report = generate_pipeline_report(results, system_name="Core", llm_calls=llm_calls)
    assert "# Pipeline Report: Core" in report
    # Should have a summary section with total tokens
    assert "2,550" in report or "2550" in report  # total tokens across all calls
    assert "2 LLM calls" in report or "LLM Calls: 2" in report

def test_report_no_llm_calls():
    """Deterministic-only run should say so explicitly."""
    results = {
        "observe": StageResult(
            output=None, quality=QualityMetrics(score=95.0),
            diagnostics=[], uncertainties=[], duration_ms=100,
        ),
    }
    report = generate_pipeline_report(results, system_name="Core", llm_calls=[])
    assert "No LLM calls" in report or "deterministic" in report.lower()
```

**Step 2: Run test to verify it fails**

**Step 3: Implement report generator**

The `generate_pipeline_report()` function takes `dict[str, StageResult]` + `llm_calls: list[LLMCallRecord]` and produces markdown with:

**Header section:**
- System name, timestamp, total duration
- LLM summary: total calls, total tokens (prompt/completion), total cost estimate, models used
- Stage scores overview table

**Per-stage sections:**
- Duration, quality score
- Deterministic findings (extracted from stage output via `_extract_findings`)
- LLM calls for this stage (filtered from `llm_calls` by `stage` field), each showing:
  - Purpose
  - Files sent (list)
  - Slices sent (list)
  - Token breakdown: prompt / context / completion / total
  - Model used
  - Duration
  - Quality: confidence, items produced, cached?, output used?
  - Notes
- Diagnostics and uncertainties

**Footer:**
- Aggregate token economics: total prompt tokens, total completion tokens, files touched
- Slicing strategy analysis: which slices were used most, compression ratios

A `_extract_findings(stage_name, result)` function introspects the output type to extract human-readable findings (e.g., for observe: "Discovered N modules, M functions, C classes").

**Example output section:**

```markdown
## Stage: infer
**Score:** 88.0 | **Duration:** 3,500ms

### Deterministic Findings
- Inferred 12 capabilities from public APIs
- 3 parent capabilities from module grouping

### LLM Calls (2)

#### 1. capability_naming (2,300ms)
- **Model:** claude-sonnet-4-20250514
- **Files sent:** `src/core/parser.py`, `src/core/validator.py`
- **Slices:** COMP-1
- **Tokens:** 1,200 prompt (800 context) → 350 completion = 1,550 total
- **Result:** 5 capabilities renamed (confidence: 0.91)

#### 2. uncertainty_resolution (1,100ms)
- **Model:** claude-sonnet-4-20250514
- **Files sent:** `src/core/types.py`
- **Tokens:** 600 prompt → 150 completion = 750 total
- **Result:** 1 item resolved (confidence: 0.75)
- **Note:** Resolved ambiguous module categorization

### Diagnostics
- ⚠️ W1: low confidence capability
```

**Step 4: Run tests, verify pass**

**Step 5: Commit** — `feat(pipeline): add pipeline report generator with LLM call tracking`

---

### Task 2.2: Lessons generator

**Files:**
- Create: `src/architecture_model/pipeline/lessons.py`
- Test: `tests/test_pipeline_lessons.py`

**Step 1: Write the failing test**

```python
"""Tests for lessons summary generation."""
from architecture_model.pipeline.lessons import generate_lessons, LessonEntry
from architecture_model.pipeline.protocol import Diagnostic, Uncertainty

def test_lesson_from_diagnostics():
    diags = [
        Diagnostic(severity="warning", code="LOW_COVERAGE", message="File coverage 82%"),
        Diagnostic(severity="warning", code="LOW_COVERAGE", message="File coverage 79%"),
    ]
    lessons = LessonEntry.from_diagnostics("allocate", diags)
    assert len(lessons) >= 1
    assert "coverage" in lessons[0].summary.lower()

def test_generate_lessons_markdown():
    entries = [
        LessonEntry(stage="infer", summary="Public _-prefix functions miscategorized as private", count=3),
        LessonEntry(stage="specify", summary="Cross-system interface detection found 8 contracts", count=1),
    ]
    md = generate_lessons(entries, system_name="Core")
    assert "# Lessons: Core" in md
    assert "## Stage: infer" in md
    assert "miscategorized" in md
```

**Step 2: Run test to verify it fails**

**Step 3: Implement lessons generator**

`LessonEntry` dataclass: `stage`, `summary`, `count`, `severity`. Class method `from_diagnostics()` aggregates repeated diagnostic codes into lessons. `from_uncertainties()` does the same for uncertainties.

`generate_lessons()` takes `list[LessonEntry]` + optional learning store data and produces markdown grouped by stage.

**Step 4: Run tests, verify pass**

**Step 5: Commit** — `feat(pipeline): add lessons summary generator`

---

## Phase 3: Synthesize Stage

### Task 3.1: SynthesizeStage types

**Files:**
- Create: `src/architecture_model/pipeline/synthesize_types.py`
- Test: `tests/test_pipeline_synthesize.py`

**Step 1: Write the failing test**

```python
from architecture_model.pipeline.synthesize_types import (
    SystemModel, SoSModel, SynthesizeResult,
)

def test_system_model():
    sm = SystemModel(
        system_id="SYS-core",
        name="Core",
        model_yaml="",
        manifest_json="",
        pipeline_report_md="# Pipeline Report: Core",
        lessons_md="# Lessons: Core",
        stage_results={},
    )
    assert sm.system_id == "SYS-core"

def test_synthesize_result():
    sr = SynthesizeResult(
        sos_model_yaml="meta:\n  project: test",
        system_models=[],
        top_manifest_json="{}",
    )
    assert "project: test" in sr.sos_model_yaml
```

**Step 2: Run test to verify it fails**

**Step 3: Implement types**

```python
"""Output types for the synthesize pipeline stage."""
from __future__ import annotations
from dataclasses import dataclass, field
from architecture_model.pipeline.protocol import StageResult, LLMCallRecord

@dataclass
class SystemModel:
    """A complete autonomous system model produced by scoped pipeline run."""
    system_id: str
    name: str
    model_yaml: str  # serialized .architecture-model.yaml content
    manifest_json: str  # serialized manifest.json content
    pipeline_report_md: str
    lessons_md: str
    stage_results: dict[str, StageResult]  # raw results for further processing
    llm_calls: list[LLMCallRecord] = field(default_factory=list)  # all LLM calls for this system

@dataclass
class SoSModel:
    """The System-of-Systems top-level model."""
    model_yaml: str
    actors: list[dict]  # serialized actor entities
    emergent_capabilities: list[dict]
    cross_system_behaviors: list[dict]
    inter_system_interfaces: list[dict]
    constraints: list[dict]

@dataclass
class SynthesizeResult:
    """Complete synthesis output."""
    sos_model: SoSModel | None = None
    sos_model_yaml: str = ""  # convenience: serialized top-level model
    system_models: list[SystemModel] = field(default_factory=list)
    top_manifest_json: str = ""
    pipeline_report_md: str = ""  # top-level pipeline report
    lessons_md: str = ""  # top-level lessons
    all_llm_calls: list[LLMCallRecord] = field(default_factory=list)  # all LLM calls across all systems
```

**Step 4: Run tests, verify pass**

**Step 5: Commit** — `feat(pipeline): add synthesize stage types`

---

### Task 3.2: SynthesizeStage implementation

**Files:**
- Create: `src/architecture_model/pipeline/synthesize.py`
- Modify: `tests/test_pipeline_synthesize.py`

This is the most complex stage. It:

1. Takes `DecomposeResult` (system boundaries) + all prior stage results
2. For each system boundary where `is_full_system=True`:
   a. Creates a scoped `PipelineContext` with `scope_files` = system's files
   b. Decides pipeline depth: full 7 stages if `len(files) >= FULL_PIPELINE_THRESHOLD`, else observe+infer only
   c. Runs the scoped pipeline via the coordinator
   d. Builds an `ArchitectureModel` from the scoped results
   e. Generates pipeline-report.md and lessons.md for this system
3. For inline components: creates minimal model entries
4. Assembles the SoS top-level model:
   - Actors = entry points into the SoS from outside (CLI, MCP, external consumers)
   - Emergent capabilities = capabilities that require multiple systems working together
   - Cross-system behaviors = call chains crossing system boundaries
   - Inter-system interfaces = symbols imported across system boundaries
   - Constraints = system-level NFRs
5. Generates top-level pipeline-report.md and lessons.md

**Key implementation detail:** The synthesize stage needs access to a `PipelineCoordinator` to run scoped sub-pipelines. It receives this via `PipelineContext.config["coordinator"]` (set by the CLI or MCP orchestrator).

**Step 1: Write tests** (scoped pipeline run, SoS model assembly, report generation)

**Step 2: Implement** — split into internal functions:
- `_run_scoped_pipeline(ctx, coordinator, boundary) -> SystemModel`
- `_build_system_model(stage_results, boundary) -> str` (YAML)
- `_build_sos_model(systems, inlines, inter_edges, top_results) -> SoSModel`
- `_decide_pipeline_depth(boundary) -> list[str]` (which stages to run)

**Step 3: Commit** — `feat(pipeline): add synthesize stage with scoped sub-pipelines`

---

## Phase 4: Emit Stage

### Task 4.1: EmitStage types + implementation

**Files:**
- Create: `src/architecture_model/pipeline/emit_types.py`
- Create: `src/architecture_model/pipeline/emit.py`
- Test: `tests/test_pipeline_emit.py`

The emit stage writes the final artifact structure to disk:

```
.architecture-models/
├── manifest.json
├── .architecture-model.yaml          ← SoS model
├── pipeline-report.md                ← top-level report
├── lessons.md                        ← top-level lessons
├── core/
│   ├── .architecture-model.yaml      ← autonomous system model
│   ├── manifest.json
│   ├── pipeline-report.md
│   └── lessons.md
├── pipeline/
│   ├── ...
└── docs/
    ├── capability-tree.md
    ├── behavior-flows.md
    ├── system-interactions.md
    └── diagrams/
        ├── sos-context.mmd
        ├── system-interactions.mmd
        └── per-system/*.mmd
```

**EmitResult:**
```python
@dataclass
class EmitResult:
    written_paths: list[str] = field(default_factory=list)
    total_bytes: int = 0
    system_count: int = 0
    doc_count: int = 0
```

**EmitStage.run():**
1. Reads `SynthesizeResult` from context
2. Creates output directory structure
3. Writes SoS model, per-system models, manifests
4. Writes pipeline-report.md and lessons.md at each level
5. Generates docs from model data (capability tree, behavior flows, system interactions)
6. Generates Mermaid diagrams with actual relationships (not bare nodes)

**Step 1: Write tests** (directory structure, file existence, content verification)

**Step 2: Implement**

**Step 3: Commit** — `feat(pipeline): add emit stage for SoS artifact output`

---

## Phase 5: Wire Everything Together

### Task 5.1: Register new stages in coordinator + CLI

**Files:**
- Modify: `src/architecture_model/cli/main.py` (pipeline command, remove init)
- Modify: `src/architecture_model/pipeline/__init__.py` (exports)

**Changes:**
1. Add decompose, synthesize, emit to stage registration in CLI pipeline command
2. Pass coordinator reference into context for synthesize stage
3. Remove `_cmd_init` function and `init` subparser
4. Update `__init__.py` exports

```python
stages = {
    "observe": ObserveStage(),
    "infer": InferStage(),
    "allocate": AllocateStage(),
    "relate": RelateStage(),
    "specify": SpecifyStage(),
    "contract": ContractStage(),
    "validate": ValidateStage(),
    "decompose": DecomposeStage(),
    "synthesize": SynthesizeStage(),
    "emit": EmitStage(),
}
```

**Step 1: Write integration test** — full 10-stage pipeline on a fixture repo

**Step 2: Wire up**

**Step 3: Commit** — `feat(pipeline): register 10 stages, remove init command`

---

### Task 5.2: Update run_recursive to use decompose stage

**Files:**
- Modify: `src/architecture_model/pipeline/coordinator.py`

Replace the current `run_recursive` (which uses allocate output to decide recursion) with logic that delegates to the decompose + synthesize stages. The coordinator's `run_all` now runs all 10 stages including the recursive sub-pipeline runs inside synthesize.

**Step 1: Write test** for new recursive behavior

**Step 2: Modify coordinator**

**Step 3: Commit** — `refactor(pipeline): coordinator delegates recursion to decompose+synthesize`

---

## Phase 6: MCP Orchestrator Updates (opencode-arch)

### Task 6.1: Update extract.py to use pipeline stages with LLM call recording

**Files:**
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/extract.py`

Replace the monolithic `store_extraction()` with stage-by-stage orchestration:
1. Call each pipeline stage deterministically
2. Between stages, do LLM enrichment (rename capabilities, synthesize behavior narratives, etc.)
3. For EVERY LLM call, create an `LLMCallRecord` capturing:
   - Which files were sent (resolved from slices/context)
   - Token counts (prompt, context, completion)
   - Model used
   - What the LLM produced and whether it was used
4. Accumulate all `LLMCallRecord`s in a list
5. Pass the full list to `generate_pipeline_report()` and `generate_lessons()`
6. Write reports to the system's output directory

**LLM call recording pattern (every call site):**

```python
from architecture_model.pipeline.protocol import LLMCallRecord
import time

# Before LLM call
t0 = time.monotonic()
files_for_context = [str(f) for f in component.files]
slice_context = architect_slice(repo_path, focus=comp_id)
prompt = build_prompt(slice_context, uncertainties)
prompt_tokens = estimate_tokens(prompt)
context_tokens = estimate_tokens(slice_context)

# LLM call
result = await cached_llm_call(runner, prompt, ...)

# After LLM call
duration = int((time.monotonic() - t0) * 1000)
llm_calls.append(LLMCallRecord(
    stage="infer",
    purpose="capability_naming",
    files_sent=files_for_context,
    slices_sent=[comp_id],
    prompt_template=prompt[:200],
    prompt_tokens=prompt_tokens,
    context_tokens=context_tokens,
    completion_tokens=estimate_tokens(result.output),
    total_tokens=prompt_tokens + estimate_tokens(result.output),
    model=result.model,
    duration_ms=duration,
    cached=result.cached,
    output_used=True,
    confidence=0.9,
    items_produced=len(renamed_caps),
    notes=f"Renamed {len(renamed_caps)} capabilities",
))
```

**Step 1: Refactor extract.py** to call pipeline stages

**Step 2: Add LLM call recording** at every LLM invocation point

**Step 3: Commit** — `refactor(mcp): extract uses pipeline stages with LLM call recording`

---

### Task 6.2: PipelineContext carries LLM call log

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py`

Add `llm_calls: list[LLMCallRecord]` to `PipelineContext`. The MCP orchestrator appends to this list after each LLM call. The report/lessons generators read from it.

```python
@dataclass
class PipelineContext:
    repo_path: Path
    output_dir: Path = ...
    # ... existing fields ...
    llm_calls: list[LLMCallRecord] = field(default_factory=list)  # NEW
```

This is the bridge: opencode-arch writes to `ctx.llm_calls`, arch-std reads from it in report/lessons generators.

**Commit** — `feat(protocol): PipelineContext carries LLM call log`

---

### Task 6.3: Expose pipeline-report and lessons via MCP

**Files:**
- Modify or create MCP tool for pipeline report retrieval

The MCP orchestrator should be able to:
- Return pipeline-report.md for any system
- Return lessons.md for any system
- Include LLM call details in reports

---

## Phase 7: Cleanup

### Task 7.1: Remove legacy code

**Files:**
- Delete or deprecate: `src/architecture_model/orchestration/pipeline.py` (legacy `run_pipeline`)
- Delete or deprecate: `src/architecture_model/orchestration/full_extraction.py` (legacy `full_extraction`)
- Update: imports that reference removed code

### Task 7.2: Update CONTEXT.md

Update the documented artifact structure, stage count (10), and remove references to `init`.

### Task 7.3: Re-extract both repos

Run the new 10-stage pipeline on:
1. architecture-model-standard
2. opencode-arch

Verify: SoS structure, sub-models, pipeline reports, lessons, diagrams with edges.

---

## Summary

| Phase | Tasks | What it produces |
|-------|-------|-----------------|
| 1 | Decompose stage (types + impl) | System boundary detection |
| 2 | LLMCallRecord + Report + Lessons generators | LLMCallRecord type, pipeline-report.md (with every LLM call, files sent, tokens), lessons.md |
| 3 | Synthesize stage (types + impl) | Scoped sub-pipeline runs → per-system models + SoS model, LLM calls aggregated |
| 4 | Emit stage | Artifact structure on disk (models, reports, lessons, docs, diagrams) |
| 5 | Wiring | 10-stage pipeline registration, kill `init` |
| 6 | MCP updates | LLM call recording at every invocation, PipelineContext.llm_calls bridge |
| 7 | Cleanup | Remove legacy, re-extract both repos |

**Estimated new/modified files:** ~13 new, ~6 modified in arch-std; ~3 modified in opencode-arch
**Estimated new tests:** ~9 test files, ~50 test cases
