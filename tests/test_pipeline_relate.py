"""Tests for RelateStage."""

import pytest
from pathlib import Path

from architecture_model.pipeline.infer_types import InferenceResult, InferredCapability
from architecture_model.pipeline.allocate_types import AllocationResult, ComponentAllocation
from architecture_model.pipeline.observe_types import Inventory
from architecture_model.pipeline.protocol import QualityMetrics, StageResult
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.protocol import PipelineContext


class TestRelateStage:
    def test_capability_hierarchy_contains(self, tmp_path):
        """Capabilities with sub_capabilities should get contains relationships."""
        (tmp_path / "core.py").write_text("def validate(): pass\ndef parse(): pass\n")

        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")

        # Run prerequisite stages
        obs = ObserveStage().run(ctx)
        ctx.cache["observe"] = obs

        infer_result = InferStage().run(ctx)

        # Ensure we have a parent capability and add a child
        if not infer_result.output.capabilities:
            parent = InferredCapability(id="CAP-1", name="Core")
            infer_result.output.capabilities.append(parent)
        else:
            parent = infer_result.output.capabilities[0]

        child = InferredCapability(id="CAP-SUB-1", name="Sub Cap", description="A sub cap")
        infer_result.output.capabilities.append(child)
        parent.sub_capabilities = ["CAP-SUB-1"]

        ctx.cache["infer"] = infer_result

        alloc_result = AllocateStage().run(ctx)
        ctx.cache["allocate"] = alloc_result

        relate_result = RelateStage().run(ctx)

        contains_rels = [
            r
            for r in relate_result.output.relationships
            if r.rel_type == "contains" and r.to_id == "CAP-SUB-1"
        ]
        assert len(contains_rels) >= 1, "Should have contains relationship for sub_capabilities"
        assert contains_rels[0].from_id == parent.id

    def test_route_component_realizes_aggregate_and_leaf_capabilities(self, tmp_path):
        route_file = "app/routers/users.py"
        capabilities = [
            InferredCapability(id="CAP-ROUTES", name="Web Routes", evidence_source="routes", source_files=[route_file]),
            InferredCapability(id="CAP-USERS", name="User Management", evidence_source="routes", source_files=[route_file]),
        ]
        component = ComponentAllocation(
            id="COMP-1", name="Users", capability_id="CAP-USERS", files=[Path(route_file)]
        )
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(Inventory(), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(InferenceResult(capabilities=capabilities), QualityMetrics(100))
        ctx.cache["allocate"] = StageResult(AllocationResult(components=[component]), QualityMetrics(100))

        result = RelateStage().run(ctx)
        realizes = {(r.from_id, r.to_id) for r in result.output.relationships if r.rel_type == "realizes"}

        assert realizes == {("COMP-1", "CAP-ROUTES"), ("COMP-1", "CAP-USERS")}
        assert all(r.from_id == "COMP-1" for r in result.output.relationships if r.rel_type == "realizes")

    def test_aggregate_route_capability_is_realized_by_every_route_owner(self, tmp_path):
        capabilities = [
            InferredCapability(
                id="CAP-ROUTES",
                name="Web Routes",
                evidence_source="routes",
                source_files=["routers/users.py", "routers/projects.py"],
            )
        ]
        components = [
            ComponentAllocation(id="COMP-1", name="Users", files=[Path("routers/users.py")]),
            ComponentAllocation(id="COMP-2", name="Projects", files=[Path("routers/projects.py")]),
        ]
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(Inventory(), QualityMetrics(100))
        ctx.cache["infer"] = StageResult(InferenceResult(capabilities=capabilities), QualityMetrics(100))
        ctx.cache["allocate"] = StageResult(AllocationResult(components=components), QualityMetrics(100))

        result = RelateStage().run(ctx)

        assert {
            r.from_id for r in result.output.relationships
            if r.rel_type == "realizes" and r.to_id == "CAP-ROUTES"
        } == {"COMP-1", "COMP-2"}
