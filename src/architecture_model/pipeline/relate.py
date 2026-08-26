"""Relate pipeline stage — derives relationships between architecture entities.

Produces relationships: realizes (component→capability), depends-on (component→component),
contains (layer→component), exposes (component→interface from routes).
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from .allocate_types import AllocationResult, ComponentAllocation
from .infer_types import InferenceResult
from .observe_types import Inventory
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from .relate_types import DerivedRelationship, RelateResult


UTILITY_PATTERNS = {"utils", "helpers", "common", "shared", "lib", "support", "base"}


def _pick_relationship_type(target_layer: str, target_name: str) -> str:
    """Choose 'uses' for utility/infrastructure targets, 'depends-on' otherwise."""
    if target_layer in ("infrastructure", "utility"):
        return "uses"
    name_lower = target_name.lower().replace("-", "_").replace(" ", "_")
    if any(pat in name_lower for pat in UTILITY_PATTERNS):
        return "uses"
    return "depends-on"


class RelateStage:
    """Derives relationships between architecture entities."""

    name: str = "relate"
    requires: list[str] = ["observe", "infer", "allocate"]

    def run(self, ctx: PipelineContext) -> StageResult[RelateResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        observe_result = ctx.get("observe")
        infer_result = ctx.get("infer")
        allocate_result = ctx.get("allocate")
        if not all([observe_result, infer_result, allocate_result]):
            raise RuntimeError("relate requires observe, infer, allocate")

        inventory: Inventory = observe_result.output
        inference: InferenceResult = infer_result.output
        allocation: AllocationResult = allocate_result.output

        relationships: list[DerivedRelationship] = []

        # 1. realizes: component → capability (from allocation)
        realized_caps: set[str] = set()
        for comp in allocation.components:
            if comp.capability_id:
                relationships.append(
                    DerivedRelationship(
                        from_id=comp.id,
                        to_id=comp.capability_id,
                        rel_type="realizes",
                        evidence_source="allocation",
                    )
                )
                realized_caps.add(comp.capability_id)

        # 1b. Infer realizes for components without capability_id
        # Match by name similarity to unrealized capabilities
        unrealized_caps = [c for c in inference.capabilities if c.id not in realized_caps]
        if unrealized_caps:
            for comp in allocation.components:
                if comp.capability_id:
                    continue
                # Try name matching
                comp_words = set(comp.name.lower().replace("(", "").replace(")", "").split())
                best_cap = None
                best_score = 0
                for cap in unrealized_caps:
                    cap_words = set(cap.name.lower().split())
                    overlap = len(comp_words & cap_words)
                    if overlap > best_score:
                        best_score = overlap
                        best_cap = cap
                if best_cap and best_score >= 1:
                    relationships.append(
                        DerivedRelationship(
                            from_id=comp.id,
                            to_id=best_cap.id,
                            rel_type="realizes",
                            evidence_source="name_inference",
                        )
                    )
                    realized_caps.add(best_cap.id)
                    unrealized_caps.remove(best_cap)

        # 2. depends-on/uses: component → component (from import edges)
        file_to_comp = _build_file_map(allocation.components)
        comp_by_id = {comp.id: comp for comp in allocation.components}
        dep_pairs: set[tuple[str, str]] = set()
        for mod in inventory.modules:
            src_comp = file_to_comp.get(mod.path)
            if not src_comp:
                continue
            for imp in mod.imports:
                # Find target module
                for other_mod in inventory.modules:
                    if other_mod.path.stem in imp or str(other_mod.path.parent.stem) in imp:
                        tgt_comp = file_to_comp.get(other_mod.path)
                        if tgt_comp and tgt_comp != src_comp:
                            dep_pairs.add((src_comp, tgt_comp))

        for src, tgt in dep_pairs:
            tgt_alloc = comp_by_id.get(tgt)
            tgt_layer = getattr(tgt_alloc, "layer", "") or "" if tgt_alloc else ""
            tgt_name = getattr(tgt_alloc, "name", "") or "" if tgt_alloc else ""
            rel_type = _pick_relationship_type(tgt_layer, tgt_name)
            relationships.append(
                DerivedRelationship(
                    from_id=src,
                    to_id=tgt,
                    rel_type=rel_type,
                    evidence_source="import",
                )
            )

        # 3. contains: layer → component
        layers_seen: dict[str, list[str]] = defaultdict(list)
        for comp in allocation.components:
            if comp.layer:
                layers_seen[comp.layer].append(comp.id)

        for layer, comp_ids in layers_seen.items():
            layer_id = f"LAYER-{layer.upper()}"
            for comp_id in comp_ids:
                relationships.append(
                    DerivedRelationship(
                        from_id=layer_id,
                        to_id=comp_id,
                        rel_type="contains",
                        evidence_source="layer_inference",
                    )
                )

        # 4. exposes: component → interface (from routes)
        for route in inventory.routes:
            route_file = route.file
            comp_id = file_to_comp.get(route_file)
            if comp_id:
                iface_id = f"IF-{route.method}-{route.path.strip('/').replace('/', '-')}"
                relationships.append(
                    DerivedRelationship(
                        from_id=comp_id,
                        to_id=iface_id,
                        rel_type="exposes",
                        evidence_source="route",
                    )
                )

        # 5. constrained-by: component → constraint
        for i, con in enumerate(inventory.constraints):
            con_id = f"CON-{i + 1}"
            # Technology constraints apply to all components
            if con.constraint_type == "TECHNOLOGY":
                for comp in allocation.components:
                    relationships.append(
                        DerivedRelationship(
                            from_id=comp.id,
                            to_id=con_id,
                            rel_type="constrained-by",
                            evidence_source="constraint_detection",
                        )
                    )
            else:
                # File-specific constraints — find which component owns the file
                comp_id = file_to_comp.get(Path(con.source))
                if comp_id:
                    relationships.append(
                        DerivedRelationship(
                            from_id=comp_id,
                            to_id=con_id,
                            rel_type="constrained-by",
                            evidence_source="constraint_detection",
                        )
                    )

        result = RelateResult(
            relationships=relationships,
            layers=[
                {
                    "id": f"LAYER-{layer.upper()}",
                    "name": layer.title(),
                    "description": f"Components in the {layer} architectural tier",
                }
                for layer in sorted(layers_seen.keys())
            ],
        )

        quality = QualityMetrics(
            score=min(100, int(len(relationships) / max(len(allocation.components), 1) * 25)),
            sub_scores={
                "relationship_count": float(len(relationships)),
                "realizes_count": float(sum(1 for r in relationships if r.rel_type == "realizes")),
                "depends_on_count": float(
                    sum(1 for r in relationships if r.rel_type == "depends-on")
                ),
                "constrained_by_count": float(
                    sum(1 for r in relationships if r.rel_type == "constrained-by")
                ),
                "layer_count": float(len(layers_seen)),
            },
            thresholds={},
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(allocation.components)),
            duration_ms=duration_ms,
            version="1.0",
            summary=f"Derived {len(relationships)} relationships across {len(layers_seen)} layers.",
        )


def _build_file_map(components: list[ComponentAllocation]) -> dict[Path, str]:
    """Map file paths to component IDs."""
    result: dict[Path, str] = {}
    for comp in components:
        for f in comp.files:
            result[f] = comp.id
    return result
