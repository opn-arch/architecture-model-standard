"""Tests for the decompose pipeline stage."""
from pathlib import Path

import pytest

from architecture_model.pipeline.allocate_types import AllocationResult, ComponentAllocation
from architecture_model.pipeline.decompose import DecomposeStage, FULL_SYSTEM_FILE_THRESHOLD
from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.protocol import PipelineContext, QualityMetrics, StageResult
from architecture_model.pipeline.relate_types import DerivedRelationship, RelateResult


def _make_ctx(components, relationships=None):
    """Build a PipelineContext with allocate and relate results pre-cached."""
    ctx = PipelineContext(repo_path=Path("/tmp/test"), output_dir=Path("/tmp/out"))
    ctx.cache["allocate"] = StageResult(
        output=AllocationResult(components=components),
        quality=QualityMetrics(score=100.0),
    )
    ctx.cache["relate"] = StageResult(
        output=RelateResult(relationships=relationships or []),
        quality=QualityMetrics(score=100.0),
    )
    return ctx


# --- Dataclass construction ---

class TestTypes:
    def test_system_boundary_defaults(self):
        sb = SystemBoundary(system_id="SYS-x", name="X")
        assert sb.component_ids == []
        assert sb.files == []
        assert sb.complexity == 0.0
        assert sb.is_full_system is True

    def test_decompose_result_defaults(self):
        dr = DecomposeResult()
        assert dr.systems == []
        assert dr.inline_components == []
        assert dr.inter_system_edges == []


# --- Stage metadata ---

class TestStageMetadata:
    def test_name_version_requires(self):
        stage = DecomposeStage()
        assert stage.name == "decompose"
        assert stage.version == "1.0"
        assert stage.requires == ["allocate", "relate", "specify"]

    def test_can_run_requires_both(self):
        stage = DecomposeStage()
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
        assert stage.can_run(ctx) is False

        ctx.cache["allocate"] = StageResult(output=None, quality=QualityMetrics(score=0))
        assert stage.can_run(ctx) is False

        ctx.cache["relate"] = StageResult(output=None, quality=QualityMetrics(score=0))
        assert stage.can_run(ctx) is False

        ctx.cache["specify"] = StageResult(output=None, quality=QualityMetrics(score=0))
        assert stage.can_run(ctx) is True

    def test_output_path(self):
        stage = DecomposeStage()
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp/out"))
        assert stage.output_path(ctx) == Path("/tmp/out/decompose.yaml")


# --- Run behavior ---

class TestDecomposeRun:
    def test_mixed_large_and_small(self):
        """Large components become systems, small ones become inline."""
        large = ComponentAllocation(
            id="COMP-1", name="Core",
            files=[Path(f"f{i}.py") for i in range(6)],
        )
        small = ComponentAllocation(
            id="COMP-2", name="Utils",
            files=[Path("u1.py"), Path("u2.py")],
        )
        ctx = _make_ctx([large, small])
        result = DecomposeStage().run(ctx)

        assert len(result.output.systems) == 1
        assert result.output.systems[0].system_id == "SYS-core"
        assert result.output.systems[0].is_full_system is True
        assert len(result.output.inline_components) == 1
        assert result.output.inline_components[0].system_id == "SYS-utils"
        assert result.output.inline_components[0].is_full_system is False
        assert result.quality.score == 100.0

    def test_inter_system_edges(self):
        """Cross-component relationships produce inter-system edges."""
        c1 = ComponentAllocation(id="C1", name="A", files=[Path(f"a{i}.py") for i in range(5)])
        c2 = ComponentAllocation(id="C2", name="B", files=[Path(f"b{i}.py") for i in range(5)])
        rels = [DerivedRelationship(from_id="C1", to_id="C2", rel_type="depends-on")]
        ctx = _make_ctx([c1, c2], rels)
        result = DecomposeStage().run(ctx)

        assert len(result.output.inter_system_edges) == 1
        assert result.output.inter_system_edges[0] == ("SYS-a", "SYS-b", "depends-on")

    def test_intra_component_rel_no_edge(self):
        """Relationship within same component produces no inter-system edge."""
        c1 = ComponentAllocation(id="C1", name="A", files=[Path(f"a{i}.py") for i in range(5)])
        rels = [DerivedRelationship(from_id="C1", to_id="C1", rel_type="contains")]
        ctx = _make_ctx([c1], rels)
        result = DecomposeStage().run(ctx)

        assert result.output.inter_system_edges == []

    def test_all_small_components_warning(self):
        """When no components are large enough, a warning diagnostic is emitted."""
        small = ComponentAllocation(id="C1", name="Tiny", files=[Path("x.py")])
        ctx = _make_ctx([small])
        result = DecomposeStage().run(ctx)

        assert len(result.output.systems) == 0
        assert len(result.output.inline_components) == 1
        assert result.quality.score == 50.0
        assert any(d.code == "NO_SYSTEMS" for d in result.diagnostics)

    def test_single_large_component(self):
        """Single large component becomes one system."""
        c = ComponentAllocation(id="C1", name="Mono", files=[Path(f"m{i}.py") for i in range(10)])
        ctx = _make_ctx([c])
        result = DecomposeStage().run(ctx)

        assert len(result.output.systems) == 1
        assert result.output.systems[0].complexity == 10.0
        assert result.output.systems[0].files == [f"m{i}.py" for i in range(10)]
        assert result.diagnostics == []

    def test_threshold_boundary(self):
        """Exactly FULL_SYSTEM_FILE_THRESHOLD files → full system."""
        c = ComponentAllocation(
            id="C1", name="Edge",
            files=[Path(f"e{i}.py") for i in range(FULL_SYSTEM_FILE_THRESHOLD)],
        )
        ctx = _make_ctx([c])
        result = DecomposeStage().run(ctx)
        assert len(result.output.systems) == 1

        # One less → inline
        c2 = ComponentAllocation(
            id="C2", name="Under",
            files=[Path(f"u{i}.py") for i in range(FULL_SYSTEM_FILE_THRESHOLD - 1)],
        )
        ctx2 = _make_ctx([c2])
        result2 = DecomposeStage().run(ctx2)
        assert len(result2.output.systems) == 0
        assert len(result2.output.inline_components) == 1

    def test_name_with_spaces(self):
        """Component names with spaces get hyphenated in system_id."""
        c = ComponentAllocation(id="C1", name="My Component", files=[Path(f"f{i}.py") for i in range(5)])
        ctx = _make_ctx([c])
        result = DecomposeStage().run(ctx)
        assert result.output.systems[0].system_id == "SYS-my-component"

    def test_duration_ms_set(self):
        ctx = _make_ctx([])
        result = DecomposeStage().run(ctx)
        assert result.duration_ms >= 0
