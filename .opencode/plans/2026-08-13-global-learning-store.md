# Global Learning Store Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a cross-project learning store that captures heuristic rules, archetype patterns, and workflow lessons — auto-applied by pipeline stages.

**Architecture:** `GlobalLearningStore` class in `pipeline/global_learning.py` persists to `~/.config/opencode/arch-learning/`. Stages receive it via `PipelineContext.global_learning`. New MCP tool `architect_learn` in opencode-arch records learnings.

**Tech Stack:** Python dataclasses, JSON persistence, existing PipelineContext pattern.

---

### Task 1: GlobalLearningStore data model + persistence

**Files:**
- Create: `src/architecture_model/pipeline/global_learning.py`
- Test: `tests/test_pipeline_global_learning.py`

**Step 1: Write the failing test**

```python
"""Tests for GlobalLearningStore."""
import json
import tempfile
from pathlib import Path

import pytest

from architecture_model.pipeline.global_learning import (
    ArchetypePattern,
    GlobalLearningStore,
    HeuristicRule,
    WorkflowLesson,
)


@pytest.fixture
def store(tmp_path):
    return GlobalLearningStore(tmp_path / "learning")


class TestHeuristicRules:
    def test_add_and_get(self, store):
        rule = HeuristicRule(
            id="HR-001",
            stage="infer",
            condition="module_count > 50",
            action="use package_group strategy",
            rationale="Per-module grouping produces too many capabilities",
            learned_from="django extraction 2026-08-12",
            validated_on=["django"],
            threshold={"parameter": "LARGE_REPO_MODULE_THRESHOLD", "value": 50},
        )
        store.add_heuristic(rule)
        rules = store.get_heuristics(stage="infer")
        assert len(rules) == 1
        assert rules[0].id == "HR-001"
        assert rules[0].condition == "module_count > 50"

    def test_filter_by_stage(self, store):
        store.add_heuristic(HeuristicRule(
            id="HR-001", stage="infer", condition="x > 1",
            action="a", rationale="r", learned_from="test",
            validated_on=[], threshold={},
        ))
        store.add_heuristic(HeuristicRule(
            id="HR-002", stage="allocate", condition="y > 2",
            action="b", rationale="r", learned_from="test",
            validated_on=[], threshold={},
        ))
        assert len(store.get_heuristics(stage="infer")) == 1
        assert len(store.get_heuristics(stage="allocate")) == 1
        assert len(store.get_heuristics()) == 2

    def test_validate_on(self, store):
        store.add_heuristic(HeuristicRule(
            id="HR-001", stage="infer", condition="x",
            action="a", rationale="r", learned_from="test",
            validated_on=["django"], threshold={},
        ))
        store.validate_heuristic("HR-001", "flask")
        rules = store.get_heuristics()
        assert "flask" in rules[0].validated_on


class TestArchetypePatterns:
    def test_add_and_get(self, store):
        pattern = ArchetypePattern(
            id="AP-001",
            name="contrib-monolith",
            indicators=["top-level dir with >5 sub-packages"],
            problem="Single-level grouping treats entire dir as one capability",
            solution="Recurse one level for packages exceeding file threshold",
            applicable_repos=["django"],
        )
        store.add_archetype(pattern)
        patterns = store.get_archetypes()
        assert len(patterns) == 1
        assert patterns[0].name == "contrib-monolith"

    def test_match_indicators(self, store):
        store.add_archetype(ArchetypePattern(
            id="AP-001", name="contrib-monolith",
            indicators=["contrib_dir_exists", "sub_package_count > 5"],
            problem="p", solution="s", applicable_repos=[],
        ))
        # match returns patterns where at least one indicator matches
        matches = store.match_archetypes(["contrib_dir_exists"])
        assert len(matches) == 1


class TestWorkflowLessons:
    def test_add_and_get(self, store):
        lesson = WorkflowLesson(
            id="WL-001",
            trigger="validate_score < 50 AND component_count > 100",
            diagnosis="allocate stage seeding too many components",
            fix_applied="Package-level seeding in _seed_from_capabilities()",
            validation="Django: 285→24 components, score 15→85",
            files_changed=["pipeline/infer.py", "pipeline/allocate.py"],
            commit="d0f5e12",
        )
        store.add_workflow(lesson)
        lessons = store.get_workflows()
        assert len(lessons) == 1
        assert lessons[0].trigger == "validate_score < 50 AND component_count > 100"


class TestPersistence:
    def test_survives_reload(self, tmp_path):
        path = tmp_path / "learning"
        store1 = GlobalLearningStore(path)
        store1.add_heuristic(HeuristicRule(
            id="HR-001", stage="infer", condition="x",
            action="a", rationale="r", learned_from="test",
            validated_on=[], threshold={},
        ))
        store2 = GlobalLearningStore(path)
        assert len(store2.get_heuristics()) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_global_learning.py -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

```python
"""Cross-project global learning store.

Persists heuristic rules, archetype patterns, and workflow lessons
to ~/.config/opencode/arch-learning/ for reuse across all projects.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HeuristicRule:
    """A learned pipeline behavior rule (auto-applied by stages)."""
    id: str
    stage: str                    # infer | allocate | relate | decompose | ...
    condition: str                # human-readable condition
    action: str                   # what the stage should do differently
    rationale: str                # why this rule exists
    learned_from: str             # which repo/extraction taught us this
    validated_on: list[str] = field(default_factory=list)
    threshold: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchetypePattern:
    """A repo structure pattern with known problem/solution."""
    id: str
    name: str                     # human-readable name
    indicators: list[str]         # observable signals that identify this archetype
    problem: str                  # what goes wrong without intervention
    solution: str                 # recommended fix
    applicable_repos: list[str] = field(default_factory=list)


@dataclass
class WorkflowLesson:
    """A complete improvement cycle record."""
    id: str
    trigger: str                  # what quality signal initiated the improvement
    diagnosis: str                # root cause identified
    fix_applied: str              # what was changed
    validation: str               # before/after metrics
    files_changed: list[str] = field(default_factory=list)
    commit: str = ""


class GlobalLearningStore:
    """Cross-project learning persistence.

    Stores heuristic rules, archetype patterns, and workflow lessons
    for reuse across all extractions.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    # --- Heuristic Rules ---

    def add_heuristic(self, rule: HeuristicRule) -> None:
        rules = self._load_json("heuristics.json", [])
        # Replace if same ID exists
        rules = [r for r in rules if r.get("id") != rule.id]
        rules.append(asdict(rule))
        self._save_json("heuristics.json", rules)

    def get_heuristics(self, stage: str | None = None) -> list[HeuristicRule]:
        data = self._load_json("heuristics.json", [])
        rules = [HeuristicRule(**d) for d in data]
        if stage:
            rules = [r for r in rules if r.stage == stage]
        return rules

    def validate_heuristic(self, rule_id: str, repo: str) -> None:
        """Record that a heuristic was validated on a new repo."""
        rules = self._load_json("heuristics.json", [])
        for r in rules:
            if r["id"] == rule_id and repo not in r["validated_on"]:
                r["validated_on"].append(repo)
        self._save_json("heuristics.json", rules)

    # --- Archetype Patterns ---

    def add_archetype(self, pattern: ArchetypePattern) -> None:
        patterns = self._load_json("archetypes.json", [])
        patterns = [p for p in patterns if p.get("id") != pattern.id]
        patterns.append(asdict(pattern))
        self._save_json("archetypes.json", patterns)

    def get_archetypes(self) -> list[ArchetypePattern]:
        data = self._load_json("archetypes.json", [])
        return [ArchetypePattern(**d) for d in data]

    def match_archetypes(self, observed_indicators: list[str]) -> list[ArchetypePattern]:
        """Return patterns where at least one indicator matches."""
        all_patterns = self.get_archetypes()
        return [
            p for p in all_patterns
            if any(ind in observed_indicators for ind in p.indicators)
        ]

    # --- Workflow Lessons ---

    def add_workflow(self, lesson: WorkflowLesson) -> None:
        lessons = self._load_json("workflows.json", [])
        lessons = [l for l in lessons if l.get("id") != lesson.id]
        lessons.append(asdict(lesson))
        self._save_json("workflows.json", lessons)

    def get_workflows(self) -> list[WorkflowLesson]:
        data = self._load_json("workflows.json", [])
        return [WorkflowLesson(**d) for d in data]

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

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline_global_learning.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/global_learning.py tests/test_pipeline_global_learning.py
git commit -m "feat(pipeline): add GlobalLearningStore for cross-project learning"
```

---

### Task 2: Integrate GlobalLearningStore into PipelineContext

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py` (add field)
- Modify: `src/architecture_model/pipeline/coordinator.py` (accept + attach)
- Modify: `src/architecture_model/pipeline/__init__.py` (export new types)
- Test: `tests/test_pipeline_global_learning.py` (add integration test)

**Step 1: Write the failing test**

Add to `tests/test_pipeline_global_learning.py`:

```python
class TestPipelineIntegration:
    def test_context_has_global_learning(self, store):
        from architecture_model.pipeline.protocol import PipelineContext
        ctx = PipelineContext(repo_path=Path("/tmp/test"))
        ctx.global_learning = store
        assert ctx.global_learning is store
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_global_learning.py::TestPipelineIntegration -v`
Expected: FAIL — AttributeError: no `global_learning` field

**Step 3: Add `global_learning` to PipelineContext**

In `protocol.py`, add field after `learning_store`:
```python
global_learning: GlobalLearningStore | None = field(default=None, repr=False)
```

In `coordinator.py`, add `global_learning` parameter to `__init__`:
```python
def __init__(self, stages, learning_store=None, global_learning=None):
    ...
    self._global_learning = global_learning
```

And in the run method where context is set up:
```python
if self._global_learning and not ctx.global_learning:
    ctx.global_learning = self._global_learning
```

In `__init__.py`, add exports:
```python
from architecture_model.pipeline.global_learning import (
    ArchetypePattern,
    GlobalLearningStore,
    HeuristicRule,
    WorkflowLesson,
)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline_global_learning.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add -u
git commit -m "feat(pipeline): integrate GlobalLearningStore into PipelineContext"
```

---

### Task 3: Stage auto-application of heuristics

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py` (check heuristics before grouping decision)
- Modify: `src/architecture_model/pipeline/allocate.py` (check heuristics before seeding)
- Test: `tests/test_pipeline_global_learning.py` (add stage tests)

**Step 1: Write the failing test**

```python
class TestStageHeuristicApplication:
    def test_infer_uses_heuristic_threshold(self, store, tmp_path):
        """If a heuristic overrides LARGE_REPO_MODULE_THRESHOLD, infer uses it."""
        from architecture_model.pipeline.infer import InferStage, _LARGE_REPO_MODULE_THRESHOLD
        from architecture_model.pipeline.protocol import PipelineContext

        store.add_heuristic(HeuristicRule(
            id="HR-TEST", stage="infer",
            condition="module_count > 30",
            action="use package_group strategy",
            rationale="test",
            learned_from="test",
            validated_on=[],
            threshold={"parameter": "LARGE_REPO_MODULE_THRESHOLD", "value": 30},
        ))

        ctx = PipelineContext(repo_path=tmp_path)
        ctx.global_learning = store
        # The stage should pick up the threshold override
        threshold = InferStage._get_large_repo_threshold(ctx)
        assert threshold == 30
```

**Step 2: Run test — fails (no `_get_large_repo_threshold` method)**

**Step 3: Add `_get_large_repo_threshold` class method to InferStage**

```python
@classmethod
def _get_large_repo_threshold(cls, ctx: PipelineContext) -> int:
    """Get large repo threshold, checking global heuristics first."""
    if ctx.global_learning:
        rules = ctx.global_learning.get_heuristics(stage="infer")
        for rule in rules:
            if rule.threshold.get("parameter") == "LARGE_REPO_MODULE_THRESHOLD":
                return int(rule.threshold["value"])
    return _LARGE_REPO_MODULE_THRESHOLD
```

Then update `_infer_capabilities()` to call `self._get_large_repo_threshold(ctx)` instead of using the module constant directly.

**Step 4: Run tests**

Run: `pytest tests/test_pipeline_global_learning.py tests/test_pipeline_stages.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add -u
git commit -m "feat(infer): auto-apply global heuristic thresholds"
```

---

### Task 4: MCP tool `architect_learn` in opencode-arch

**Files:**
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/server.py` (add tool)
- Test: `/Users/baigm2/Documents/Projects/opencode-arch/tests/test_learn_tool.py`

**Step 1: Write the failing test**

```python
"""Tests for architect_learn MCP tool."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from opencode_arch.mcp.server import app


@pytest.fixture
def learning_path(tmp_path):
    return tmp_path / "arch-learning"


class TestArchitectLearn:
    @pytest.mark.asyncio
    async def test_add_heuristic(self, learning_path):
        with patch("opencode_arch.mcp.server.GLOBAL_LEARNING_PATH", learning_path):
            result = await app.architect_learn(
                learning_type="heuristic",
                stage="infer",
                condition="module_count > 50",
                action="use package_group strategy",
                rationale="Per-module grouping produces too many capabilities for large repos",
                learned_from="django extraction 2026-08-12",
            )
        assert "HR-" in result
        assert (learning_path / "heuristics.json").exists()

    @pytest.mark.asyncio
    async def test_add_archetype(self, learning_path):
        with patch("opencode_arch.mcp.server.GLOBAL_LEARNING_PATH", learning_path):
            result = await app.architect_learn(
                learning_type="archetype",
                name="contrib-monolith",
                indicators="top-level dir with >5 sub-packages, each sub-package >10 files",
                problem="Single-level grouping treats entire dir as one capability",
                solution="Recurse one level for packages exceeding file threshold",
            )
        assert "AP-" in result

    @pytest.mark.asyncio
    async def test_add_workflow(self, learning_path):
        with patch("opencode_arch.mcp.server.GLOBAL_LEARNING_PATH", learning_path):
            result = await app.architect_learn(
                learning_type="workflow",
                trigger="validate_score < 50 AND component_count > 100",
                diagnosis="allocate stage seeding too many components",
                fix_applied="Package-level seeding in _seed_from_capabilities()",
                validation="Django: 285→24 components, score 15→85",
                files_changed="pipeline/infer.py, pipeline/allocate.py",
                commit="d0f5e12",
            )
        assert "WL-" in result
```

**Step 2: Run test — fails (no `architect_learn` tool)**

**Step 3: Implement the MCP tool**

Add to `server.py`:

```python
GLOBAL_LEARNING_PATH = Path.home() / ".config" / "opencode" / "arch-learning"

@app.tool()
async def architect_learn(
    learning_type: str,
    stage: str = "",
    condition: str = "",
    action: str = "",
    rationale: str = "",
    learned_from: str = "",
    name: str = "",
    indicators: str = "",
    problem: str = "",
    solution: str = "",
    trigger: str = "",
    diagnosis: str = "",
    fix_applied: str = "",
    validation: str = "",
    files_changed: str = "",
    commit: str = "",
) -> str:
    """Record a learning (heuristic, archetype, or workflow) to the global store."""
    from architecture_model.pipeline.global_learning import (
        ArchetypePattern,
        GlobalLearningStore,
        HeuristicRule,
        WorkflowLesson,
    )

    store = GlobalLearningStore(GLOBAL_LEARNING_PATH)

    if learning_type == "heuristic":
        existing = store.get_heuristics()
        next_id = f"HR-{len(existing) + 1:03d}"
        store.add_heuristic(HeuristicRule(
            id=next_id, stage=stage, condition=condition,
            action=action, rationale=rationale, learned_from=learned_from,
            validated_on=[], threshold={},
        ))
        return f"Recorded heuristic {next_id}: {condition} → {action}"

    elif learning_type == "archetype":
        existing = store.get_archetypes()
        next_id = f"AP-{len(existing) + 1:03d}"
        store.add_archetype(ArchetypePattern(
            id=next_id, name=name,
            indicators=[i.strip() for i in indicators.split(",")],
            problem=problem, solution=solution, applicable_repos=[],
        ))
        return f"Recorded archetype {next_id}: {name}"

    elif learning_type == "workflow":
        existing = store.get_workflows()
        next_id = f"WL-{len(existing) + 1:03d}"
        store.add_workflow(WorkflowLesson(
            id=next_id, trigger=trigger, diagnosis=diagnosis,
            fix_applied=fix_applied, validation=validation,
            files_changed=[f.strip() for f in files_changed.split(",") if f.strip()],
            commit=commit,
        ))
        return f"Recorded workflow lesson {next_id}: {trigger}"

    else:
        return f"Unknown learning_type: {learning_type}. Use: heuristic, archetype, workflow"
```

**Step 4: Run tests**

Run: `pytest tests/test_learn_tool.py -v` (from opencode-arch)
Expected: ALL PASS

**Step 5: Commit** (in opencode-arch repo)

```bash
git add -u tests/test_learn_tool.py
git commit -m "feat(mcp): add architect_learn tool for recording global learnings"
```

---

### Task 5: Seed initial learnings from Django work

**Files:**
- No code changes — use the MCP tool to record our Django learnings

**Step 1: Record the heuristics we already hard-coded**

Call `architect_learn` with:
- HR-001: `stage=infer, condition="module_count > 50", action="group capabilities by top-level package directory", rationale="Per-module grouping produces N capabilities where N ≈ module_count, overwhelming downstream stages", learned_from="django 2026-08-12"`
- HR-002: `stage=infer, condition="route_count > 10", action="consolidate all routes into single Web Routes capability", rationale="Per-route capabilities fragment URL handling across many small components", learned_from="django 2026-08-12"`

**Step 2: Record the archetype**

- AP-001: `name="contrib-monolith", indicators="top-level dir with >5 sub-packages each having >10 files", problem="Single-level package grouping treats entire directory as one capability", solution="Recurse one level for packages exceeding file threshold"`

**Step 3: Record the workflow**

- WL-001: `trigger="validate_score < 50 AND component_count > 100", diagnosis="allocate stage seeding one component per capability due to per-module infer strategy", fix_applied="Added _LARGE_REPO_MODULE_THRESHOLD=50 in infer + package-dir matching in allocate _seed_from_capabilities()", validation="Django: 285→24 components, score 15→85", files_changed="pipeline/infer.py, pipeline/allocate.py", commit="d0f5e12"`

---

### Task 6: CLI command `architecture-model learnings`

**Files:**
- Modify: `src/architecture_model/cli/main.py` (add `learnings` command)
- Test: `tests/test_cli_learnings.py`

**Step 1: Write the failing test**

```python
"""Tests for learnings CLI command."""
from click.testing import CliRunner
from architecture_model.cli.main import cli


def test_learnings_show(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "architecture_model.cli.main.GLOBAL_LEARNING_PATH", tmp_path / "learning"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["learnings"])
    assert result.exit_code == 0
    assert "heuristics" in result.output.lower() or "No learnings" in result.output
```

**Step 2: Implement CLI command**

```python
@cli.command()
def learnings():
    """Show global learnings (heuristics, archetypes, workflows)."""
    from architecture_model.pipeline.global_learning import GlobalLearningStore

    store = GlobalLearningStore(GLOBAL_LEARNING_PATH)
    rules = store.get_heuristics()
    archetypes = store.get_archetypes()
    workflows = store.get_workflows()

    if not rules and not archetypes and not workflows:
        click.echo("No learnings recorded yet. Use architect_learn to add.")
        return

    if rules:
        click.echo(f"\n## Heuristic Rules ({len(rules)})")
        for r in rules:
            click.echo(f"  {r.id} [{r.stage}]: {r.condition} → {r.action}")
            if r.validated_on:
                click.echo(f"         validated on: {', '.join(r.validated_on)}")

    if archetypes:
        click.echo(f"\n## Archetype Patterns ({len(archetypes)})")
        for a in archetypes:
            click.echo(f"  {a.id} {a.name}: {a.problem}")

    if workflows:
        click.echo(f"\n## Workflow Lessons ({len(workflows)})")
        for w in workflows:
            click.echo(f"  {w.id}: {w.trigger}")
            click.echo(f"         fix: {w.fix_applied}")
```

**Step 3: Run tests**

Run: `pytest tests/test_cli_learnings.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -u tests/test_cli_learnings.py
git commit -m "feat(cli): add learnings command to display global learning store"
```

---

## Summary

| Task | Repo | Description |
|------|------|-------------|
| 1 | arch-std | GlobalLearningStore class + tests |
| 2 | arch-std | Integrate into PipelineContext |
| 3 | arch-std | Stage auto-application (infer threshold) |
| 4 | opencode-arch | MCP tool `architect_learn` |
| 5 | — | Seed Django learnings via tool |
| 6 | arch-std | CLI `learnings` command |

Total: ~6 tasks, each 5-15 min. TDD throughout.
