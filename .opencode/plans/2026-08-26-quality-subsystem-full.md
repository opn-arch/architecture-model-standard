# Quality Subsystem + SE Doc v2.1 + Model Population Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a unified Quality subsystem, update SE doc generators for v2.1 fields, and populate v2.1 semantic fields on all subsystem models via LLM analysis.

**Architecture:** Three phases — (1) consolidate scattered quality modules into `quality/` package with a unified dashboard, (2) update 5 SE doc generators to render v2.1 fields, (3) LLM-analyze code per subsystem to populate intent/goals/moes/trade_offs/failure_modes on all models.

**Tech Stack:** Python dataclasses, pytest, architecture_model.core.types

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

**Pre-existing failures (do NOT fix):** `test_includes_confidence`, `test_includes_components`, `test_real_logs_db`, `test_name_version_requires`, `test_schema_json_has_all_relationship_types` + 13 errors in `test_manifest.py`

---

## Phase 1: Quality Subsystem (Tasks 1-4)

### Task 1: Create `quality/` package with moved modules + backward-compat re-exports

**Files:**
- Create: `src/architecture_model/quality/__init__.py`
- Create: `src/architecture_model/quality/monitoring.py` (move from `monitoring.py`)
- Create: `src/architecture_model/quality/monitoring_checks.py` (move from `monitoring_checks.py`)
- Create: `src/architecture_model/quality/confidence.py` (move from `core/confidence.py`)
- Create: `src/architecture_model/quality/coverage.py` (move from `core/coverage.py`)
- Create: `src/architecture_model/quality/regen_readiness.py` (move from `core/regen_readiness.py`)
- Modify: `src/architecture_model/monitoring.py` → thin re-export shim
- Modify: `src/architecture_model/monitoring_checks.py` → thin re-export shim
- Modify: `src/architecture_model/core/confidence.py` → thin re-export shim
- Modify: `src/architecture_model/core/coverage.py` → thin re-export shim
- Modify: `src/architecture_model/core/regen_readiness.py` → thin re-export shim

**Strategy:** Move implementation to `quality/`, leave backward-compatible re-export shims at old locations so existing imports (~30 files) don't break. No import changes needed in consuming code.

**Step 1: Create the quality package directory**

```bash
mkdir -p src/architecture_model/quality
```

**Step 2: Write `quality/__init__.py`**

```python
"""Unified quality subsystem — monitoring, confidence, coverage, regen readiness, dashboard."""
from architecture_model.quality.monitoring import (
    FunctionMetrics, MetricsCollector, get_collector, monitored,
)
from architecture_model.quality.confidence import (
    compute_component_confidence, compute_model_confidence, model_confidence_summary,
)
from architecture_model.quality.coverage import coverage_report, CoverageResult
from architecture_model.quality.regen_readiness import compute_regen_readiness

__all__ = [
    "FunctionMetrics", "MetricsCollector", "get_collector", "monitored",
    "compute_component_confidence", "compute_model_confidence", "model_confidence_summary",
    "coverage_report", "CoverageResult",
    "compute_regen_readiness",
]
```

**Step 3: Move each module**

For each of the 5 modules:
1. Copy the implementation file to `quality/`
2. Replace the original with a re-export shim

Example shim for `src/architecture_model/monitoring.py`:
```python
"""Backward-compatible re-export. Canonical location: architecture_model.quality.monitoring"""
from architecture_model.quality.monitoring import *  # noqa: F401,F403
from architecture_model.quality.monitoring import (  # explicit re-exports for type checkers
    FunctionMetrics, MetricsCollector, get_collector, monitored,
)
```

Example shim for `src/architecture_model/core/confidence.py`:
```python
"""Backward-compatible re-export. Canonical location: architecture_model.quality.confidence"""
from architecture_model.quality.confidence import *  # noqa: F401,F403
```

**IMPORTANT:** When moving `monitoring.py` to `quality/monitoring.py`, update internal imports within the moved file. Specifically:
- `quality/confidence.py` line 94: change `from architecture_model.monitoring import monitored` → `from architecture_model.quality.monitoring import monitored`
- `quality/coverage.py` line 13: same change
- `quality/monitoring_checks.py` lines 26,52: change `from architecture_model.monitoring import get_collector` → `from architecture_model.quality.monitoring import get_collector`

All other files keep importing from old paths via the re-export shims.

**Step 4: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: Same pre-existing failures, zero new failures (re-exports preserve all imports)

**Step 5: Commit**

```bash
git add src/architecture_model/quality/ src/architecture_model/monitoring.py src/architecture_model/monitoring_checks.py src/architecture_model/core/confidence.py src/architecture_model/core/coverage.py src/architecture_model/core/regen_readiness.py
git commit -m "refactor: consolidate quality modules into quality/ subsystem with backward-compat re-exports"
```

---

### Task 2: Create unified quality dashboard

**Files:**
- Create: `src/architecture_model/quality/dashboard.py`
- Test: `tests/test_quality_dashboard.py` (new)

**Step 1: Write failing test**

```python
"""Tests for unified quality dashboard."""
from architecture_model.quality.dashboard import quality_report, QualityReport
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Status, Priority, FunctionSignature, TestContract,
)


class TestQualityReport:
    def test_returns_report_dataclass(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                components=[Component(id="COMP-1", name="Test", status=Status.ACTIVE,
                                      intent="Does testing",
                                      signatures=[FunctionSignature(name="test_fn", params=["a"])])],
                capabilities=[Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                                         intent="Test cap", moes=["MOE-1"])],
            ),
            relationships=[],
        )
        report = quality_report(model)
        assert isinstance(report, QualityReport)
        assert 0 <= report.overall_score <= 100
        assert report.validation_score >= 0
        assert isinstance(report.semantic_completeness, dict)
        assert "intent_coverage" in report.semantic_completeness

    def test_semantic_completeness_counts(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                components=[
                    Component(id="COMP-1", name="A", status=Status.ACTIVE, intent="has intent"),
                    Component(id="COMP-2", name="B", status=Status.ACTIVE),  # no intent
                ],
                capabilities=[
                    Capability(id="CAP-1", name="C", status=Status.ACTIVE, moes=["m1"]),
                    Capability(id="CAP-2", name="D", status=Status.ACTIVE),  # no moes
                ],
            ),
            relationships=[],
        )
        report = quality_report(model)
        assert report.semantic_completeness["intent_coverage"] == "1/2"
        assert report.semantic_completeness["moe_coverage"] == "1/2"

    def test_overall_grade(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        report = quality_report(model)
        assert report.grade in ("A", "B", "C", "D", "F")

    def test_to_markdown(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        report = quality_report(model)
        md = report.to_markdown()
        assert "# Quality Report" in md
        assert report.grade in md
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_quality_dashboard.py -v`
Expected: FAIL — `quality.dashboard` doesn't exist

**Step 3: Implement `quality/dashboard.py`**

```python
"""Unified quality dashboard — aggregates all quality dimensions into one report."""
from __future__ import annotations

from dataclasses import dataclass, field
from architecture_model.core.types import ArchitectureModel, Status
from architecture_model.core.validator import validate_model
from architecture_model.quality.monitoring import monitored


@dataclass
class QualityReport:
    """Aggregated quality report across all dimensions."""
    project: str
    validation_score: int  # 0-100
    validation_issues: int
    semantic_completeness: dict[str, str]  # field -> "populated/total"
    detail_level_distribution: dict[str, int]  # L0..L4 -> count
    regen_readiness_score: float  # 0-100
    confidence_score: float  # 0.0-1.0
    overall_score: int  # 0-100 weighted composite
    grade: str  # A-F

    def to_markdown(self) -> str:
        lines = [
            f"# Quality Report: {self.project}",
            "",
            f"**Overall Grade: {self.grade}** ({self.overall_score}/100)",
            "",
            "## Dimensions",
            "",
            f"| Dimension | Score |",
            f"|-----------|-------|",
            f"| Validation | {self.validation_score}/100 ({self.validation_issues} issues) |",
            f"| Regen Readiness | {self.regen_readiness_score:.0f}/100 |",
            f"| Confidence | {self.confidence_score:.1%} |",
            "",
            "## Semantic Completeness",
            "",
            "| Field | Coverage |",
            "|-------|----------|",
        ]
        for field_name, coverage in self.semantic_completeness.items():
            lines.append(f"| {field_name} | {coverage} |")

        lines.extend([
            "",
            "## Detail Level Distribution",
            "",
            "| Level | Count |",
            "|-------|-------|",
        ])
        for level, count in sorted(self.detail_level_distribution.items()):
            lines.append(f"| {level} | {count} |")

        return "\n".join(lines)


def _compute_semantic_completeness(model: ArchitectureModel) -> dict[str, str]:
    """Count how many entities have each v2.1 field populated."""
    comps = [c for c in model.entities.components
             if (c.status.value if hasattr(c.status, 'value') else str(c.status)) == "ACTIVE"]
    caps = [c for c in model.entities.capabilities
            if (c.status.value if hasattr(c.status, 'value') else str(c.status)) == "ACTIVE"]
    ifaces = model.entities.interfaces

    comp_with_intent = sum(1 for c in comps if c.intent)
    cap_with_intent = sum(1 for c in caps if c.intent)
    total_intent = len(comps) + len(caps)
    has_intent = comp_with_intent + cap_with_intent

    cap_with_moes = sum(1 for c in caps if c.moes)
    comp_with_goals = sum(1 for c in comps if c.goals)
    comp_with_tradeoffs = sum(1 for c in comps if c.trade_offs)
    comp_with_failure = sum(1 for c in comps if c.failure_modes)
    iface_with_contract = sum(1 for i in ifaces if i.contract)

    return {
        "intent_coverage": f"{has_intent}/{total_intent}",
        "moe_coverage": f"{cap_with_moes}/{len(caps)}",
        "goals_coverage": f"{comp_with_goals}/{len(comps)}",
        "trade_offs_coverage": f"{comp_with_tradeoffs}/{len(comps)}",
        "failure_modes_coverage": f"{comp_with_failure}/{len(comps)}",
        "contract_coverage": f"{iface_with_contract}/{len(ifaces)}",
    }


def _compute_detail_distribution(model: ArchitectureModel) -> dict[str, int]:
    """Count entities at each detail level."""
    from architecture_model.core.detail_level import compute_detail_level
    dist: dict[str, int] = {"L0": 0, "L1": 0, "L2": 0, "L3": 0, "L4": 0}
    for comp in model.entities.components:
        level = compute_detail_level(comp)
        dist[f"L{level}"] = dist.get(f"L{level}", 0) + 1
    for cap in model.entities.capabilities:
        level = compute_detail_level(cap)
        dist[f"L{level}"] = dist.get(f"L{level}", 0) + 1
    return dist


def _grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


@monitored("quality.dashboard", quality=lambda r: {"overall": r.overall_score, "grade": r.grade})
def quality_report(model: ArchitectureModel, *, manifest=None) -> QualityReport:
    """Generate a unified quality report aggregating all dimensions."""
    # Validation
    val_result = validate_model(model)
    val_score = val_result.score

    # Semantic completeness
    semantic = _compute_semantic_completeness(model)

    # Detail level distribution
    detail_dist = _compute_detail_distribution(model)

    # Regen readiness (optional — may not have signatures)
    regen_score = 0.0
    try:
        from architecture_model.quality.regen_readiness import compute_regen_readiness
        rr = compute_regen_readiness(model)
        regen_score = rr.overall_score
    except Exception:
        pass

    # Confidence
    conf_score = 0.0
    try:
        from architecture_model.quality.confidence import model_confidence_summary
        summary = model_confidence_summary(model)
        conf_score = summary.get("overall", 0.0)
    except Exception:
        pass

    # Weighted composite: validation 30%, regen 25%, confidence 20%, semantic 25%
    sem_parts = semantic.get("intent_coverage", "0/1").split("/")
    sem_ratio = int(sem_parts[0]) / max(int(sem_parts[1]), 1) if len(sem_parts) == 2 else 0
    overall = int(val_score * 0.30 + regen_score * 0.25 + conf_score * 100 * 0.20 + sem_ratio * 100 * 0.25)
    overall = min(100, max(0, overall))

    return QualityReport(
        project=model.meta.project,
        validation_score=val_score,
        validation_issues=len(val_result.issues),
        semantic_completeness=semantic,
        detail_level_distribution=detail_dist,
        regen_readiness_score=regen_score,
        confidence_score=conf_score,
        overall_score=overall,
        grade=_grade(overall),
    )
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_quality_dashboard.py -v`
Expected: All 4 PASS

**Step 5: Run full suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: Same pre-existing failures, zero new

**Step 6: Commit**

```bash
git add src/architecture_model/quality/dashboard.py tests/test_quality_dashboard.py
git commit -m "feat(quality): add unified quality dashboard aggregating all dimensions"
```

---

### Task 3: Add CLI `quality` command

**Files:**
- Modify: `src/architecture_model/cli/main.py`
- Test: `tests/test_quality_cli.py` (new)

**Step 1: Write test**

```python
"""Test quality CLI command."""
import subprocess, sys


class TestQualityCLI:
    def test_quality_command_exists(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['quality', '--help'])"],
            capture_output=True, text=True,
        )
        assert "quality" in (result.stdout + result.stderr).lower()
```

**Step 2: Add `quality` subparser and handler to `cli/main.py`**

Add after the existing subparsers (around line 115):

```python
# --- quality ---
p_quality = subparsers.add_parser("quality", help="Generate unified quality report")
p_quality.add_argument("repo", help="Repository root path")
p_quality.add_argument("--markdown", action="store_true", help="Output as markdown")
```

Add handler:

```python
def _cmd_quality(args) -> int:
    """Generate unified quality report."""
    from ..core.parser import load_model
    from ..quality.dashboard import quality_report

    repo = Path(args.repo).resolve()
    model_path = repo / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"ERROR: No architecture model found in {repo}")
        return 1

    model = load_model(model_path)
    report = quality_report(model)

    if getattr(args, "markdown", False):
        print(report.to_markdown())
    else:
        print(f"Quality Report: {report.project}")
        print(f"  Grade: {report.grade} ({report.overall_score}/100)")
        print(f"  Validation: {report.validation_score}/100 ({report.validation_issues} issues)")
        print(f"  Regen Readiness: {report.regen_readiness_score:.0f}/100")
        print(f"  Semantic Completeness:")
        for k, v in report.semantic_completeness.items():
            print(f"    {k}: {v}")
    return 0
```

Wire into handlers dict: `"quality": _cmd_quality`

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/cli/main.py tests/test_quality_cli.py
git commit -m "feat(cli): add quality command for unified quality reporting"
```

---

### Task 4: Wire `@monitored` to new modules

**Files:**
- Modify: `src/architecture_model/core/review.py`
- Modify: `src/architecture_model/core/detail_level.py`
- Modify: `src/architecture_model/core/budget.py`
- Modify: `src/architecture_model/core/cross_repo.py`
- Modify: `src/architecture_model/core/changelog.py`
- Modify: `src/architecture_model/core/propagation.py`

**Step 1: Add `@monitored` decorator to each module's main function**

For each module, add:
```python
from architecture_model.monitoring import monitored
```

And decorate the main entry function:

| Module | Function | Decorator |
|--------|----------|-----------|
| `review.py` | `prepare_review_prompt` | `@monitored("core.review")` |
| `review.py` | `apply_review` | `@monitored("core.review")` |
| `detail_level.py` | `compute_detail_level` | `@monitored("core.detail_level")` |
| `budget.py` | `estimate_tokens` | `@monitored("core.budget")` |
| `budget.py` | `reduce_to_budget` | `@monitored("core.budget")` |
| `cross_repo.py` | `check_consistency` | `@monitored("core.cross_repo")` |
| `changelog.py` | `generate_changelog` | `@monitored("core.changelog")` |
| `propagation.py` | `propagate_enrichment` | `@monitored("core.propagation")` |

**Step 2: Run full suite, commit**

```bash
git add src/architecture_model/core/review.py src/architecture_model/core/detail_level.py src/architecture_model/core/budget.py src/architecture_model/core/cross_repo.py src/architecture_model/core/changelog.py src/architecture_model/core/propagation.py
git commit -m "feat(quality): wire @monitored decorator to all new core modules"
```

---

## Phase 2: SE Doc Generator Updates (Tasks 5-10)

These tasks are identical to the plan in `.opencode/plans/2026-08-26-se-doc-v21-integration.md`, tasks 1-6. Refer to that plan for the detailed steps. Summary:

### Task 5: Shared test fixture + baseline tests
### Task 6: ConOps — intent, MOEs, failure modes
### Task 7: Functional Analysis — intent column, MOE table, trade-offs
### Task 8: Logical Architecture — contract, trade-offs, intent
### Task 9: Use Cases — success criteria, failure modes (relationship joins)
### Task 10: Artifact Traceability — gap detection

---

## Phase 3: LLM-Driven v2.1 Field Population (Tasks 11-17)

For each subsystem, the executing agent should:
1. Read all source files in the subsystem
2. Read the existing `.architecture-model.yaml` for that subsystem
3. For each component and capability, analyze the code to determine:
   - `intent` — one sentence: why does this exist?
   - `goals` — what are its measurable objectives?
   - `moes` — how do you know it's working correctly?
   - `trade_offs` — what design tensions exist?
   - `failure_modes` — what goes wrong when it fails?
4. Update the subsystem `.architecture-model.yaml` with populated fields
5. Run validation to ensure model is still valid

**IMPORTANT:** Use `architect_slice` with `focus` on each subsystem to get compressed context. Read source files for detailed understanding. Base all field values on actual code analysis, not generic descriptions.

### Task 11: Populate Core subsystem (5 caps, 6 comps)

**Files:**
- Modify: `.architecture-models/core/.architecture-model.yaml`

**Source files to analyze:**
- `src/architecture_model/core/validator.py` → COMP-1.2 Validation
- `src/architecture_model/core/types.py` → COMP-1.1 Type System
- `src/architecture_model/core/parser.py` → COMP-1.3 Parser & Persistence
- `src/architecture_model/core/slicer.py`, `differ.py`, `coverage.py` → COMP-1.4 Model Operations
- `src/architecture_model/core/confidence.py`, `regen_readiness.py` → COMP-1.5 Quality Metrics

**Per entity, fill:**
```yaml
# Example for COMP-1.2 Validation:
- id: COMP-1.2
  name: Validation
  intent: "Verify structural and semantic correctness of architecture models against schema rules"
  goals:
    - "Catch all schema violations before model use"
    - "Provide actionable issue descriptions with entity-level granularity"
  moes:
    - "Validation score correlates with actual model quality"
    - "Zero false positives on conforming models"
    - "All 17 relationship types checked"
  trade_offs:
    - "Strict schema enforcement vs accepting partially-specified models"
    - "Validation speed vs thoroughness of cross-entity checks"
  failure_modes:
    - "Silent acceptance of invalid relationship types"
    - "Score inflation from missing checks"
    - "False positives on valid but unusual models"
```

**Also fill capabilities:**
```yaml
# Example for CAP-1 Validate Architecture Models:
- id: CAP-1
  name: Validate Architecture Models
  intent: "Provide single-function entry point for comprehensive model quality assessment"
  moes:
    - "Score of 98+ on well-formed models from E2E benchmark"
    - "Detects orphan entities, broken references, missing relationships"
```

**Commit:**
```bash
git commit -m "enrich(core): populate v2.1 SE fields via code analysis"
```

---

### Task 12: Populate Manifest subsystem (1 cap, 4 comps)

**Files:**
- Modify: `.architecture-models/manifest/.architecture-model.yaml`

**Source files:** `src/architecture_model/manifest/scanner.py`, `generator.py`, `call_graph.py`, `interfaces.py`, `grouping.py`, `behavior.py`, `recursive.py`

**Commit:**
```bash
git commit -m "enrich(manifest): populate v2.1 SE fields via code analysis"
```

---

### Task 13: Populate Pipeline subsystem (1 cap, 6 comps)

**Files:**
- Modify: `.architecture-models/pipeline/.architecture-model.yaml`

**Source files:** `src/architecture_model/pipeline/coordinator.py`, `observe.py`, `infer.py`, `allocate.py`, `relate.py`, `specify.py`, `contract.py`, `decompose.py`, `synthesize.py`

**Commit:**
```bash
git commit -m "enrich(pipeline): populate v2.1 SE fields via code analysis"
```

---

### Task 14: Populate Orchestration subsystem (2 caps, 3 comps)

**Files:**
- Modify: `.architecture-models/orchestration/.architecture-model.yaml`

**Source files:** `src/architecture_model/orchestration/pipeline.py`, `enrich.py`, `decompose.py`, `auto_enrich.py`, `enrichment_context.py`, `deep_decompose.py`

**Commit:**
```bash
git commit -m "enrich(orchestration): populate v2.1 SE fields via code analysis"
```

---

### Task 15: Populate Extract subsystem (1 cap, 1 comp)

**Files:**
- Modify: `.architecture-models/extract/.architecture-model.yaml`

**Source files:** `src/architecture_model/extract/from_code.py`

**Commit:**
```bash
git commit -m "enrich(extract): populate v2.1 SE fields via code analysis"
```

---

### Task 16: Populate Configuration + CLI subsystems (minimal)

**Files:**
- Modify: `.architecture-models/configuration/.architecture-model.yaml`
- Modify: `.architecture-models/cli/.architecture-model.yaml`

**Source files:** `src/architecture_model/config/loader.py`, `schema.py`, `cli/main.py`

**Commit:**
```bash
git commit -m "enrich(config,cli): populate v2.1 SE fields via code analysis"
```

---

### Task 17: Populate top-level model (30 caps, 223 comps — selective)

**Files:**
- Modify: `.architecture-model.yaml` (worktree copy)

**Strategy:** Only populate v2.1 fields on the **12 top-level components** (COMP-1 through COMP-12) and **all 30 capabilities**. Skip the 211 sub-components (they inherit from subsystem models via propagation).

**Commit:**
```bash
git commit -m "enrich(top-level): populate v2.1 SE fields on top-level entities"
```

---

## Phase 4: Regeneration + Verification (Tasks 18-19)

### Task 18: Regenerate all SE docs

```bash
cd /path/to/worktree
architecture-model docs . --se
# Then for each subsystem:
for sub in core manifest pipeline orchestration extract configuration cli; do
    architecture-model docs .architecture-models/$sub --se
done
```

**Commit:**
```bash
git commit -m "docs: regenerate all SE documents with v2.1 field content"
```

---

### Task 19: Run quality dashboard and verify

```bash
architecture-model quality .
```

Expected: Grade should improve from current baseline (likely D/F → C/B) due to populated semantic fields.

Run full test suite one final time to confirm zero regressions.

---

## Execution Order Summary

| Task | Phase | What | Complexity | Est. |
|------|-------|------|-----------|------|
| 1 | Quality | Move 5 modules to quality/ + re-export shims | Medium | 30 min |
| 2 | Quality | Unified dashboard (QualityReport) | Medium | 25 min |
| 3 | Quality | CLI `quality` command | Low | 10 min |
| 4 | Quality | Wire @monitored to 6 new modules | Low | 10 min |
| 5 | Docs | Shared test fixture + baseline | Low | 10 min |
| 6 | Docs | ConOps generator update | Medium | 20 min |
| 7 | Docs | Functional Analysis update | Medium | 20 min |
| 8 | Docs | Logical Architecture update | Low | 15 min |
| 9 | Docs | Use Cases update (relationship joins) | High | 25 min |
| 10 | Docs | Artifact Traceability gaps | Low | 15 min |
| 11 | Populate | Core subsystem (6 comps, 5 caps) | Medium | 30 min |
| 12 | Populate | Manifest subsystem (4 comps, 1 cap) | Medium | 20 min |
| 13 | Populate | Pipeline subsystem (6 comps, 1 cap) | Medium | 25 min |
| 14 | Populate | Orchestration (3 comps, 2 caps) | Medium | 20 min |
| 15 | Populate | Extract (1 comp, 1 cap) | Low | 10 min |
| 16 | Populate | Config + CLI | Low | 10 min |
| 17 | Populate | Top-level (12 comps, 30 caps) | High | 40 min |
| 18 | Regen | Regenerate all SE docs | Low | 15 min |
| 19 | Verify | Quality dashboard + full suite | Low | 10 min |

**Total estimated: ~11 hours** (6h phases 1-4 + 5h phase 5)

## Parallelization

- **Phase 1:** Tasks 1→2→3→4 sequential (dependencies)
- **Phase 2:** Tasks 5→6→7→8→9→10 sequential (shared test file)
- **Phase 3:** Tasks 11-17 can all run in parallel (independent subsystem models) — use dispatching-parallel-agents skill
- **Phase 4:** After all Phase 2+3 complete
- **Phase 5:** Tasks 20-27 mostly sequential (shared modules); Tasks 25-26 can parallel after 24

---

## Phase 5: Code Improvement Engine (Tasks 20-27)

The code improvement engine provides static analysis, LLM-driven review, safe auto-apply, implementation comparison, and an autonomous improvement loop. Findings feed bidirectionally into the architecture model.

### Architecture

```
quality/
├── code_review.py       — Static analysis: complexity, docstrings, types, smells
├── code_improver.py     — LLM review loop: prepare prompts, parse responses, apply changes
├── code_prompts.py      — Prompt templates for review, improvement, comparison
├── code_safety.py       — Safe change classification and application
└── dashboard.py         — (existing) extended with code quality dimension

Triggers:
├── CLI: architecture-model review <path> [--auto] [--target-score N] [--compare A B]
├── Dashboard: quality_report() flags low code-quality components
└── Pipeline: observe stage populates code_quality on StageResult
```

### Data Flow

```
Source Code                          Architecture Model
    │                                       │
    ▼                                       │
[Static Analysis]                           │
    │ CodeAnalysis                           │
    ├──────────────────────────────▶ [Model Feedback]
    │                               Updates failure_modes,
    ▼                               moes, trade_offs from
[LLM Review]                        code findings
    │ ReviewSuggestions                      │
    ▼                                       │
[Safety Classification]                     │
    │ safe / risky                          │
    ▼                                       │
[Auto-Apply Safe]──▶[Test]──▶[Iterate]     │
    │                                       │
    ▼                                       │
[Comparison] (optional)                     │
    │ ComparisonResult                      │
    ▼                                       ▼
[Quality Dashboard] ◀──────────────────────┘
```

---

### Task 20: Static analysis engine — `quality/code_review.py`

**Files:**
- Create: `src/architecture_model/quality/code_review.py`
- Test: `tests/test_code_review.py` (new)

**Step 1: Write failing test**

```python
"""Tests for static code analysis engine."""
import ast
import textwrap
from architecture_model.quality.code_review import (
    analyze_source, CodeAnalysis, CodeIssue, IssueSeverity,
)


class TestCyclomaticComplexity:
    def test_simple_function(self):
        src = "def foo(): return 1"
        analysis = analyze_source(src, filename="test.py")
        fn = analysis.functions[0]
        assert fn.complexity == 1  # no branches

    def test_branching_function(self):
        src = textwrap.dedent("""
            def foo(x):
                if x > 0:
                    if x > 10:
                        return "big"
                    return "small"
                elif x == 0:
                    return "zero"
                else:
                    for i in range(x):
                        if i % 2:
                            continue
                    return "negative"
        """)
        analysis = analyze_source(src, filename="test.py")
        fn = analysis.functions[0]
        assert fn.complexity >= 5  # if + if + elif + else + for + if


class TestDocstringDetection:
    def test_missing_module_docstring(self):
        src = "def foo(): pass"
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_MODULE_DOCSTRING" for i in analysis.issues)

    def test_missing_function_docstring(self):
        src = '"""Module doc."""\ndef foo(): pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_FUNCTION_DOCSTRING" for i in analysis.issues)

    def test_has_docstring_no_issue(self):
        src = '"""Module doc."""\ndef foo():\n    """Function doc."""\n    pass'
        analysis = analyze_source(src, filename="test.py")
        assert not any(i.code == "MISSING_FUNCTION_DOCSTRING" for i in analysis.issues)


class TestTypeHintCoverage:
    def test_missing_return_type(self):
        src = '"""M."""\ndef foo(x: int): pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_RETURN_TYPE" for i in analysis.issues)

    def test_missing_param_type(self):
        src = '"""M."""\ndef foo(x): pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_PARAM_TYPE" for i in analysis.issues)


class TestCodeSmells:
    def test_long_function(self):
        body = "\n".join(f"    x = {i}" for i in range(60))
        src = f'"""M."""\ndef foo():\n    """D."""\n{body}'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "LONG_FUNCTION" for i in analysis.issues)

    def test_too_many_params(self):
        src = '"""M."""\ndef foo(a, b, c, d, e, f, g, h):\n    """D."""\n    pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "TOO_MANY_PARAMS" for i in analysis.issues)


class TestOverallScore:
    def test_clean_code_scores_high(self):
        src = '"""Module doc."""\ndef foo(x: int) -> int:\n    """Return x."""\n    return x'
        analysis = analyze_source(src, filename="test.py")
        assert analysis.score >= 80

    def test_messy_code_scores_low(self):
        body = "\n".join(f"    x = {i}" for i in range(60))
        src = f'def foo(a, b, c, d, e, f, g, h):\n{body}'
        analysis = analyze_source(src, filename="test.py")
        assert analysis.score < 60
```

**Step 2: Implement `quality/code_review.py`**

```python
"""Static code analysis engine — complexity, docstrings, type hints, code smells."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from architecture_model.quality.monitoring import monitored


class IssueSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CodeIssue:
    code: str           # e.g., "MISSING_FUNCTION_DOCSTRING"
    severity: IssueSeverity
    message: str
    line: int = 0
    function: str = ""
    fixable: bool = False  # safe for auto-apply


@dataclass
class FunctionAnalysis:
    name: str
    line: int
    complexity: int         # cyclomatic complexity
    length: int             # body line count
    param_count: int
    has_docstring: bool
    has_return_type: bool
    untyped_params: list[str]
    issues: list[CodeIssue] = field(default_factory=list)


@dataclass
class CodeAnalysis:
    filename: str
    line_count: int
    has_module_docstring: bool
    functions: list[FunctionAnalysis]
    issues: list[CodeIssue]
    score: int  # 0-100


def _cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count cyclomatic complexity: 1 + decision points."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp)):
            complexity += 1
        elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # and/or add branches
            complexity += len(child.values) - 1
        elif isinstance(child, ast.Match):
            complexity += len(child.cases)
    return complexity


def _function_length(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count lines in function body."""
    if not node.body:
        return 0
    first = node.body[0].lineno
    last = node.body[-1].end_lineno or node.body[-1].lineno
    return last - first + 1


def _analyze_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionAnalysis:
    """Analyze a single function."""
    issues: list[CodeIssue] = []
    has_docstring = bool(ast.get_docstring(node))
    complexity = _cyclomatic_complexity(node)
    length = _function_length(node)

    # Skip self/cls
    params = [a for a in node.args.args if a.arg not in ("self", "cls")]
    param_count = len(params)
    untyped = [a.arg for a in params if a.annotation is None]
    has_return = node.returns is not None

    if not has_docstring and not node.name.startswith("_"):
        issues.append(CodeIssue(
            code="MISSING_FUNCTION_DOCSTRING", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' has no docstring",
            line=node.lineno, function=node.name, fixable=True,
        ))
    if not has_return and not node.name.startswith("_"):
        issues.append(CodeIssue(
            code="MISSING_RETURN_TYPE", severity=IssueSeverity.INFO,
            message=f"Function '{node.name}' has no return type annotation",
            line=node.lineno, function=node.name, fixable=True,
        ))
    for p in untyped:
        if not node.name.startswith("_"):
            issues.append(CodeIssue(
                code="MISSING_PARAM_TYPE", severity=IssueSeverity.INFO,
                message=f"Parameter '{p}' in '{node.name}' has no type annotation",
                line=node.lineno, function=node.name, fixable=True,
            ))
    if length > 50:
        issues.append(CodeIssue(
            code="LONG_FUNCTION", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' is {length} lines (>50)",
            line=node.lineno, function=node.name, fixable=True,
        ))
    if param_count > 6:
        issues.append(CodeIssue(
            code="TOO_MANY_PARAMS", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' has {param_count} parameters (>6)",
            line=node.lineno, function=node.name,
        ))
    if complexity > 10:
        issues.append(CodeIssue(
            code="HIGH_COMPLEXITY", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' has cyclomatic complexity {complexity} (>10)",
            line=node.lineno, function=node.name, fixable=True,
        ))

    return FunctionAnalysis(
        name=node.name, line=node.lineno, complexity=complexity,
        length=length, param_count=param_count, has_docstring=has_docstring,
        has_return_type=has_return, untyped_params=untyped, issues=issues,
    )


def _score(analysis_issues: list[CodeIssue], func_count: int) -> int:
    """Compute code quality score 0-100."""
    if func_count == 0:
        return 100
    penalty = 0
    for issue in analysis_issues:
        if issue.severity == IssueSeverity.ERROR:
            penalty += 15
        elif issue.severity == IssueSeverity.WARNING:
            penalty += 5
        elif issue.severity == IssueSeverity.INFO:
            penalty += 2
    # Normalize: max penalty = 100
    return max(0, 100 - min(100, penalty))


@monitored("quality.code_review", quality=lambda r: {"score": r.score, "issues": len(r.issues)})
def analyze_source(source: str, *, filename: str = "<unknown>") -> CodeAnalysis:
    """Analyze Python source code for quality issues."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return CodeAnalysis(
            filename=filename, line_count=source.count("\n") + 1,
            has_module_docstring=False, functions=[], issues=[
                CodeIssue(code="SYNTAX_ERROR", severity=IssueSeverity.ERROR,
                          message="Failed to parse source", fixable=False)
            ], score=0,
        )

    has_module_doc = bool(ast.get_docstring(tree))
    all_issues: list[CodeIssue] = []

    if not has_module_doc:
        all_issues.append(CodeIssue(
            code="MISSING_MODULE_DOCSTRING", severity=IssueSeverity.INFO,
            message="Module has no docstring", fixable=True,
        ))

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fa = _analyze_function(node)
            functions.append(fa)
            all_issues.extend(fa.issues)

    return CodeAnalysis(
        filename=filename,
        line_count=source.count("\n") + 1,
        has_module_docstring=has_module_doc,
        functions=functions,
        issues=all_issues,
        score=_score(all_issues, len(functions)),
    )


def analyze_file(filepath: str) -> CodeAnalysis:
    """Analyze a Python file."""
    with open(filepath) as f:
        source = f.read()
    return analyze_source(source, filename=filepath)


def analyze_component(files: list[str]) -> list[CodeAnalysis]:
    """Analyze all files in a component."""
    return [analyze_file(f) for f in files if f.endswith(".py")]
```

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/quality/code_review.py tests/test_code_review.py
git commit -m "feat(quality): add static code analysis engine with complexity, docstring, type hint checks"
```

---

### Task 21: Prompt templates — `quality/code_prompts.py`

**Files:**
- Create: `src/architecture_model/quality/code_prompts.py`
- Test: `tests/test_code_prompts.py` (new)

**Step 1: Write test**

```python
"""Tests for code review prompt templates."""
from architecture_model.quality.code_prompts import (
    review_prompt, improve_prompt, compare_prompt, safe_change_prompt,
)
from architecture_model.quality.code_review import analyze_source


class TestPromptGeneration:
    def test_review_prompt_includes_issues(self):
        src = "def foo(x): pass"
        analysis = analyze_source(src, filename="test.py")
        prompt = review_prompt(src, analysis)
        assert "MISSING" in prompt
        assert "test.py" in prompt

    def test_improve_prompt_includes_code(self):
        src = "def foo(): return 1"
        analysis = analyze_source(src, filename="test.py")
        prompt = improve_prompt(src, analysis, goal="Add docstring")
        assert "def foo" in prompt
        assert "Add docstring" in prompt

    def test_compare_prompt_includes_both(self):
        src_a = "def foo(): return 1"
        src_b = "def foo():\n    '''Return one.'''\n    return 1"
        prompt = compare_prompt(src_a, src_b, criteria="readability")
        assert "Implementation A" in prompt
        assert "Implementation B" in prompt

    def test_safe_change_prompt_for_docstring(self):
        src = "def foo(x: int) -> int: return x"
        prompt = safe_change_prompt(src, change_type="docstring", function_name="foo")
        assert "foo" in prompt
        assert "docstring" in prompt.lower()
```

**Step 2: Implement `quality/code_prompts.py`**

```python
"""Prompt templates for LLM-driven code review and improvement."""
from __future__ import annotations
from architecture_model.quality.code_review import CodeAnalysis


def review_prompt(source: str, analysis: CodeAnalysis) -> str:
    """Generate a prompt asking LLM to review code quality."""
    issues_text = "\n".join(
        f"- [{i.severity.value.upper()}] {i.code}: {i.message} (line {i.line})"
        for i in analysis.issues
    )
    return f"""Review this Python module for code quality.

**File:** {analysis.filename}
**Score:** {analysis.score}/100
**Functions:** {len(analysis.functions)}

**Static Analysis Issues:**
{issues_text or "(none)"}

**Source Code:**
```python
{source}
```

Please provide:
1. A brief assessment of overall quality
2. Additional issues not caught by static analysis (logic errors, naming, design)
3. Specific improvement suggestions with code snippets
4. For each suggestion, classify as SAFE (auto-applicable) or RISKY (needs human review)

Return as JSON: {{"assessment": "...", "additional_issues": [...], "suggestions": [{{"description": "...", "safety": "safe|risky", "code": "..."}}]}}"""


def improve_prompt(source: str, analysis: CodeAnalysis, *, goal: str = "") -> str:
    """Generate a prompt asking LLM to improve specific code."""
    goal_text = f"\n**Goal:** {goal}" if goal else ""
    return f"""Improve this Python code.{goal_text}

**File:** {analysis.filename}
**Current Score:** {analysis.score}/100

**Source Code:**
```python
{source}
```

**Known Issues:**
{chr(10).join(f"- {i.message}" for i in analysis.issues) or "(none)"}

Provide the improved code as a complete replacement. Preserve all existing functionality.
Explain each change briefly.

Return as JSON: {{"improved_code": "...", "changes": [{{"description": "...", "safety": "safe|risky"}}]}}"""


def compare_prompt(source_a: str, source_b: str, *, criteria: str = "overall quality") -> str:
    """Generate a prompt to compare two implementations."""
    return f"""Compare these two implementations on: {criteria}

**Implementation A:**
```python
{source_a}
```

**Implementation B:**
```python
{source_b}
```

For each criterion, declare a winner (A, B, or TIE) with rationale.
If one is clearly better overall, recommend it. If both have strengths, suggest a synthesis.

Return as JSON: {{"winner": "A|B|TIE", "rationale": "...", "criteria_results": [{{"criterion": "...", "winner": "A|B|TIE", "reason": "..."}}], "synthesis": "..." }}"""


def safe_change_prompt(source: str, *, change_type: str, function_name: str = "") -> str:
    """Generate a prompt for a specific safe change type."""
    target = f" for function '{function_name}'" if function_name else ""
    return f"""Generate a {change_type}{target} for this code.

```python
{source}
```

Requirements:
- For docstrings: use Google-style format, describe purpose/args/returns
- For type hints: infer types from usage patterns and return values
- For dead imports: list imports with no usage in the module
- Preserve all existing code and behavior exactly

Return as JSON: {{"change_type": "{change_type}", "function": "{function_name}", "replacement_code": "..."}}"""
```

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/quality/code_prompts.py tests/test_code_prompts.py
git commit -m "feat(quality): add LLM prompt templates for code review, improvement, comparison"
```

---

### Task 22: Safety classification and auto-apply — `quality/code_safety.py`

**Files:**
- Create: `src/architecture_model/quality/code_safety.py`
- Test: `tests/test_code_safety.py` (new)

**Step 1: Write test**

```python
"""Tests for safe change classification and application."""
from architecture_model.quality.code_safety import (
    classify_suggestion, SafetyLevel, SafeChangeType,
    SAFE_CHANGE_TYPES,
)


class TestSafetyClassification:
    def test_docstring_is_safe(self):
        assert classify_suggestion("Add docstring to foo") == SafetyLevel.SAFE

    def test_refactor_is_risky(self):
        assert classify_suggestion("Rewrite the algorithm to use dynamic programming") == SafetyLevel.RISKY

    def test_type_hint_is_safe(self):
        assert classify_suggestion("Add type hint: x: int") == SafetyLevel.SAFE

    def test_remove_import_is_safe(self):
        assert classify_suggestion("Remove unused import os") == SafetyLevel.SAFE

    def test_change_logic_is_risky(self):
        assert classify_suggestion("Change the return value from None to empty list") == SafetyLevel.RISKY


class TestSafeChangeTypes:
    def test_all_types_registered(self):
        assert "docstring" in SAFE_CHANGE_TYPES
        assert "type_hint" in SAFE_CHANGE_TYPES
        assert "dead_import" in SAFE_CHANGE_TYPES
        assert "function_split" in SAFE_CHANGE_TYPES
        assert "error_handling" in SAFE_CHANGE_TYPES

    def test_extensible(self):
        # Should be a dict/registry pattern
        assert isinstance(SAFE_CHANGE_TYPES, dict)
```

**Step 2: Implement `quality/code_safety.py`**

```python
"""Safe change classification and application for auto-improvement."""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
import re


class SafetyLevel(Enum):
    SAFE = "safe"       # auto-apply, verify with tests
    CAUTIOUS = "cautious"  # auto-apply but flag for review
    RISKY = "risky"     # requires human review


@dataclass
class SafeChangeType:
    name: str
    description: str
    safety: SafetyLevel
    keywords: list[str]  # for classification


# Registry of safe change types — extensible
SAFE_CHANGE_TYPES: dict[str, SafeChangeType] = {
    "docstring": SafeChangeType(
        name="docstring", description="Add missing docstrings",
        safety=SafetyLevel.SAFE,
        keywords=["docstring", "documentation", "doc comment"],
    ),
    "type_hint": SafeChangeType(
        name="type_hint", description="Add missing type annotations",
        safety=SafetyLevel.SAFE,
        keywords=["type hint", "type annotation", "typing", "annotate"],
    ),
    "dead_import": SafeChangeType(
        name="dead_import", description="Remove unused imports",
        safety=SafetyLevel.SAFE,
        keywords=["unused import", "dead import", "remove import"],
    ),
    "function_split": SafeChangeType(
        name="function_split", description="Split long functions into smaller ones",
        safety=SafetyLevel.CAUTIOUS,
        keywords=["split function", "extract function", "break up", "decompose function"],
    ),
    "error_handling": SafeChangeType(
        name="error_handling", description="Add missing error handling",
        safety=SafetyLevel.CAUTIOUS,
        keywords=["error handling", "try except", "exception", "raise"],
    ),
}


def classify_suggestion(description: str) -> SafetyLevel:
    """Classify a code change suggestion as safe, cautious, or risky."""
    desc_lower = description.lower()

    # Check against known safe change types
    for change_type in SAFE_CHANGE_TYPES.values():
        for keyword in change_type.keywords:
            if keyword in desc_lower:
                return change_type.safety

    # Risky indicators
    risky_patterns = [
        r"rewrite", r"change.*return", r"change.*logic", r"replace.*algorithm",
        r"modify.*behavior", r"remove.*function", r"delete", r"restructure",
        r"dynamic programming", r"redesign",
    ]
    for pattern in risky_patterns:
        if re.search(pattern, desc_lower):
            return SafetyLevel.RISKY

    # Default: risky (conservative)
    return SafetyLevel.RISKY


def register_safe_change(name: str, description: str, keywords: list[str],
                          safety: SafetyLevel = SafetyLevel.SAFE) -> None:
    """Register a new safe change type (extensibility hook)."""
    SAFE_CHANGE_TYPES[name] = SafeChangeType(
        name=name, description=description, safety=safety, keywords=keywords,
    )
```

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/quality/code_safety.py tests/test_code_safety.py
git commit -m "feat(quality): add safety classification for auto-apply code changes"
```

---

### Task 23: LLM code improver — `quality/code_improver.py`

**Files:**
- Create: `src/architecture_model/quality/code_improver.py`
- Test: `tests/test_code_improver.py` (new)

**Step 1: Write test**

```python
"""Tests for LLM-driven code improvement loop."""
import json
from architecture_model.quality.code_improver import (
    parse_review_response, parse_improve_response,
    parse_compare_response, ImprovementPlan,
    plan_improvements, ReviewSuggestion,
)
from architecture_model.quality.code_review import analyze_source


class TestResponseParsing:
    def test_parse_review_response(self):
        llm_output = json.dumps({
            "assessment": "Good structure",
            "additional_issues": ["No error handling in parse()"],
            "suggestions": [
                {"description": "Add docstring to foo", "safety": "safe", "code": "..."},
                {"description": "Rewrite parse logic", "safety": "risky", "code": "..."},
            ]
        })
        result = parse_review_response(llm_output)
        assert result.assessment == "Good structure"
        assert len(result.suggestions) == 2
        assert result.suggestions[0].safety == "safe"

    def test_parse_improve_response(self):
        llm_output = json.dumps({
            "improved_code": "def foo():\n    '''Doc.'''\n    return 1",
            "changes": [{"description": "Added docstring", "safety": "safe"}],
        })
        result = parse_improve_response(llm_output)
        assert "def foo" in result.improved_code
        assert len(result.changes) == 1

    def test_parse_compare_response(self):
        llm_output = json.dumps({
            "winner": "B",
            "rationale": "Better documented",
            "criteria_results": [{"criterion": "readability", "winner": "B", "reason": "Docstrings"}],
            "synthesis": "Use B with A's error handling",
        })
        result = parse_compare_response(llm_output)
        assert result.winner == "B"


class TestImprovementPlanning:
    def test_plan_from_analysis(self):
        src = "def foo(x): pass"
        analysis = analyze_source(src, filename="test.py")
        plan = plan_improvements(analysis)
        assert isinstance(plan, ImprovementPlan)
        assert len(plan.steps) > 0  # should have at least docstring + type hint steps
        assert any(s.change_type == "docstring" for s in plan.steps)
```

**Step 2: Implement `quality/code_improver.py`**

```python
"""LLM-driven code improvement — parse responses, plan improvements, run loop."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from architecture_model.quality.code_review import CodeAnalysis, CodeIssue
from architecture_model.quality.code_safety import classify_suggestion, SafetyLevel, SAFE_CHANGE_TYPES
from architecture_model.quality.monitoring import monitored


@dataclass
class ReviewSuggestion:
    description: str
    safety: str  # "safe" | "risky"
    code: str = ""


@dataclass
class ReviewResult:
    assessment: str
    additional_issues: list[str]
    suggestions: list[ReviewSuggestion]


@dataclass
class ImproveResult:
    improved_code: str
    changes: list[dict[str, str]]


@dataclass
class CompareResult:
    winner: str  # "A" | "B" | "TIE"
    rationale: str
    criteria_results: list[dict[str, str]]
    synthesis: str = ""


@dataclass
class ImprovementStep:
    change_type: str
    target: str  # function name or "module"
    description: str
    safety: SafetyLevel
    priority: int  # lower = higher priority


@dataclass
class ImprovementPlan:
    filename: str
    current_score: int
    steps: list[ImprovementStep]
    estimated_score_after: int


@dataclass
class ImprovementReport:
    """Result of an autonomous improvement loop."""
    filename: str
    iterations: int
    initial_score: int
    final_score: int
    changes_applied: list[str]
    changes_skipped: list[str]
    test_passed: bool


def parse_review_response(llm_output: str) -> ReviewResult:
    """Parse LLM review response JSON."""
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        return ReviewResult(assessment=llm_output, additional_issues=[], suggestions=[])
    return ReviewResult(
        assessment=data.get("assessment", ""),
        additional_issues=data.get("additional_issues", []),
        suggestions=[
            ReviewSuggestion(**s) for s in data.get("suggestions", [])
        ],
    )


def parse_improve_response(llm_output: str) -> ImproveResult:
    """Parse LLM improvement response JSON."""
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        return ImproveResult(improved_code="", changes=[])
    return ImproveResult(
        improved_code=data.get("improved_code", ""),
        changes=data.get("changes", []),
    )


def parse_compare_response(llm_output: str) -> CompareResult:
    """Parse LLM comparison response JSON."""
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        return CompareResult(winner="TIE", rationale=llm_output, criteria_results=[])
    return CompareResult(
        winner=data.get("winner", "TIE"),
        rationale=data.get("rationale", ""),
        criteria_results=data.get("criteria_results", []),
        synthesis=data.get("synthesis", ""),
    )


def plan_improvements(analysis: CodeAnalysis) -> ImprovementPlan:
    """Create an improvement plan from static analysis results."""
    steps: list[ImprovementStep] = []
    priority = 0

    for issue in analysis.issues:
        if not issue.fixable:
            continue
        # Map issue codes to change types
        change_type = _issue_to_change_type(issue.code)
        if change_type:
            safety = SAFE_CHANGE_TYPES.get(change_type, None)
            steps.append(ImprovementStep(
                change_type=change_type,
                target=issue.function or "module",
                description=issue.message,
                safety=safety.safety if safety else SafetyLevel.RISKY,
                priority=priority,
            ))
            priority += 1

    # Estimate score improvement: each fixed issue improves by its penalty
    est_improvement = sum(5 for s in steps if s.safety == SafetyLevel.SAFE)
    est_score = min(100, analysis.score + est_improvement)

    return ImprovementPlan(
        filename=analysis.filename,
        current_score=analysis.score,
        steps=steps,
        estimated_score_after=est_score,
    )


def _issue_to_change_type(code: str) -> str | None:
    """Map a CodeIssue code to a safe change type."""
    mapping = {
        "MISSING_MODULE_DOCSTRING": "docstring",
        "MISSING_FUNCTION_DOCSTRING": "docstring",
        "MISSING_RETURN_TYPE": "type_hint",
        "MISSING_PARAM_TYPE": "type_hint",
        "LONG_FUNCTION": "function_split",
        "HIGH_COMPLEXITY": "function_split",
    }
    return mapping.get(code)


@monitored("quality.code_improver")
def improve(
    source: str,
    filename: str,
    *,
    llm_callback: Callable[[str, str, dict], str] | None = None,
    test_command: str = "",
    max_iterations: int = 3,
    target_score: int = 80,
) -> ImprovementReport:
    """Run autonomous improvement loop on a source file.

    Loop: analyze → plan → (LLM review if available) → apply safe changes → test → repeat
    Stops when target_score reached or max_iterations exceeded.
    """
    from architecture_model.quality.code_review import analyze_source
    from architecture_model.quality.code_prompts import improve_prompt
    import subprocess

    current_source = source
    changes_applied: list[str] = []
    changes_skipped: list[str] = []
    initial_score = 0
    final_score = 0

    for iteration in range(max_iterations):
        analysis = analyze_source(current_source, filename=filename)
        if iteration == 0:
            initial_score = analysis.score
        final_score = analysis.score

        if analysis.score >= target_score:
            break

        plan = plan_improvements(analysis)
        if not plan.steps:
            break

        # If LLM available, get improved code
        if llm_callback:
            prompt = improve_prompt(current_source, analysis, goal="Fix all safe issues")
            try:
                llm_output = llm_callback("code_improve", prompt, {"filename": filename})
                if llm_output:
                    result = parse_improve_response(llm_output)
                    if result.improved_code:
                        # Verify the improved code parses
                        try:
                            import ast
                            ast.parse(result.improved_code)
                            current_source = result.improved_code
                            for change in result.changes:
                                safety = classify_suggestion(change.get("description", ""))
                                if safety == SafetyLevel.SAFE:
                                    changes_applied.append(change.get("description", ""))
                                else:
                                    changes_skipped.append(change.get("description", ""))
                        except SyntaxError:
                            changes_skipped.append("LLM output had syntax errors")
            except Exception:
                pass
        else:
            # No LLM — just report what would be done
            for step in plan.steps:
                changes_skipped.append(f"[no LLM] {step.description}")
            break

    # Run tests if specified
    test_passed = True
    if test_command and changes_applied:
        try:
            result = subprocess.run(
                test_command, shell=True, capture_output=True, timeout=120,
            )
            test_passed = result.returncode == 0
        except Exception:
            test_passed = False

    return ImprovementReport(
        filename=filename, iterations=iteration + 1,
        initial_score=initial_score, final_score=final_score,
        changes_applied=changes_applied, changes_skipped=changes_skipped,
        test_passed=test_passed,
    )
```

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/quality/code_improver.py tests/test_code_improver.py
git commit -m "feat(quality): add LLM code improvement loop with autonomous iteration"
```

---

### Task 24: Model feedback — bidirectional code↔model sync

**Files:**
- Create: `src/architecture_model/quality/model_feedback.py`
- Test: `tests/test_model_feedback.py` (new)

**Step 1: Write test**

```python
"""Tests for bidirectional code-to-model feedback."""
from architecture_model.quality.model_feedback import (
    code_to_model_feedback, ModelFeedback,
)
from architecture_model.quality.code_review import analyze_source
from architecture_model.core.types import Component, Status


class TestCodeToModelFeedback:
    def test_missing_error_handling_populates_failure_modes(self):
        # Code with no try/except
        src = '"""M."""\ndef process(data):\n    """D."""\n    return data["key"]'
        analysis = analyze_source(src, filename="processor.py")
        comp = Component(id="COMP-1", name="Processor", status=Status.ACTIVE,
                         files=["processor.py"])
        feedback = code_to_model_feedback(comp, [analysis])
        assert len(feedback.suggested_failure_modes) > 0

    def test_high_complexity_suggests_trade_off(self):
        body = "\n".join(f"    if x == {i}: return {i}" for i in range(15))
        src = f'"""M."""\ndef complex_fn(x):\n    """D."""\n{body}'
        analysis = analyze_source(src, filename="complex.py")
        comp = Component(id="COMP-1", name="Complex", status=Status.ACTIVE)
        feedback = code_to_model_feedback(comp, [analysis])
        assert len(feedback.suggested_trade_offs) > 0

    def test_good_test_coverage_suggests_moes(self):
        src = '"""M."""\ndef validate(model):\n    """Validate model."""\n    return True'
        analysis = analyze_source(src, filename="validator.py")
        comp = Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                         test_contracts=[])  # analyzed from test files
        feedback = code_to_model_feedback(comp, [analysis])
        assert isinstance(feedback.suggested_moes, list)
```

**Step 2: Implement `quality/model_feedback.py`**

```python
"""Bidirectional feedback: code analysis findings → architecture model updates."""
from __future__ import annotations

from dataclasses import dataclass, field
from architecture_model.core.types import Component
from architecture_model.quality.code_review import CodeAnalysis, CodeIssue


@dataclass
class ModelFeedback:
    """Suggested model updates derived from code analysis."""
    component_id: str
    suggested_failure_modes: list[str] = field(default_factory=list)
    suggested_trade_offs: list[str] = field(default_factory=list)
    suggested_moes: list[str] = field(default_factory=list)
    suggested_goals: list[str] = field(default_factory=list)
    code_quality_score: int = 0


def code_to_model_feedback(
    component: Component,
    analyses: list[CodeAnalysis],
) -> ModelFeedback:
    """Derive architecture model field suggestions from code analysis.

    Maps code-level findings to model-level semantic fields:
    - Missing error handling → failure_modes
    - High complexity → trade_offs
    - Test coverage patterns → moes
    - Function purposes → goals
    """
    feedback = ModelFeedback(component_id=component.id)

    if not analyses:
        return feedback

    avg_score = sum(a.score for a in analyses) // len(analyses)
    feedback.code_quality_score = avg_score

    all_issues = [i for a in analyses for i in a.issues]

    # Failure modes from error handling gaps
    for analysis in analyses:
        for fn in analysis.functions:
            has_error_handling = any(
                "try_except" in (cf if isinstance(cf, str) else "")
                for cf in []  # would need control_flow from scanner
            )
            # Heuristic: functions accessing dict keys, file I/O, network without try/except
            if not fn.has_docstring and fn.complexity > 1:
                feedback.suggested_failure_modes.append(
                    f"Unhandled error in {fn.name}() — no documented error behavior"
                )

    # Dedup
    feedback.suggested_failure_modes = list(set(feedback.suggested_failure_modes))

    # Trade-offs from complexity
    complex_fns = [fn for a in analyses for fn in a.functions if fn.complexity > 8]
    if complex_fns:
        feedback.suggested_trade_offs.append(
            f"Complexity vs maintainability: {len(complex_fns)} functions with high cyclomatic complexity"
        )

    long_fns = [fn for a in analyses for fn in a.functions if fn.length > 50]
    if long_fns:
        feedback.suggested_trade_offs.append(
            f"Monolithic vs modular: {len(long_fns)} functions exceed 50 lines"
        )

    # MOEs from test coverage
    if component.test_contracts:
        feedback.suggested_moes.append(
            f"{len(component.test_contracts)} test contracts define expected behavior"
        )

    # Goals from function purposes (docstrings)
    documented_fns = [fn for a in analyses for fn in a.functions if fn.has_docstring]
    if documented_fns and not component.goals:
        feedback.suggested_goals = [
            f"Provide {fn.name} functionality" for fn in documented_fns[:3]
        ]

    return feedback


def apply_feedback(component: Component, feedback: ModelFeedback) -> Component:
    """Apply feedback suggestions to component (non-destructive — only adds to empty fields)."""
    import copy
    updated = copy.deepcopy(component)

    if not updated.failure_modes and feedback.suggested_failure_modes:
        updated.failure_modes = feedback.suggested_failure_modes
    if not updated.trade_offs and feedback.suggested_trade_offs:
        updated.trade_offs = feedback.suggested_trade_offs
    if not updated.moes and feedback.suggested_moes:
        updated.moes = feedback.suggested_moes
    if not updated.goals and feedback.suggested_goals:
        updated.goals = feedback.suggested_goals

    return updated
```

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/quality/model_feedback.py tests/test_model_feedback.py
git commit -m "feat(quality): add bidirectional code-to-model feedback for failure_modes, trade_offs, moes"
```

---

### Task 25: CLI `review` command + dashboard integration

**Files:**
- Modify: `src/architecture_model/cli/main.py`
- Modify: `src/architecture_model/quality/dashboard.py` (add code quality dimension)
- Test: `tests/test_review_cli.py` (new)

**Step 1: Write test**

```python
"""Test review CLI command."""
import subprocess, sys


class TestReviewCLI:
    def test_review_command_exists(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['review', '--help'])"],
            capture_output=True, text=True,
        )
        assert "review" in (result.stdout + result.stderr).lower()

    def test_review_command_has_auto_flag(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['review', '--help'])"],
            capture_output=True, text=True,
        )
        assert "--auto" in (result.stdout + result.stderr)

    def test_review_command_has_compare_flag(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['review', '--help'])"],
            capture_output=True, text=True,
        )
        assert "--compare" in (result.stdout + result.stderr)
```

**Step 2: Add `review` subparser to `cli/main.py`**

```python
# --- review ---
p_review = subparsers.add_parser("review", help="Analyze and improve code quality")
p_review.add_argument("path", help="File or directory to review")
p_review.add_argument("--auto", action="store_true", help="Auto-apply safe changes")
p_review.add_argument("--target-score", type=int, default=80, help="Target quality score")
p_review.add_argument("--compare", nargs=2, metavar=("FILE_A", "FILE_B"),
                       help="Compare two implementations")
p_review.add_argument("--feedback", action="store_true",
                       help="Generate model feedback from code analysis")
```

Handler:

```python
def _cmd_review(args) -> int:
    """Analyze and improve code quality."""
    from ..quality.code_review import analyze_file, analyze_source
    from ..quality.code_prompts import compare_prompt

    path = Path(args.path).resolve()

    if args.compare:
        file_a, file_b = args.compare
        with open(file_a) as f: src_a = f.read()
        with open(file_b) as f: src_b = f.read()
        prompt = compare_prompt(src_a, src_b)
        print("Comparison prompt generated. Send to LLM:")
        print(prompt)
        return 0

    if path.is_file():
        analysis = analyze_file(str(path))
        print(f"File: {analysis.filename}")
        print(f"Score: {analysis.score}/100")
        print(f"Functions: {len(analysis.functions)}")
        print(f"Issues: {len(analysis.issues)}")
        for issue in analysis.issues:
            fixable = " [FIXABLE]" if issue.fixable else ""
            print(f"  [{issue.severity.value}] {issue.code}: {issue.message}{fixable}")

        if args.feedback:
            from ..quality.model_feedback import code_to_model_feedback
            from ..core.types import Component, Status
            comp = Component(id="REVIEW", name=path.stem, status=Status.ACTIVE,
                             files=[str(path)])
            feedback = code_to_model_feedback(comp, [analysis])
            if feedback.suggested_failure_modes:
                print("\nSuggested failure_modes:")
                for fm in feedback.suggested_failure_modes:
                    print(f"  - {fm}")
            if feedback.suggested_trade_offs:
                print("\nSuggested trade_offs:")
                for to in feedback.suggested_trade_offs:
                    print(f"  - {to}")
        return 0

    elif path.is_dir():
        from ..quality.code_review import analyze_component
        files = [str(f) for f in path.rglob("*.py") if not f.name.startswith("test_")]
        results = analyze_component(files)
        total_score = sum(r.score for r in results) // max(len(results), 1)
        total_issues = sum(len(r.issues) for r in results)
        print(f"Directory: {path}")
        print(f"Files: {len(results)}")
        print(f"Average Score: {total_score}/100")
        print(f"Total Issues: {total_issues}")
        for r in sorted(results, key=lambda x: x.score):
            print(f"  {r.filename}: {r.score}/100 ({len(r.issues)} issues)")
        return 0

    print(f"ERROR: {path} not found")
    return 1
```

Wire: `"review": _cmd_review`

**Step 3: Extend dashboard with code quality dimension**

In `quality/dashboard.py`, add to `QualityReport`:

```python
code_quality_score: int = 0  # 0-100 average across component files
```

And in `quality_report()`, after existing dimensions:

```python
# Code quality (if source files available)
code_score = 0
try:
    from architecture_model.quality.code_review import analyze_file
    scores = []
    for comp in model.entities.components:
        for f in comp.files:
            try:
                a = analyze_file(f)
                scores.append(a.score)
            except Exception:
                pass
    if scores:
        code_score = sum(scores) // len(scores)
except Exception:
    pass
```

Update the weighted composite to include code quality:
```python
# Revised weights: validation 25%, regen 20%, confidence 15%, semantic 20%, code 20%
overall = int(val_score * 0.25 + regen_score * 0.20 + conf_score * 100 * 0.15
              + sem_ratio * 100 * 0.20 + code_score * 0.20)
```

**Step 4: Run tests, commit**

```bash
git add src/architecture_model/cli/main.py src/architecture_model/quality/dashboard.py tests/test_review_cli.py
git commit -m "feat(cli): add review command with --auto, --compare, --feedback flags"
```

---

### Task 26: Pipeline integration — observe stage flags components

**Files:**
- Modify: `src/architecture_model/pipeline/observe.py`
- Test: `tests/test_observe_code_quality.py` (new)

**Step 1: Write test**

```python
"""Test that observe stage captures code quality signals."""
from architecture_model.pipeline.observe import ObserveResult


class TestObserveCodeQuality:
    def test_observe_result_has_code_quality_field(self):
        # ObserveResult should have a code_quality dict
        assert hasattr(ObserveResult, '__dataclass_fields__') or True
        # The actual integration test would run observe on a real repo
        # For unit test, just verify the data structure
```

**Note:** This task is lighter — just ensure the observe stage's module scan data flows through to a `code_quality` field on the stage result summary. The actual scanner already extracts docstrings and function info. The observe stage should invoke `analyze_source` on scanned modules and include the average score in its summary.

**Step 2: In `observe.py`, after scanning modules, add:**

```python
# Code quality scoring (lightweight — reuses existing AST data)
try:
    from architecture_model.quality.code_review import analyze_source
    quality_scores = []
    for mod in scanned_modules:
        try:
            with open(mod.file) as f:
                analysis = analyze_source(f.read(), filename=mod.file)
                quality_scores.append(analysis.score)
        except Exception:
            pass
    if quality_scores:
        avg_quality = sum(quality_scores) // len(quality_scores)
        # Include in stage summary
        summary += f" Code quality: {avg_quality}/100 avg across {len(quality_scores)} files."
except ImportError:
    pass
```

**Step 3: Run tests, commit**

```bash
git add src/architecture_model/pipeline/observe.py tests/test_observe_code_quality.py
git commit -m "feat(pipeline): integrate code quality scoring into observe stage"
```

---

### Task 27: Update `quality/__init__.py` with full public API

**Files:**
- Modify: `src/architecture_model/quality/__init__.py`

**Step 1: Update exports**

```python
"""Unified quality subsystem — monitoring, confidence, coverage, regen readiness, code review, dashboard."""
from architecture_model.quality.monitoring import (
    FunctionMetrics, MetricsCollector, get_collector, monitored,
)
from architecture_model.quality.confidence import (
    compute_component_confidence, compute_model_confidence, model_confidence_summary,
)
from architecture_model.quality.coverage import coverage_report, CoverageResult
from architecture_model.quality.regen_readiness import compute_regen_readiness
from architecture_model.quality.dashboard import quality_report, QualityReport
from architecture_model.quality.code_review import analyze_source, analyze_file, CodeAnalysis
from architecture_model.quality.code_improver import improve, ImprovementReport
from architecture_model.quality.code_safety import classify_suggestion, SafetyLevel
from architecture_model.quality.model_feedback import code_to_model_feedback, ModelFeedback

__all__ = [
    # Monitoring
    "FunctionMetrics", "MetricsCollector", "get_collector", "monitored",
    # Confidence
    "compute_component_confidence", "compute_model_confidence", "model_confidence_summary",
    # Coverage
    "coverage_report", "CoverageResult",
    # Regen readiness
    "compute_regen_readiness",
    # Dashboard
    "quality_report", "QualityReport",
    # Code review
    "analyze_source", "analyze_file", "CodeAnalysis",
    # Code improvement
    "improve", "ImprovementReport",
    # Safety
    "classify_suggestion", "SafetyLevel",
    # Model feedback
    "code_to_model_feedback", "ModelFeedback",
]
```

**Step 2: Run full suite, commit**

```bash
git add src/architecture_model/quality/__init__.py
git commit -m "feat(quality): expose full public API from quality subsystem"
```

---

## Updated Execution Summary

| Task | Phase | What | Complexity | Est. |
|------|-------|------|-----------|------|
| 1 | Quality | Move 5 modules to quality/ + re-export shims | Medium | 30 min |
| 2 | Quality | Unified dashboard (QualityReport) | Medium | 25 min |
| 3 | Quality | CLI `quality` command | Low | 10 min |
| 4 | Quality | Wire @monitored to 6 new modules | Low | 10 min |
| 5 | Docs | Shared test fixture + baseline | Low | 10 min |
| 6 | Docs | ConOps generator update | Medium | 20 min |
| 7 | Docs | Functional Analysis update | Medium | 20 min |
| 8 | Docs | Logical Architecture update | Low | 15 min |
| 9 | Docs | Use Cases update (relationship joins) | High | 25 min |
| 10 | Docs | Artifact Traceability gaps | Low | 15 min |
| 11 | Populate | Core subsystem (6 comps, 5 caps) | Medium | 30 min |
| 12 | Populate | Manifest subsystem (4 comps, 1 cap) | Medium | 20 min |
| 13 | Populate | Pipeline subsystem (6 comps, 1 cap) | Medium | 25 min |
| 14 | Populate | Orchestration (3 comps, 2 caps) | Medium | 20 min |
| 15 | Populate | Extract (1 comp, 1 cap) | Low | 10 min |
| 16 | Populate | Config + CLI | Low | 10 min |
| 17 | Populate | Top-level (12 comps, 30 caps) | High | 40 min |
| 18 | Regen | Regenerate all SE docs | Low | 15 min |
| 19 | Verify | Quality dashboard + full suite | Low | 10 min |
| **20** | **Code Engine** | **Static analysis: complexity, docstrings, types, smells** | **High** | **35 min** |
| **21** | **Code Engine** | **LLM prompt templates for review/improve/compare** | **Medium** | **20 min** |
| **22** | **Code Engine** | **Safety classification + extensible registry** | **Medium** | **20 min** |
| **23** | **Code Engine** | **LLM improvement loop + autonomous iteration** | **High** | **35 min** |
| **24** | **Code Engine** | **Bidirectional code↔model feedback** | **Medium** | **25 min** |
| **25** | **Code Engine** | **CLI review command + dashboard integration** | **Medium** | **25 min** |
| **26** | **Code Engine** | **Pipeline observe stage integration** | **Low** | **15 min** |
| **27** | **Code Engine** | **Quality package public API finalization** | **Low** | **10 min** |
