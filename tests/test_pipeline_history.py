"""Tests for append-only pipeline execution history."""

from __future__ import annotations

import json

import pytest

from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.history import (
    ComponentHistoryRecord,
    ModuleHistoryRecord,
    PipelineRunRecord,
    append_pipeline_history,
    finalize_pipeline_history,
    load_pipeline_history,
)
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext, QualityMetrics, StageResult
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.pipeline.contract import ContractStage


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


def test_malformed_only_jsonl_falls_back_to_legacy_report(tmp_path):
    history_dir = tmp_path / ".architecture"
    history_dir.mkdir()
    (history_dir / "pipeline-history.jsonl").write_text("{broken\n")
    models_dir = tmp_path / ".architecture-models"
    models_dir.mkdir()
    (models_dir / "pipeline-report.md").write_text(
        "**Generated:** 2026-08-19T16:59:51Z\n**Total Duration:** 25ms\n"
    )

    assert load_pipeline_history(tmp_path)[0].run_id == "legacy-pipeline-report"


def test_serialized_contract_aliases_are_explicit_and_backward_compatible():
    record = _run("aliases")
    record.invocation = "architect_pipeline"
    record.parent_run_id = "parent-1"
    record.produced_artifacts = ["inventory.json"]

    data = record.to_dict()

    assert data["timestamp"] == record.started_at
    assert data["invoked_by"] == "architect_pipeline"
    assert data["parent"] == "parent-1"
    assert data["artifacts"] == ["inventory.json"]
    assert PipelineRunRecord.from_dict(data).parent_run_id == "parent-1"


def test_nested_records_serialize_parent_and_artifact_contract_aliases():
    record = _run("nested-aliases")
    record.components = [ComponentHistoryRecord(
        component_id="COMP-1", name="API", timestamp=record.started_at,
        invoked_by="pipeline", parent_run_id="parent-1", artifacts=["structure.yaml"],
    )]
    record.modules = [ModuleHistoryRecord(
        path="api.py", module="api", timestamp=record.started_at,
        invoked_by="observe", parent_run_id="parent-1", artifacts=["inventory.json"],
    )]

    data = record.to_dict()

    assert data["components"][0]["parent"] == "parent-1"
    assert data["components"][0]["artifacts"] == ["structure.yaml"]
    assert data["modules"][0]["parent"] == "parent-1"
    assert data["modules"][0]["artifacts"] == ["inventory.json"]


def test_finalize_appends_enriched_record_and_loader_returns_latest_revision(tmp_path):
    append_pipeline_history(tmp_path, _run("run-final"))

    finalize_pipeline_history(tmp_path, "run-final", [".architecture/inventory.json"])

    assert len((tmp_path / ".architecture" / "pipeline-history.jsonl").read_text().splitlines()) == 2
    records = load_pipeline_history(tmp_path)
    assert len(records) == 1
    assert records[0].run_id == "run-final"
    assert records[0].produced_artifacts == [".architecture/inventory.json"]
    assert records[0].revision == "final"


def test_finalize_enriches_component_and_module_artifacts(tmp_path):
    record = _run("run-nested-final")
    record.components = [ComponentHistoryRecord(
        component_id="COMP-1", name="API", files=["api.py"], modules=["api.py"]
    )]
    record.modules = [ModuleHistoryRecord(path="api.py", module="api", component_id="COMP-1")]
    append_pipeline_history(tmp_path, record)

    finalize_pipeline_history(tmp_path, record.run_id, [
        ".architecture/inventory.json", ".architecture/functional.yaml",
        ".architecture/specs/comp-1.yaml", ".architecture/contracts/comp-1.yaml",
    ])

    final = load_pipeline_history(tmp_path)[0]
    assert ".architecture/specs/comp-1.yaml" in final.components[0].artifacts
    assert ".architecture/contracts/comp-1.yaml" in final.components[0].artifacts
    assert ".architecture/functional.yaml" in final.components[0].artifacts
    assert final.modules[0].artifacts == [".architecture/inventory.json"]


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


def test_later_stages_map_produced_entities_and_counts_without_component_ids(tmp_path):
    (tmp_path / "users.py").write_text(
        "from fastapi import APIRouter\nrouter = APIRouter()\nMAX_USERS = 10\n"
        "@router.get('/users')\ndef list_users():\n    return []\n"
    )
    (tmp_path / "test_users.py").write_text(
        "from users import list_users\ndef test_list_users():\n    assert list_users() == []\n"
    )
    stages = {
        "observe": ObserveStage(), "infer": InferStage(), "allocate": AllocateStage(),
        "relate": RelateStage(), "specify": SpecifyStage(), "contract": ContractStage(),
    }

    PipelineCoordinator(stages).run_all(PipelineContext(
        repo_path=tmp_path, output_dir=tmp_path / ".architecture", invocation_source="library"
    ))

    record = load_pipeline_history(tmp_path)[0]
    component = next(item for item in record.components if "users.py" in item.files)
    assert component.component_id not in component.produced_entity_ids
    assert component.counts["capabilities"] >= 1
    assert component.counts["interfaces"] >= 1
    assert component.counts["contracts"] >= 1
    assert all(entity_id.startswith(("CAP-", "BEH-", "ACT-", "IF-", "REQ-"))
               for entity_id in component.produced_entity_ids)
    module = next(item for item in record.modules if item.path == "users.py")
    assert module.component_id not in module.produced_entity_ids
    assert set(module.produced_entity_ids).issubset(set(component.produced_entity_ids))
    assert any(entity_id.startswith("CAP-") for entity_id in module.produced_entity_ids)
    assert module.counts["functions"] == 1
    assert module.counts["constants"] == 1


def test_stage_summaries_describe_consumed_and_produced_typed_results(tmp_path):
    (tmp_path / "mod.py").write_text("def work():\n    return 1\n")
    stages = {"observe": ObserveStage(), "infer": InferStage()}

    PipelineCoordinator(stages).run_all(PipelineContext(
        repo_path=tmp_path, output_dir=tmp_path / ".architecture"
    ))

    infer = next(item for item in load_pipeline_history(tmp_path)[0].stages if item.name == "infer")
    assert infer.input_summary["observe"]["type"] == "Inventory"
    assert infer.input_summary["observe"]["counts"]["modules"] == 1
    assert infer.output_summary["type"] == "InferenceResult"
    assert "capabilities" in infer.output_summary["counts"]


def test_successful_history_append_failure_does_not_fail_pipeline(tmp_path, monkeypatch):
    def fail_append(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("architecture_model.pipeline.history.append_pipeline_history", fail_append)
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")

    results = PipelineCoordinator({"observe": ObserveStage()}).run_all(ctx)

    assert "observe" in results
    assert ctx.history_warnings == ["Pipeline history persistence failed: disk full"]


def test_cli_final_revision_contains_written_artifacts(tmp_path):
    from architecture_model.cli.main import main

    (tmp_path / "app.py").write_text("def run():\n    return 1\n")

    assert main(["pipeline", str(tmp_path), "--stage", "infer"]) == 0

    record = load_pipeline_history(tmp_path)[0]
    assert record.revision == "final"
    assert record.source == "CLI"
    assert set(record.produced_artifacts) >= {
        ".architecture/inventory.json",
        ".architecture/functional.yaml",
        ".architecture/context.md",
    }
