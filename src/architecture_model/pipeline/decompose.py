"""Decompose stage — detect system boundaries from allocated components."""
from __future__ import annotations

import time

from architecture_model.pipeline.allocate_types import AllocationResult
from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
)
from architecture_model.pipeline.relate_types import RelateResult

FULL_SYSTEM_FILE_THRESHOLD = 5  # components with >= this many files become autonomous systems


class DecomposeStage:
    name = "decompose"
    version = "1.0"
    requires = ["allocate", "relate", "specify"]

    def can_run(self, ctx: PipelineContext) -> bool:
        return ctx.has("allocate") and ctx.has("relate") and ctx.has("specify")

    def output_path(self, ctx: PipelineContext):
        return ctx.output_dir / "decompose.yaml"

    def run(self, ctx: PipelineContext) -> StageResult[DecomposeResult]:
        t0 = time.monotonic()

        alloc: AllocationResult = ctx.get("allocate").output
        rels: RelateResult = ctx.get("relate").output

        systems: list[SystemBoundary] = []
        inlines: list[SystemBoundary] = []
        comp_to_sys: dict[str, str] = {}

        for comp in alloc.components:
            is_full = len(comp.files) >= FULL_SYSTEM_FILE_THRESHOLD
            sys_id = f"SYS-{comp.name.lower().replace(' ', '-')}"
            sb = SystemBoundary(
                system_id=sys_id,
                name=comp.name,
                component_ids=[comp.id],
                files=[str(f) for f in comp.files],
                complexity=float(len(comp.files)),
                is_full_system=is_full,
            )
            if is_full:
                systems.append(sb)
            else:
                inlines.append(sb)
            comp_to_sys[comp.id] = sys_id

        # Build inter-system edges from cross-component relationships
        inter_edges: list[tuple[str, str, str]] = []
        for rel in rels.relationships:
            from_sys = comp_to_sys.get(rel.from_id)
            to_sys = comp_to_sys.get(rel.to_id)
            if from_sys and to_sys and from_sys != to_sys:
                inter_edges.append((from_sys, to_sys, rel.rel_type))

        result = DecomposeResult(
            systems=systems,
            inline_components=inlines,
            inter_system_edges=inter_edges,
        )

        duration = int((time.monotonic() - t0) * 1000)
        diagnostics: list[Diagnostic] = []
        if not systems:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="NO_SYSTEMS",
                    message="No components large enough to be autonomous systems",
                )
            )

        quality = QualityMetrics(
            score=100.0 if systems else 50.0,
            sub_scores={"system_count": float(len(systems)), "inline_count": float(len(inlines))},
        )

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=[],
            duration_ms=duration,
        )
