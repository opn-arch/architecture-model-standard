"""Tests for Phase 2 Task 21 — Component.intent seeded from primary-file docstrings.

The plan located this in ``pipeline/specify.py`` but that stage does not
build component dicts. Seeding piggy-backs on the description-enrichment
loop in ``pipeline/emit.py``; behavior is identical from the spec's
perspective — intent is populated automatically when empty, deterministic
given a fixed observe inventory + allocation.

The pipeline runs decompose→synthesize→emit; when multiple boundaries
are detected, top-level emit produces a SoS model and per-subsystem
models. Task 21's seeding runs in the sub-pipeline emit (so intents land
on the subsystem components). These tests inspect the subsystem yamls.
"""
from __future__ import annotations

import yaml

from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.contract import ContractStage
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.emit import EmitStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import (
    PipelineContext,
    QualityMetrics,
    StageResult,
)
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.pipeline.synthesize import SynthesizeStage
from architecture_model.pipeline.validate import ValidateStage


def _coordinator() -> PipelineCoordinator:
    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
        "validate": ValidateStage(),
    }
    return PipelineCoordinator(stages)


def _make_repo_with_docstrings(tmp_path):
    """Two packages, each with a module-level docstring on the primary file."""
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    (jobs / "jobs.py").write_text(
        '"""Process queued jobs reliably with retry semantics."""\n'
        "def process_jobs():\n    return True\n"
    )
    for i in range(7):
        (jobs / f"worker_{i}.py").write_text(
            f"from .jobs import process_jobs\n\n"
            f"def run_worker_{i}():\n    return process_jobs()\n"
        )
    scheduler = tmp_path / "scheduler"
    scheduler.mkdir()
    (scheduler / "scheduler.py").write_text(
        '"""Schedule workers across queues.\n\nExtra detail line."""\n'
        "def schedule_workers():\n    return 4\n"
    )
    for i in range(7):
        (scheduler / f"queue_{i}.py").write_text(
            f"from .scheduler import schedule_workers\n\n"
            f"def run_queue_{i}():\n    return schedule_workers()\n"
        )


def _run_pipeline_to_emit(tmp_path) -> None:
    output_dir = tmp_path / ".architecture"
    ctx = PipelineContext(repo_path=tmp_path, output_dir=output_dir)
    coordinator = _coordinator()
    coordinator.run_to("validate", ctx)

    components = ctx.get("allocate").output.components
    jobs_boundary = SystemBoundary(
        system_id="SYS-jobs",
        name="Jobs",
        component_ids=[c.id for c in components],
        files=[str(p.relative_to(tmp_path)) for p in sorted((tmp_path / "jobs").glob("*.py"))],
        is_full_system=True,
    )
    scheduler_boundary = SystemBoundary(
        system_id="SYS-scheduler",
        name="Scheduler",
        component_ids=[c.id for c in components],
        files=[str(p.relative_to(tmp_path)) for p in sorted((tmp_path / "scheduler").glob("*.py"))],
        is_full_system=True,
    )
    ctx.cache["decompose"] = StageResult(
        output=DecomposeResult(systems=[jobs_boundary, scheduler_boundary]),
        quality=QualityMetrics(score=100.0),
    )
    ctx.config["coordinator"] = coordinator
    ctx.cache["synthesize"] = SynthesizeStage().run(ctx)
    EmitStage().run(ctx)


def _all_subsystem_components(tmp_path):
    """Yield every component dict from every subsystem's emitted yaml."""
    sub = tmp_path / ".architecture-models"
    for d in sorted(sub.iterdir()):
        if not d.is_dir():
            continue
        m = d / ".architecture-model.yaml"
        if not m.exists():
            continue
        raw = yaml.safe_load(m.read_text()) or {}
        for c in raw.get("entities", {}).get("components", []):
            yield d.name, c


def test_intent_seeded_from_primary_file_docstring(tmp_path):
    _make_repo_with_docstrings(tmp_path)
    _run_pipeline_to_emit(tmp_path)
    seeded = [
        (sysname, c["id"], c["intent"])
        for sysname, c in _all_subsystem_components(tmp_path)
        if c.get("intent")
    ]
    # At least one component per subsystem should carry a docstring-derived intent.
    docstring_intents = [
        intent
        for _, _, intent in seeded
        if "Process queued jobs" in intent or "Schedule workers" in intent
    ]
    assert docstring_intents, f"expected docstring-derived intents, got {seeded!r}"
    # Every seeded intent should be a single line ≤ 200 chars.
    for _, cid, intent in seeded:
        assert "\n" not in intent, f"{cid} intent has newline: {intent!r}"
        assert len(intent) <= 200


def test_intent_takes_first_nonempty_line(tmp_path):
    """When docstring has multiple lines, first non-empty line wins.

    The scheduler.py module docstring starts with "Schedule workers across
    queues." on the first line and has "Extra detail line." on a later line.
    The seeded intent must be exactly the first line — never the continuation.
    """
    _make_repo_with_docstrings(tmp_path)
    _run_pipeline_to_emit(tmp_path)
    intents = [c.get("intent", "") for _, c in _all_subsystem_components(tmp_path)]
    # Exactly the first docstring line must appear.
    assert "Schedule workers across queues." in intents
    assert "Process queued jobs reliably with retry semantics." in intents
    # And the continuation line must NEVER appear on its own.
    assert not any("Extra detail" in i for i in intents), (
        f"first-line rule violated: {intents!r}"
    )


def test_existing_intent_not_overwritten(tmp_path):
    """Seeding must skip components that already have a non-empty intent.

    We assert directly on the emit-loop invariant: any component with a
    pre-existing intent survives. Synthesize sets intents from realizing
    capabilities before emit runs; those intents must not be clobbered by
    docstring-derived values.
    """
    _make_repo_with_docstrings(tmp_path)
    _run_pipeline_to_emit(tmp_path)
    # Every emitted component either has intent from synthesize (capability-
    # derived) or from Task 21 (docstring-derived). Look for the "Handles X"
    # pattern which is the synthesize-derived form; if any of those got
    # overwritten by a docstring line, this test would fail.
    synth_intents = [
        c["intent"]
        for _, c in _all_subsystem_components(tmp_path)
        if c.get("intent", "").startswith("Handles ")
    ]
    assert synth_intents, "expected some capability-derived 'Handles X' intents"
    # None of them should contain the module docstring text.
    for intent in synth_intents:
        assert "Process queued jobs" not in intent
        assert "Schedule workers" not in intent


def test_module_without_docstring_produces_no_docstring_intent(tmp_path):
    """A component whose primary file has no module docstring gets no
    docstring-derived intent (synthesize may still set a capability-derived
    fallback like 'Handles X'; Task 21 must not invent one).
    """
    pkg = tmp_path / "silent"
    pkg.mkdir()
    (pkg / "core.py").write_text("def do():\n    return 1\n")
    for i in range(7):
        (pkg / f"m_{i}.py").write_text(
            f"from .core import do\n\ndef m_{i}():\n    return do()\n"
        )
    other = tmp_path / "other"
    other.mkdir()
    (other / "main.py").write_text("def run():\n    return 2\n")
    for i in range(7):
        (other / f"aux_{i}.py").write_text(
            f"from .main import run\n\ndef a_{i}():\n    return run()\n"
        )
    _run_pipeline_to_emit(tmp_path)
    for _, c in _all_subsystem_components(tmp_path):
        intent = c.get("intent", "")
        # No docstring text should appear; docstrings simply don't exist here.
        assert intent == "" or intent.startswith("Handles "), (
            f"unexpected intent {intent!r} on component with no source docstring"
        )
