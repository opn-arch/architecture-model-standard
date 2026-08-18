"""Tests for enrichment record creation in coordinator."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.protocol import (
    EnrichmentRecord,
    PipelineContext,
    QualityMetrics,
    StageResult,
)


@dataclass
class FakeCap:
    id: str = "CAP-1"
    name: str = "Utils"
    evidence_source: str = "src/utils.py"


@dataclass
class FakeInferResult:
    capabilities: list = field(default_factory=list)


@dataclass
class FakeComp:
    id: str = "COMP-1"
    name: str = "Svc"
    files: list = field(default_factory=list)


@dataclass
class FakeAllocResult:
    components: list = field(default_factory=list)


@pytest.mark.asyncio
async def test_infer_enrichment_records():
    async def fake_llm(stage, prompt, context):
        return "Data Processing Engine"

    ctx = PipelineContext(
        repo_path=Path("/tmp"),
        output_dir=Path("/tmp/out"),
        llm_callback=fake_llm,
    )
    cap = FakeCap(id="CAP-1", name="Utils")
    result = StageResult(
        output=FakeInferResult(capabilities=[cap]),
        quality=QualityMetrics(score=0.8),
    )
    ctx.cache["infer"] = result

    coord = PipelineCoordinator(stages={})
    changes = await coord.enrich_stage_output("infer", ctx)

    assert len(changes) >= 1
    assert len(ctx.enrichment_log) == 1
    rec = ctx.enrichment_log[0]
    assert rec.entity_id == "CAP-1"
    assert rec.entity_type == "capability"
    assert rec.stage == "infer"
    assert rec.old_value == "Utils"
    assert rec.new_value == "Data Processing Engine"


@pytest.mark.asyncio
async def test_allocate_enrichment_records():
    async def fake_llm(stage, prompt, context):
        return "Authentication Service"

    ctx = PipelineContext(
        repo_path=Path("/tmp"),
        output_dir=Path("/tmp/out"),
        llm_callback=fake_llm,
    )
    comp = FakeComp(id="COMP-1", name="Svc", files=[Path("auth.py")])
    result = StageResult(
        output=FakeAllocResult(components=[comp]),
        quality=QualityMetrics(score=0.8),
    )
    ctx.cache["allocate"] = result

    coord = PipelineCoordinator(stages={})
    changes = await coord.enrich_stage_output("allocate", ctx)

    assert len(changes) >= 1
    assert len(ctx.enrichment_log) == 1
    rec = ctx.enrichment_log[0]
    assert rec.entity_id == "COMP-1"
    assert rec.entity_type == "component"
    assert rec.stage == "allocate"
