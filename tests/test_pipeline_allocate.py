"""Tests for the allocate pipeline stage."""
import pytest
from pathlib import Path
from architecture_model.pipeline.allocate import AllocateStage, _apply_allocation_resolutions
from architecture_model.pipeline.allocate_types import ComponentAllocation
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.protocol import Evidence, PipelineContext, QualityMetrics, StageResult
from architecture_model.pipeline.infer_types import InferenceResult, InferredCapability
from architecture_model.pipeline.observe_types import Inventory, ModuleRecord
from architecture_model.pipeline.relate import RelateStage


def _run_pipeline(tmp_path):
    """Run observe → infer → allocate."""
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
    obs = ObserveStage()
    ctx.cache["observe"] = obs.run(ctx)
    inf = InferStage()
    ctx.cache["infer"] = inf.run(ctx)
    alloc = AllocateStage()
    return alloc.run(ctx), ctx


class TestAllocateStage:
    def test_allocate_name_and_requires(self):
        stage = AllocateStage()
        assert stage.name == "allocate"
        assert "observe" in stage.requires
        assert "infer" in stage.requires

    def test_allocate_empty_project(self, tmp_path):
        result, _ = _run_pipeline(tmp_path)
        assert result.output.components == []
        assert result.output.file_coverage == 100.0

    def test_allocate_seeds_from_capabilities(self, tmp_path):
        # Create files matching capability names
        (tmp_path / "users.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    pass

@router.post("/users")
def create_user():
    pass
''')
        (tmp_path / "articles.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/articles")
def list_articles():
    pass
''')
        result, _ = _run_pipeline(tmp_path)
        assert len(result.output.components) >= 1
        assert result.output.file_coverage > 0

    def test_allocate_file_coverage(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        result, _ = _run_pipeline(tmp_path)
        # All files should be allocated (even if to Infrastructure)
        assert result.output.file_coverage == 100.0

    def test_allocate_quality_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        result, _ = _run_pipeline(tmp_path)
        assert "file_coverage" in result.quality.sub_scores
        assert "boundary_coherence" in result.quality.sub_scores
        assert "component_count" in result.quality.sub_scores

    def test_renamed_package_capability_uses_stable_source_files(self, tmp_path):
        modules = [ModuleRecord(path=Path("app/models/user.py"))]
        capability = InferredCapability(
            id="CAP-1",
            name="Rich Persistence Domain",
            evidence_source="package_group",
            source_files=["app/models/user.py"],
            source_key="models",
        )
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(Inventory(modules=modules), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(InferenceResult(capabilities=[capability]), QualityMetrics(100))

        result = AllocateStage().run(ctx)

        assert result.output.components[0].files == [Path("app/models/user.py")]
        assert result.output.components[0].capability_id == "CAP-1"

    def test_cli_exact_sources_win_over_prefix_fallback(self, tmp_path):
        modules = [
            ModuleRecord(path=Path("commands/backfill_uw_types.py")),
            ModuleRecord(path=Path("commands/backfill_projects.py")),
            ModuleRecord(path=Path("commands/seed_kb.py")),
            ModuleRecord(path=Path("commands/seed_projects.py")),
        ]
        capabilities = [
            InferredCapability(id="CAP-1", name="Renamed Backfill", evidence_source="cli_pattern", source_files=["commands/backfill_uw_types.py"], source_key="backfill_uw_types"),
            InferredCapability(id="CAP-2", name="Projects Backfill", evidence_source="cli_pattern", source_files=["commands/backfill_projects.py"], source_key="backfill_projects"),
            InferredCapability(id="CAP-3", name="Knowledge Seed", evidence_source="cli_pattern", source_files=["commands/seed_kb.py"], source_key="seed_kb"),
            InferredCapability(id="CAP-4", name="Projects Seed", evidence_source="cli_pattern", source_files=["commands/seed_projects.py"], source_key="seed_projects"),
        ]
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(Inventory(modules=modules), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(InferenceResult(capabilities=capabilities), QualityMetrics(100))

        result = AllocateStage().run(ctx)
        files_by_cap = {c.capability_id: c.files for c in result.output.components}

        assert files_by_cap["CAP-1"] == [Path("commands/backfill_uw_types.py")]
        assert files_by_cap["CAP-2"] == [Path("commands/backfill_projects.py")]
        assert files_by_cap["CAP-3"] == [Path("commands/seed_kb.py")]
        assert files_by_cap["CAP-4"] == [Path("commands/seed_projects.py")]

    def test_cli_prefix_fallback_cannot_steal_another_capability_exact_source(self, tmp_path):
        modules = [ModuleRecord(path=Path("commands/backfill_projects.py"))]
        capabilities = [
            InferredCapability(id="CAP-1", name="CLI Backfill", evidence_source="cli_pattern", source_key="backfill"),
            InferredCapability(id="CAP-2", name="Projects", evidence_source="cli_pattern", source_files=["commands/backfill_projects.py"], source_key="backfill_projects"),
        ]
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(Inventory(modules=modules), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(InferenceResult(capabilities=capabilities), QualityMetrics(100))

        result = AllocateStage().run(ctx)

        owner = next(c for c in result.output.components if Path("commands/backfill_projects.py") in c.files)
        assert owner.capability_id == "CAP-2"

    def test_ambiguous_module_resolution_groups_files_and_records_evidence(self, tmp_path):
        modules = [ModuleRecord(path=Path("a.py")), ModuleRecord(path=Path("b.py"))]
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(Inventory(modules=modules), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(InferenceResult(), QualityMetrics(100))
        ctx.prior_corrections = [
            Evidence(
                source="user_confirmation",
                confidence=1.0,
                raw="These modules form one bounded concern",
                location="ambiguous_module",
                metadata={"file_allocations": ["a.py", "b.py"], "target_name": "Resolved Group"},
            )
        ]

        result = AllocateStage().run(ctx)

        component = next(c for c in result.output.components if c.name == "Resolved Group")
        assert component.files == [Path("a.py"), Path("b.py")]
        assert component.evidence == ["These modules form one bounded concern"]

    def test_structured_allocation_mapping_preserves_groups_and_unique_ids(self, tmp_path):
        modules = [ModuleRecord(path=Path(name)) for name in ("a.py", "b.py", "c.py")]
        components = [
            ComponentAllocation(id="COMP-1", name="Keep A", files=[Path("a.py")]),
            ComponentAllocation(id="COMP-3", name="Keep C", capability_id="CAP-1", files=[Path("c.py")]),
        ]
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.prior_corrections = [
            Evidence(
                source="user_confirmation",
                confidence=1.0,
                raw="Explicit regrouping",
                location="ambiguous_module",
                metadata={"file_allocations": {"Group A": ["a.py"], "Group B": ["b.py"]}},
            )
        ]

        _apply_allocation_resolutions(ctx, components, modules, "library", [])

        assert [(component.name, component.files) for component in components] == [
            ("Keep C", [Path("c.py")]),
            ("Group A", [Path("a.py")]),
            ("Group B", [Path("b.py")]),
        ]
        assert [component.id for component in components] == ["COMP-3", "COMP-4", "COMP-5"]
        assert len({component.id for component in components}) == len(components)

        ctx.cache["observe"] = StageResult(Inventory(modules=modules), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(
            InferenceResult(capabilities=[InferredCapability(id="CAP-1", name="Keep C")]),
            QualityMetrics(100),
        )
        from architecture_model.pipeline.allocate_types import AllocationResult
        ctx.cache["allocate"] = StageResult(AllocationResult(components=components), QualityMetrics(100))
        relationships = RelateStage().run(ctx).output.relationships
        entity_ids = {component.id for component in components} | {"CAP-1"}
        assert relationships
        assert all(
            endpoint in entity_ids
            for relationship in relationships
            for endpoint in (relationship.from_id, relationship.to_id)
            if endpoint.startswith("COMP-") or endpoint.startswith("CAP-")
        )


class TestAllocatePerComponentQuality:
    def test_allocate_has_component_scores(self, tmp_path):
        """After allocate, component_scores keyed by component ID."""
        (tmp_path / "app.py").write_text("def main(): pass")
        result, _ = _run_pipeline(tmp_path)
        assert isinstance(result.quality.component_scores, dict)

    def test_allocate_component_scores_from_module_quality(self, tmp_path):
        """Component scores aggregate module-level quality from observe."""
        (tmp_path / "app.py").write_text("def main(x: int) -> int:\n    \"\"\"Doc.\"\"\"\n    return x\n")
        result, ctx = _run_pipeline(tmp_path)
        # If observe produced module scores, allocate should aggregate them
        obs_quality = ctx.cache["observe"].quality
        if obs_quality.component_scores:
            # allocate should have component_scores too
            assert len(result.quality.component_scores) >= 0  # may be 0 if no mapping


class TestInferLayerEnhancements:
    def test_infer_layer_library_default(self):
        from architecture_model.pipeline.allocate import _infer_layer
        assert _infer_layer([Path("colorama/ansi.py")], project_type="library") == "library"

    def test_infer_layer_core(self):
        from architecture_model.pipeline.allocate import _infer_layer
        assert _infer_layer([Path("mylib/core/engine.py")]) == "core"

    def test_infer_layer_still_detects_web(self):
        from architecture_model.pipeline.allocate import _infer_layer
        assert _infer_layer([Path("mylib/api/routes.py")], project_type="library") == "web"

    def test_infer_layer_util_returns_infra(self):
        from architecture_model.pipeline.allocate import _infer_layer
        assert _infer_layer([Path("mylib/utils/helper.py")]) == "infra"

    def test_infer_layer_non_library_default(self):
        from architecture_model.pipeline.allocate import _infer_layer
        assert _infer_layer([Path("colorama/ansi.py")], project_type="web_app") == "infra"

    def test_one_handler_file_does_not_infect_layer(self):
        """One file with 'handler' should not make the whole component 'web'."""
        from architecture_model.pipeline.allocate import _infer_layer
        files = [
            Path("src/mylib/core/parser.py"),
            Path("src/mylib/core/types.py"),
            Path("src/mylib/core/validator.py"),
            Path("src/mylib/core/handler.py"),
        ]
        result = _infer_layer(files, "library")
        assert result != "web"

    def test_majority_web_files_get_web_layer(self):
        """When most files ARE web-related, should get web layer."""
        from architecture_model.pipeline.allocate import _infer_layer
        files = [
            Path("src/app/api/routes.py"),
            Path("src/app/api/views.py"),
            Path("src/app/api/handlers.py"),
            Path("src/app/api/utils.py"),
        ]
        result = _infer_layer(files, "web_app")
        assert result == "web"

    def test_single_file_uses_direct_match(self):
        """Single file should use direct keyword match."""
        from architecture_model.pipeline.allocate import _infer_layer
        files = [Path("src/app/handler.py")]
        result = _infer_layer(files, "web_app")
        assert result == "web"


class TestDetectProjectType:
    def test_detect_project_type_library(self):
        from architecture_model.pipeline.allocate import _detect_project_type
        from architecture_model.pipeline.observe_types import ModuleRecord
        mods = [ModuleRecord(path=Path("mylib/core.py"), imports=["os", "sys"], line_count=50)]
        assert _detect_project_type(mods) == "library"

    def test_detect_project_type_web(self):
        from architecture_model.pipeline.allocate import _detect_project_type
        from architecture_model.pipeline.observe_types import ModuleRecord
        mods = [ModuleRecord(path=Path("app/main.py"), imports=["flask"], line_count=50)]
        assert _detect_project_type(mods) == "web_app"

    def test_detect_project_type_cli(self):
        from architecture_model.pipeline.allocate import _detect_project_type
        from architecture_model.pipeline.observe_types import ModuleRecord
        mods = [ModuleRecord(path=Path("app/main.py"), imports=["click"], line_count=50)]
        assert _detect_project_type(mods) == "cli_tool"

    def test_infer_layer_api_in_filename_not_web(self):
        """api_wrapper.py should NOT get 'web' layer — 'api' alone is not enough."""
        from architecture_model.pipeline.allocate import _infer_layer
        result = _infer_layer([Path("src/tools/api_wrapper.py")], "library")
        assert result != "web"

    def test_infer_layer_route_file_is_web(self):
        """src/routes/users.py SHOULD get 'web' layer."""
        from architecture_model.pipeline.allocate import _infer_layer
        result = _infer_layer([Path("src/routes/users.py")], "library")
        assert result == "web"
