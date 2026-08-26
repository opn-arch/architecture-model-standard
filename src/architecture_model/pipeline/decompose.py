"""Decompose stage — detect system boundaries and hierarchical sub-components."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from architecture_model.pipeline.allocate_types import AllocationResult
from architecture_model.pipeline.decompose_types import (
    DecomposeResult,
    SubComponent,
    SystemBoundary,
)
from architecture_model.pipeline.protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
)
from architecture_model.pipeline.relate_types import RelateResult

FULL_SYSTEM_FILE_THRESHOLD = 5
HIERARCHY_FILE_THRESHOLD = 8  # components with >= this many files get sub-components
MAX_SYSTEMS = 8  # merge overly fragmented decompositions
MERGE_COUPLING_THRESHOLD = 0.3  # merge systems with >30% mutual import density


def _cluster_by_directory(files: list[Path]) -> dict[str, list[Path]]:
    """Group files by their immediate parent directory."""
    clusters: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        # Use parent directory name as cluster key
        parent = f.parent.name if f.parent.name else "root"
        clusters[parent].append(f)
    return dict(clusters)


def _decompose_component(comp_id: str, comp_name: str, files: list[Path]) -> list[SubComponent]:
    """Split a large component into sub-components by directory affinity."""
    clusters = _cluster_by_directory(files)

    # If all files in same directory, no useful split
    if len(clusters) <= 1:
        return []

    # Only split if clusters are meaningful (>1 file each, or >2 clusters)
    meaningful = {k: v for k, v in clusters.items() if len(v) >= 2}
    if len(meaningful) < 2:
        return []

    subs = []
    for i, (dir_name, dir_files) in enumerate(sorted(meaningful.items()), 1):
        sub_id = f"{comp_id}.{i}"
        sub_name = f"{comp_name}/{dir_name}"
        subs.append(
            SubComponent(
                id=sub_id,
                name=sub_name,
                parent_id=comp_id,
                files=[str(f) for f in dir_files],
            )
        )

    # Collect remaining files not in meaningful clusters
    remaining = []
    for k, v in clusters.items():
        if k not in meaningful:
            remaining.extend(v)
    if remaining:
        subs.append(
            SubComponent(
                id=f"{comp_id}.{len(meaningful) + 1}",
                name=f"{comp_name}/misc",
                parent_id=comp_id,
                files=[str(f) for f in remaining],
            )
        )

    return subs


def _merge_coupled_systems(
    systems: list[SystemBoundary],
    inlines: list[SystemBoundary],
    inter_edges: list[tuple[str, str, str]],
) -> tuple[list[SystemBoundary], list[SystemBoundary], list[tuple[str, str, str]]]:
    """Merge tightly-coupled systems to improve cohesion.

    Two systems merge if:
    - Combined they'd still be reasonable size (<200 files)
    - They share high coupling (many inter-system edges relative to size)
    - Total system count exceeds MAX_SYSTEMS
    """
    if len(systems) <= MAX_SYSTEMS:
        return systems, inlines, inter_edges

    # Count edge density between system pairs
    pair_edges: dict[tuple[str, str], int] = defaultdict(int)
    sys_by_id = {s.system_id: s for s in systems}

    for from_sys, to_sys, _ in inter_edges:
        key = tuple(sorted([from_sys, to_sys]))
        pair_edges[key] += 1

    # Sort pairs by coupling density (edges / min_files)
    merge_candidates = []
    for (a, b), count in pair_edges.items():
        sa, sb = sys_by_id.get(a), sys_by_id.get(b)
        if not sa or not sb:
            continue
        min_files = min(len(sa.files), len(sb.files))
        if min_files == 0:
            continue
        density = count / min_files
        if density >= MERGE_COUPLING_THRESHOLD:
            merge_candidates.append((density, a, b))

    merge_candidates.sort(reverse=True)

    # Perform merges until we're at MAX_SYSTEMS
    merged_ids: set[str] = set()
    for _, a, b in merge_candidates:
        if len(systems) - len(merged_ids) <= MAX_SYSTEMS:
            break
        if a in merged_ids or b in merged_ids:
            continue
        sa, sb = sys_by_id.get(a), sys_by_id.get(b)
        if not sa or not sb:
            continue
        # Merge b into a
        sa.files.extend(sb.files)
        sa.component_ids.extend(sb.component_ids)
        # Keep merged name concise for MCP routing
        merge_count = getattr(sa, "_merge_count", 1) + 1
        sa._merge_count = merge_count
        if merge_count == 2:
            sa.name = f"{sa.name} + {sb.name}"
        else:
            # After 2+ merges, use primary name + count
            primary = sa.name.split(" + ")[0]
            sa.name = f"{primary} (+ {merge_count - 1} related)"
        sa.complexity = float(len(sa.files))
        merged_ids.add(b)

    # Remove merged systems
    systems = [s for s in systems if s.system_id not in merged_ids]

    # Remove inter-edges that are now intra-system
    remaining_sys_ids = {s.system_id for s in systems}
    inter_edges = [
        (f, t, r)
        for f, t, r in inter_edges
        if f in remaining_sys_ids and t in remaining_sys_ids and f != t
    ]

    return systems, inlines, inter_edges


class DecomposeStage:
    name = "decompose"
    version = "2.0"
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

            # Hierarchical decomposition for large components
            sub_components: list[SubComponent] = []
            if len(comp.files) >= HIERARCHY_FILE_THRESHOLD:
                sub_components = _decompose_component(comp.id, comp.name, comp.files)

            sb = SystemBoundary(
                system_id=sys_id,
                name=comp.name,
                component_ids=[comp.id],
                files=[str(f) for f in comp.files],
                complexity=float(len(comp.files)),
                is_full_system=is_full,
                sub_components=sub_components,
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

        # Merge tightly-coupled small systems to reduce fragmentation
        systems, inlines, inter_edges = _merge_coupled_systems(systems, inlines, inter_edges)

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

        total_subs = sum(len(s.sub_components) for s in systems + inlines)
        if total_subs > 0:
            diagnostics.append(
                Diagnostic(
                    severity="info",
                    code="HIERARCHY_CREATED",
                    message=f"Created {total_subs} sub-components across {sum(1 for s in systems + inlines if s.sub_components)} components",
                )
            )

        quality = QualityMetrics(
            score=100.0 if systems else 50.0,
            sub_scores={
                "system_count": float(len(systems)),
                "inline_count": float(len(inlines)),
                "sub_component_count": float(total_subs),
            },
        )

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=[],
            duration_ms=duration,
            summary=f"Identified {len(systems)} autonomous systems and {len(inlines)} inline components.",
        )
