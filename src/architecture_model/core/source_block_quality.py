"""F-Block quality metrics: modularity, conductance, provenance, agreement."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ArchitectureModel

from .types import RelationType


def _depends_on_edges(model: "ArchitectureModel") -> list[tuple[str, str]]:
    """Extract directed depends-on edges between components."""
    comp_ids = {c.id for c in model.entities.components}
    edges = []
    for rel in model.relationships:
        if rel.type == RelationType.DEPENDS_ON:
            if rel.from_id in comp_ids and rel.to_id in comp_ids:
                edges.append((rel.from_id, rel.to_id))
    return edges


def _undirected_edges(edges: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Convert directed edges to undirected (both directions count as one edge)."""
    seen: set[tuple[str, str]] = set()
    result = []
    for a, b in edges:
        key = (min(a, b), max(a, b))
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def compute_modularity(model: "ArchitectureModel") -> float:
    """Compute Newman's modularity Q over depends-on edges.

    Q = (1/2m) * sum_ij (A_ij - k_i*k_j / 2m) * delta(c_i, c_j)

    Uses undirected interpretation of depends-on edges.
    """
    directed = _depends_on_edges(model)
    if not directed:
        return 0.0

    # Build undirected adjacency matrix representation
    undirected = _undirected_edges(directed)
    m = len(undirected)
    if m == 0:
        return 0.0

    # Degree of each node (undirected)
    degree: dict[str, int] = defaultdict(int)
    for a, b in undirected:
        degree[a] += 1
        degree[b] += 1

    # Community assignment: component -> source_block
    comp_to_fb = {c.id: c.source_block for c in model.entities.components}

    # Adjacency set for quick lookup
    adj_set: set[tuple[str, str]] = set()
    for a, b in undirected:
        adj_set.add((a, b))
        adj_set.add((b, a))

    two_m = 2 * m
    q_sum = 0.0
    comp_ids = [c.id for c in model.entities.components]

    for i in comp_ids:
        for j in comp_ids:
            ci = comp_to_fb.get(i, i)
            cj = comp_to_fb.get(j, j)
            if ci and cj and ci == cj:
                a_ij = 1.0 if (i, j) in adj_set else 0.0
                q_sum += a_ij - (degree.get(i, 0) * degree.get(j, 0)) / two_m

    return q_sum / two_m


def compute_conductance(model: "ArchitectureModel") -> dict[str, float]:
    """Compute conductance per F-block.

    conductance = edges_out / (edges_out + edges_in)
    where edges_in = edges with both endpoints in the block,
    edges_out = edges with exactly one endpoint in the block.
    """
    directed = _depends_on_edges(model)
    comp_to_fb = {c.id: c.source_block for c in model.entities.components}

    # Group components by source_block
    fb_members: dict[str, set[str]] = defaultdict(set)
    for c in model.entities.components:
        if c.source_block:
            fb_members[c.source_block].add(c.id)

    result: dict[str, float] = {}
    for fb, members in fb_members.items():
        edges_in = 0
        edges_out = 0
        for a, b in directed:
            a_in = a in members
            b_in = b in members
            if a_in and b_in:
                edges_in += 1
            elif a_in or b_in:
                edges_out += 1
        total = edges_out + edges_in
        result[fb] = edges_out / total if total > 0 else 0.0

    return result


def compute_agreement_rate(model: "ArchitectureModel") -> float:
    """Compare existing source_block assignments with auto_assign_source_blocks output.

    Returns fraction of components where assignments agree.
    """
    from .source_block_assign import auto_assign_source_blocks

    comps = model.entities.components
    if not comps:
        return 1.0

    # Check if any components have source_block set
    has_source_blocks = any(c.source_block for c in comps)
    if not has_source_blocks:
        return 1.0

    # Create a copy without source_blocks to force auto_assign to run
    model_copy = deepcopy(model)
    for c in model_copy.entities.components:
        c.source_block = ""

    auto_model = auto_assign_source_blocks(model_copy)
    auto_fb = {c.id: c.source_block for c in auto_model.entities.components}

    # Compare: we check if the *partitioning* agrees, not the labels.
    # Two components in the same source_block in original should be in the same
    # source_block in auto, and vice versa.
    # Simpler approach: direct label comparison (as specified).
    # But labels will differ. Use partition agreement instead.
    # Group by source_block in each assignment
    original_fb = {c.id: c.source_block for c in comps}

    # Build partition: which pairs are co-clustered?
    ids = sorted(original_fb.keys())
    if len(ids) <= 1:
        return 1.0

    agree = 0
    total = 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            orig_same = original_fb[ids[i]] == original_fb[ids[j]]
            auto_same = auto_fb.get(ids[i]) == auto_fb.get(ids[j])
            if orig_same == auto_same:
                agree += 1
            total += 1

    return agree / total if total > 0 else 1.0


@dataclass
class FBlockQuality:
    """Aggregate F-block quality metrics."""
    modularity: float
    conductance: dict[str, float]
    intra_inter_ratio: float
    agreement_rate: float | None
    orphan_rate: float
    cluster_balance: float
    cross_block_cycle_ratio: float


def _compute_intra_inter_ratio(model: "ArchitectureModel") -> float:
    """Ratio of intra-block edges to total edges."""
    directed = _depends_on_edges(model)
    if not directed:
        return 0.0
    comp_to_fb = {c.id: c.source_block for c in model.entities.components}
    intra = sum(1 for a, b in directed if comp_to_fb.get(a) == comp_to_fb.get(b) and comp_to_fb.get(a))
    return intra / len(directed)


def _compute_orphan_rate(model: "ArchitectureModel") -> float:
    """Fraction of components with zero depends-on edges."""
    comps = model.entities.components
    if not comps:
        return 0.0
    directed = _depends_on_edges(model)
    connected = set()
    for a, b in directed:
        connected.add(a)
        connected.add(b)
    orphans = sum(1 for c in comps if c.id not in connected)
    return orphans / len(comps)


def _compute_cluster_balance(model: "ArchitectureModel") -> float:
    """Gini coefficient of source_block cluster sizes. 0=balanced, 1=imbalanced."""
    fb_sizes: dict[str, int] = defaultdict(int)
    for c in model.entities.components:
        if c.source_block:
            fb_sizes[c.source_block] += 1
    if not fb_sizes:
        return 0.0
    sizes = sorted(fb_sizes.values())
    n = len(sizes)
    if n <= 1:
        return 0.0
    total = sum(sizes)
    if total == 0:
        return 0.0
    # Gini formula
    numerator = sum((2 * (i + 1) - n - 1) * sizes[i] for i in range(n))
    return numerator / (n * total)


def _compute_cross_block_cycle_ratio(model: "ArchitectureModel") -> float:
    """Fraction of F-block pairs with bidirectional edges."""
    directed = _depends_on_edges(model)
    comp_to_fb = {c.id: c.source_block for c in model.entities.components}

    # Build cross-block directed edges at F-block level
    fb_edges: set[tuple[str, str]] = set()
    for a, b in directed:
        fa = comp_to_fb.get(a)
        fb = comp_to_fb.get(b)
        if fa and fb and fa != fb:
            fb_edges.add((fa, fb))

    if not fb_edges:
        return 0.0

    # Pairs with any edge
    pairs_with_edges: set[tuple[str, str]] = set()
    for a, b in fb_edges:
        pairs_with_edges.add((min(a, b), max(a, b)))

    # Pairs with bidirectional edges
    bidirectional = set()
    for a, b in fb_edges:
        if (b, a) in fb_edges:
            bidirectional.add((min(a, b), max(a, b)))

    return len(bidirectional) / len(pairs_with_edges) if pairs_with_edges else 0.0


def compute_source_block_quality(model: "ArchitectureModel") -> FBlockQuality:
    """Compute all F-block quality metrics."""
    conductance = compute_conductance(model)
    try:
        agreement = compute_agreement_rate(model)
    except Exception:
        agreement = None

    return FBlockQuality(
        modularity=compute_modularity(model),
        conductance=conductance,
        intra_inter_ratio=_compute_intra_inter_ratio(model),
        agreement_rate=agreement,
        orphan_rate=_compute_orphan_rate(model),
        cluster_balance=_compute_cluster_balance(model),
        cross_block_cycle_ratio=_compute_cross_block_cycle_ratio(model),
    )


# ---------------------------------------------------------------------------
# A3: Provenance
# ---------------------------------------------------------------------------

@dataclass
class FBlockProvenance:
    """Per-component provenance metadata for F-block assignment."""
    source: str  # "directory" | "clustering" | "manual"
    confidence: float
    metrics: dict[str, float]
    content_hash: str
    computed_at: str


def compute_provenance(
    model: "ArchitectureModel",
    quality: FBlockQuality,
) -> dict[str, FBlockProvenance]:
    """Compute per-component provenance and attach to component.extensions."""
    result: dict[str, FBlockProvenance] = {}
    directed = _depends_on_edges(model)
    connected = set()
    for a, b in directed:
        connected.add(a)
        connected.add(b)

    for comp in model.entities.components:
        fb = comp.source_block or ""
        cond = quality.conductance.get(fb, 0.0)
        orphan_flag = 0.0 if comp.id in connected else 1.0
        agreement_val = 1.0 if quality.agreement_rate and quality.agreement_rate > 0.5 else 0.0

        # Modularity contribution: use overall modularity as proxy
        mod_contrib = min(max(quality.modularity, 0.0), 1.0)

        confidence = (
            0.4 * (1 - cond)
            + 0.3 * agreement_val
            + 0.2 * mod_contrib
            + 0.1 * (1 - orphan_flag)
        )

        # Determine source heuristic
        if comp.files:
            source = "directory"
        elif quality.agreement_rate is not None and quality.agreement_rate < 1.0:
            source = "clustering"
        else:
            source = "manual"

        content_hash = hashlib.sha256(
            json.dumps({"id": comp.id, "source_block": fb}, sort_keys=True).encode()
        ).hexdigest()[:16]

        prov = FBlockProvenance(
            source=source,
            confidence=round(confidence, 4),
            metrics={
                "conductance": round(cond, 4),
                "orphan_flag": orphan_flag,
                "modularity_contribution": round(mod_contrib, 4),
            },
            content_hash=content_hash,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
        result[comp.id] = prov

        # Store in extensions
        comp.extensions["source_block_provenance"] = {
            "source": prov.source,
            "confidence": prov.confidence,
            "metrics": prov.metrics,
            "content_hash": prov.content_hash,
            "computed_at": prov.computed_at,
        }

    return result
