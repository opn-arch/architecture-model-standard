"""End-to-end coverage for semantic pipeline propagation."""

import yaml

from architecture_model.core.parser import load_model
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.cache import PipelineCache
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


def test_logs_db_like_pipeline_realizes_all_evidenced_capabilities(tmp_path):
    for package_name in ("models", "routers", "schemas", "services", "alembic"):
        package = tmp_path / "src" / "app" / package_name
        package.mkdir(parents=True)
        for index in range(11):
            path = package / f"item_{index}.py"
            if package_name == "routers":
                path.write_text(
                    "from fastapi import APIRouter\n"
                    "router = APIRouter()\n\n"
                    f"@router.get('/items/{index}')\n"
                    f"def get_item_{index}():\n    return {{'id': {index}}}\n"
                )
            else:
                path.write_text(f"def handle_{package_name}_{index}():\n    return {index}\n")

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
    _coordinator().run_to("validate", ctx)

    issues = ctx.get("validate").output.issues
    assert not [issue for issue in issues if issue.rule == "capability_realization"]
    assert ctx.get("validate").output.score == 100


def test_real_pipeline_preserves_se_fields_and_rich_requirements(tmp_path):
    package = tmp_path / "jobs"
    package.mkdir()
    (package / "jobs.py").write_text(
        '"""Process queued jobs reliably."""\n'
        "import logging\n\n"
        "TIMEOUT_SECONDS = 30\n"
        "MAX_BATCH = 100\n"
        "BATCH_SIZE = 25\n\n"
        "def process_jobs():\n"
        "    logging.info('processing')\n\n"
        "def retry_failed_jobs():\n"
        "    raise RuntimeError('failed')\n"
    )
    for index in range(7):
        (package / f"worker_{index}.py").write_text(
            f"from .jobs import process_jobs\n\ndef run_worker_{index}():\n    return process_jobs()\n"
        )
    scheduler = tmp_path / "scheduler"
    scheduler.mkdir()
    (scheduler / "scheduler.py").write_text(
        '"""Schedule enough workers."""\nMIN_WORKERS = 4\n\ndef schedule_workers():\n    return MIN_WORKERS\n'
    )
    for index in range(7):
        (scheduler / f"queue_{index}.py").write_text(
            f"from .scheduler import schedule_workers\n\ndef run_queue_{index}():\n    return schedule_workers()\n"
        )

    output_dir = tmp_path / ".architecture"
    ctx = PipelineContext(repo_path=tmp_path, output_dir=output_dir)
    coordinator = _coordinator()
    coordinator.run_to("validate", ctx)

    disk_cache = PipelineCache(output_dir / "pipeline-cache")
    for stage_name in ("infer", "specify"):
        disk_cache.save_stage(stage_name, ctx.cache[stage_name])
        ctx.cache[stage_name] = disk_cache.load_stage(stage_name)

    components = ctx.get("allocate").output.components
    jobs_boundary = SystemBoundary(
        system_id="SYS-jobs",
        name="Jobs",
        component_ids=[component.id for component in components],
        files=[
            str(path.relative_to(tmp_path)) for path in sorted(package.glob("*.py"))
        ],
        is_full_system=True,
    )
    scheduler_boundary = SystemBoundary(
        system_id="SYS-scheduler",
        name="Scheduler",
        component_ids=[component.id for component in components],
        files=[
            str(path.relative_to(tmp_path)) for path in sorted(scheduler.glob("*.py"))
        ],
        is_full_system=True,
    )
    ctx.cache["decompose"] = StageResult(
        output=DecomposeResult(systems=[jobs_boundary, scheduler_boundary]),
        quality=QualityMetrics(score=100.0),
    )
    ctx.config["coordinator"] = coordinator
    ctx.cache["synthesize"] = SynthesizeStage().run(ctx)
    (tmp_path / ".architecture-model.yaml").write_text(
        "meta:\n"
        "  schema_version: '2.0'\n"
        "  project: jobs\n"
        "entities:\n"
        "  components:\n"
        "  - id: COMP-1\n"
        "    name: Jobs\n"
        "    status: ACTIVE\n"
        "    files: [jobs/jobs.py]\n"
        "  capabilities:\n"
        "  - id: CAP-1\n"
        "    name: Jobs\n"
        "    status: ACTIVE\n"
        "    moes: [Existing effectiveness measure]\n"
        "    requirements: [Existing capability requirement]\n"
        "    trade_offs: [Existing trade-off]\n"
        "relationships:\n"
        "- from: COMP-1\n"
        "  to: CAP-1\n"
        "  type: realizes\n"
    )
    emit_result = EmitStage().run(ctx)
    assert emit_result.output.promoted, emit_result.output.final_validation_issues

    emitted_dir = output_dir / ".architecture-models"
    models = [
        load_model(tmp_path / ".architecture-models" / "jobs" / ".architecture-model.yaml"),
        load_model(tmp_path / ".architecture-models" / "scheduler" / ".architecture-model.yaml"),
        load_model(tmp_path / ".architecture-model.yaml"),
    ]

    sos_model = models[-1]
    raw_sos = yaml.safe_load((tmp_path / ".architecture-model.yaml").read_text())
    all_ids = [
        entity["id"]
        for group in raw_sos["entities"].values()
        if isinstance(group, list)
        for entity in group
        if isinstance(entity, dict) and entity.get("id")
    ]
    assert len(all_ids) == len(set(all_ids))
    assert sos_model.entities.requirements == []
    assert sos_model.entities.capabilities == []
    assert sos_model.entities.behaviors == []
    assert sos_model.entities.components == []

    expected_tokens = [
        (models[0], ("TIMEOUT", "MAX_BATCH", "BATCH_SIZE"), "MIN_WORKERS"),
        (models[1], ("MIN_WORKERS",), "TIMEOUT"),
    ]
    for model, tokens, excluded_token in expected_tokens:
        threshold_requirements = [
            req
            for req in model.entities.requirements
            if any(token in req.name for token in tokens)
        ]
        assert len(threshold_requirements) == len(tokens)
        assert not any(excluded_token in req.name for req in model.entities.requirements)
        for requirement in threshold_requirements:
            assert requirement.text
            assert requirement.rationale
            assert requirement.moe
            assert requirement.moes
            assert requirement.value_function
            assert requirement.source_file
            assert requirement.source_doc
            assert requirement.priority
            assert requirement.extensions["source_type"] == "constant"
            assert requirement.content_hash

        assert len({req.content_hash for req in model.entities.requirements}) == len(
            model.entities.requirements
        )
        entity_ids = model.all_entity_ids
        requirement_ids = {req.id for req in threshold_requirements}
        satisfying = [
            rel
            for rel in model.relationships
            if rel.type.value == "satisfies" and rel.to_id in requirement_ids
        ]
        assert satisfying
        assert all(
            rel.from_id in entity_ids and rel.to_id in entity_ids
            for rel in model.relationships
        )

    assert len(sos_model.entities.systems) == 2
    assert all(system.sub_model_ref for system in sos_model.entities.systems)
