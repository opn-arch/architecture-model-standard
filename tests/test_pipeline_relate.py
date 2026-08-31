"""Tests for RelateStage."""

import pytest

from architecture_model.pipeline.infer_types import InferredCapability
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
