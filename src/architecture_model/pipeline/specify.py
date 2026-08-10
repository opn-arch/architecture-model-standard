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

        # Library API interfaces — detect public symbols consumed cross-component
        # Build per-component public symbols: comp_id -> {symbol_name: signature}
        comp_public: dict[str, dict[str, str]] = defaultdict(dict)
        # Map module dotted-style paths for import matching
        mod_path_to_comp: dict[str, str] = {}
        for mod in inventory.modules:
            comp_id = file_to_comp.get(mod.path, "")
            if not comp_id:
                continue
            # Build a dotted key from the file path stem for import matching
            stem = mod.path.stem
            parts = list(mod.path.parts)
            mod_path_to_comp[str(mod.path)] = comp_id
            for func in mod.functions:
                if not func.name.startswith("_"):
                    comp_public[comp_id][func.name] = func.signature or f"{func.name}()"
            for cls in mod.classes:
                if not cls.name.startswith("_"):
                    comp_public[comp_id][cls.name] = f"class {cls.name}"

        # Check cross-component consumption via import edges
        # comp_id -> set of symbols consumed by OTHER components
        comp_consumed: dict[str, set[str]] = defaultdict(set)
        for edge in inventory.edges:
            src_comp = file_to_comp.get(edge.source, "")
            tgt_comp = file_to_comp.get(edge.target, "")
            if src_comp and tgt_comp and src_comp != tgt_comp:
                # src imports from tgt — tgt's symbols are consumed
                for sym in edge.symbols:
                    if sym in comp_public.get(tgt_comp, {}):
                        comp_consumed[tgt_comp].add(sym)

        # Also check via raw import strings when edges are not populated
        if not inventory.edges:
            # Build dotted-path -> comp_id for import matching
            # e.g. Path("auth/core.py") -> "auth.core" -> COMP-AUTH
            dotted_to_comp: dict[str, str] = {}
            for mod in inventory.modules:
                cid = file_to_comp.get(mod.path, "")
                if cid:
                    # Convert path to dotted module name
                    p = mod.path.with_suffix("")
                    dotted = ".".join(p.parts)
                    dotted_to_comp[dotted] = cid
                    # Also register just the stem for simple imports
                    dotted_to_comp[mod.path.stem] = cid
            for mod in inventory.modules:
                src_comp = file_to_comp.get(mod.path, "")
                if not src_comp:
                    continue
                for imp in mod.imports:
                    # imp is a dotted module path like "auth.core"
                    # Try exact match, then progressively shorter prefixes
                    tgt_comp = dotted_to_comp.get(imp, "")
                    if not tgt_comp:
                        # Try base module name
                        base = imp.split(".")[0]
                        tgt_comp = dotted_to_comp.get(base, "")
                    if tgt_comp and tgt_comp != src_comp:
                        # Mark all public symbols of target as consumed
                        for sym in comp_public.get(tgt_comp, {}):
                            comp_consumed[tgt_comp].add(sym)

        # Emit one library interface per component with >=3 consumed public symbols
        for comp_id, consumed in comp_consumed.items():
            if len(consumed) >= 3:
                iface_counter += 1
                methods = sorted(
                    f"{sym}: {comp_public[comp_id][sym]}"
                    for sym in consumed
                    if sym in comp_public[comp_id]
                )
                interfaces.append(InterfaceSpec(
                    id=f"IF-{iface_counter}",
                    name=f"{comp_id} Library API",
                    component_id=comp_id,
                    interface_type="library",
                    methods=methods,
                    description=f"{len(consumed)} public symbols consumed by other components",
                ))

        result = SpecifyResult(interfaces=interfaces)

        # Quality: % of components with at least one interface
        comp_ids = {c.id for c in allocation.components}
        comps_with_iface = {i.component_id for i in interfaces}
        coverage = len(comps_with_iface) / max(len(comp_ids), 1)
        score = max(50, int(coverage * 100))

        quality = QualityMetrics(
            score=score,
            sub_scores={
                "interface_count": float(len(interfaces)),
                "rest_count": float(sum(1 for i in interfaces if i.interface_type == "rest")),
                "cli_count": float(sum(1 for i in interfaces if i.interface_type == "cli")),
                "library_count": float(sum(1 for i in interfaces if i.interface_type == "library")),
                "component_coverage": round(coverage, 2),
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
