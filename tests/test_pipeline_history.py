"""Tests for append-only pipeline execution history."""

from __future__ import annotations

import json

import pytest

from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.history import (
    PipelineRunRecord,
    append_pipeline_history,
    load_pipeline_history,
)
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext


def _run(run_id: str) -> PipelineRunRecord:
    return PipelineRunRecord(
        run_id=run_id,
        started_at="2026-09-01T12:00:00Z",
        completed_at="2026-09-01T12:00:01Z",
        duration_ms=1000,
        source="library",
        status="completed",
    )


def test_append_and_load_history_newest_first_with_limit(tmp_path):
    append_pipeline_history(tmp_path, _run("run-1"))
    append_pipeline_history(tmp_path, _run("run-2"))

    history_path = tmp_path / ".architecture" / "pipeline-history.jsonl"
    assert len(history_path.read_text().splitlines()) == 2
    assert [run.run_id for run in load_pipeline_history(tmp_path, limit=1)] == ["run-2"]


def test_load_history_skips_malformed_lines(tmp_path):
    history_dir = tmp_path / ".architecture"
    history_dir.mkdir()
    history_path = history_dir / "pipeline-history.jsonl"
    history_path.write_text(
        json.dumps(_run("run-1").to_dict()) + "\n{broken\n"
        + json.dumps(_run("run-2").to_dict()) + "\n"
    )

    assert [run.run_id for run in load_pipeline_history(tmp_path)] == ["run-2", "run-1"]


def test_load_history_falls_back_to_one_legacy_report_record(tmp_path):
    models_dir = tmp_path / ".architecture-models"
    models_dir.mkdir()
    (models_dir / "pipeline-report.md").write_text(
        "# Pipeline Report\n\n**Generated:** 2026-08-19T16:59:51Z\n"
        "**Total Duration:** 25ms\n\n"
        "| Stage | Score | Duration | LLM Calls |\n"
        "|---|---|---|---|\n| observe | 100 | 20ms | 0 |\n"
    )

    records = load_pipeline_history(tmp_path)

    assert len(records) == 1
    assert records[0].run_id == "legacy-pipeline-report"
    assert records[0].started_at == "2026-08-19T16:59:51Z"
    assert records[0].duration_ms == 25
    assert records[0].source == "legacy-report"
    assert records[0].stages[0].name == "observe"


def test_actual_pipeline_run_records_stage_component_and_module_outputs(tmp_path):
    (tmp_path / "service.py").write_text(
        "API_VERSION = '1'\n"
        "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
        "class Greeter:\n    pass\n"
    )
    stages = {"observe": ObserveStage(), "infer": InferStage(), "allocate": AllocateStage()}
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture", invocation_source="library")

    PipelineCoordinator(stages).run_to("allocate", ctx)

    record = load_pipeline_history(tmp_path)[0]
    assert record.status == "completed"
    assert [stage.name for stage in record.stages] == ["observe", "infer", "allocate"]
    assert record.components and "service.py" in record.components[0].files
    module = next(item for item in record.modules if item.path == "service.py")
    assert module.component_id == record.components[0].component_id
    assert module.produced_functions == ["greet"]
    assert module.produced_classes == ["Greeter"]
    assert module.produced_constants == ["API_VERSION"]
    assert record.stages[0].output_summary["modules"] == 1


def test_two_coordinator_runs_append_and_scoped_run_carries_context(tmp_path):
    (tmp_path / "mod.py").write_text("def work():\n    return 1\n")
    coord = PipelineCoordinator({"observe": ObserveStage()})
    coord.run_all(PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture"))
    coord.run_all(PipelineContext(
        repo_path=tmp_path,
        output_dir=tmp_path / ".architecture" / "child",
        scope="COMP-child",
        parent_run_id="parent-123",
        invocation_source="MCP",
        invocation="synthesize",
    ))

    records = load_pipeline_history(tmp_path)
    assert len(records) == 2
    assert records[0].run_id != records[1].run_id
    assert records[0].scope == "COMP-child"
    assert records[0].parent_run_id == "parent-123"
    assert records[0].source == "MCP"
    assert records[0].invocation == "synthesize"


def test_failed_pipeline_run_is_recorded_without_masking_exception(tmp_path):
    class BrokenStage:
        name = "broken"
        requires = []

        def run(self, ctx):
            raise RuntimeError("original failure")

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
    with pytest.raises(RuntimeError, match="original failure"):
        PipelineCoordinator({"broken": BrokenStage()}).run_all(ctx)

    record = load_pipeline_history(tmp_path)[0]
    assert record.status == "failed"
    assert record.error == "original failure"
    assert record.stages[0].name == "broken"
    assert record.stages[0].status == "failed"
