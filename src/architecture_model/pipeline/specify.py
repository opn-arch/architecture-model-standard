"""Specify pipeline stage — derives interface specifications from routes and exports."""
from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from .allocate_types import AllocationResult
from .observe_types import Inventory, RouteRecord
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from .specify_types import InterfaceSpec, SpecifyResult


class SpecifyStage:
    """Derives interface specifications from observed routes and module exports."""

    name: str = "specify"
    requires: list[str] = ["observe", "allocate"]

    def run(self, ctx: PipelineContext) -> StageResult[SpecifyResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        observe_result = ctx.get("observe")
        allocate_result = ctx.get("allocate")
        if not all([observe_result, allocate_result]):
            raise RuntimeError("specify requires observe and allocate")

        inventory: Inventory = observe_result.output
        allocation: AllocationResult = allocate_result.output

        interfaces: list[InterfaceSpec] = []
        iface_counter = 0

        # Build file→comp map
        file_to_comp: dict[Path, str] = {}
        for comp in allocation.components:
            for f in comp.files:
                file_to_comp[f] = comp.id

        # Group routes by component
        comp_routes: dict[str, list[RouteRecord]] = defaultdict(list)
        for route in inventory.routes:
            comp_id = file_to_comp.get(route.file, "")
            if comp_id:
                comp_routes[comp_id].append(route)

        # One REST interface per component with routes
        for comp_id, routes in comp_routes.items():
            iface_counter += 1
            methods = [f"{r.method} {r.path}" for r in routes]
            interfaces.append(InterfaceSpec(
                id=f"IF-{iface_counter}",
                name=f"{comp_id} REST API",
                component_id=comp_id,
                interface_type="rest",
                methods=methods,
                description=f"{len(routes)} endpoints",
            ))

        # CLI interfaces
        for mod in inventory.modules:
            has_cli = any("click" in imp or "typer" in imp or "argparse" in imp for imp in mod.imports)
            if has_cli:
                comp_id = file_to_comp.get(mod.path, "")
                if comp_id:
                    iface_counter += 1
                    interfaces.append(InterfaceSpec(
                        id=f"IF-{iface_counter}",
                        name=f"{mod.path.stem} CLI",
                        component_id=comp_id,
                        interface_type="cli",
                    ))

        result = SpecifyResult(interfaces=interfaces)

        quality = QualityMetrics(
            score=100 if interfaces else 50,
            sub_scores={
                "interface_count": float(len(interfaces)),
                "rest_count": float(sum(1 for i in interfaces if i.interface_type == "rest")),
                "cli_count": float(sum(1 for i in interfaces if i.interface_type == "cli")),
            },
            thresholds={},
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(inventory.routes)),
            duration_ms=duration_ms,
            version="1.0",
        )
