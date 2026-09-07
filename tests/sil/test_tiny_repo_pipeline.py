"""Integration test: run the full pipeline against tests/fixtures/sil/tiny_repo/.

Closes DoD steps 3 (pipeline runs on tiny_repo) and part of 6 (SIL events are
actually emitted by the ``@instrumented`` stage decorators when a store is
bound). We use a recording in-memory store rather than the OCA SQLite backend
so this test has zero cross-repo dependencies.

Assertions:
    1. Pipeline runs observe → contract without raising.
    2. Every stage that carries an ``@instrumented("stage:*")`` decorator
       emits at least one SIL event with matching component_id.
    3. All emitted stage events have kind="invocation" and outcome="ok".
"""
from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.contract import ContractStage
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.sil.decorators import bind_store


TINY_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "sil" / "tiny_repo"


class RecordingStore:
    """Minimal SIL store used to observe what the decorators emit."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, component_id, kind, outcome, duration_ms, ref=None):
        self.events.append(
            {
                "component_id": component_id,
                "kind": kind,
                "outcome": outcome,
                "duration_ms": duration_ms,
                "ref": ref,
            }
        )


@pytest.fixture
def store():
    s = RecordingStore()
    bind_store(s)
    yield s
    bind_store(None)


def test_tiny_repo_pipeline_runs_and_emits_sil_events(store, tmp_path):
    """The pipeline runs cleanly against tiny_repo and every stage records at
    least one SIL event under its declared component_id."""
    import shutil

    assert TINY_REPO.exists(), f"fixture missing: {TINY_REPO}"

    # Copy the fixture into tmp_path so the pipeline's incidental writes
    # (learning cache, .architecture/ artifacts) don't pollute the tree.
    workdir = tmp_path / "repo"
    shutil.copytree(TINY_REPO, workdir)

    ctx = PipelineContext(repo_path=workdir, output_dir=tmp_path / ".arch")
    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
    }
    results = PipelineCoordinator(stages).run_all(ctx)

    # 1. Every requested stage ran and produced a StageResult.
    assert set(results) == set(stages)

    # 2. Observe actually walked tiny_repo — three modules under tiny_pkg/.
    obs_output = results["observe"].output
    module_paths = {str(m.path) for m in obs_output.modules}
    assert any(p.endswith("tiny_pkg/api.py") for p in module_paths), module_paths
    assert any(p.endswith("tiny_pkg/core.py") for p in module_paths)
    assert any(p.endswith("tiny_pkg/storage.py") for p in module_paths)

    # 3. Every stage should have emitted at least one SIL event with the
    #    "stage:<name>" component_id declared by its @instrumented decorator.
    emitted_ids = {e["component_id"] for e in store.events}
    for stage_name in stages:
        expected_id = f"stage:{stage_name}"
        assert expected_id in emitted_ids, (
            f"no SIL event for {expected_id}; got {sorted(emitted_ids)}"
        )

    # 4. Every stage event should be a successful invocation.
    stage_events = [e for e in store.events if e["component_id"].startswith("stage:")]
    assert stage_events, "no stage events at all"
    for e in stage_events:
        assert e["kind"] == "invocation"
        assert e["outcome"] == "ok", e
        assert e["duration_ms"] >= 0
        assert e["ref"] is None
