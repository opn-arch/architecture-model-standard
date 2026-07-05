"""Model comparison utilities for measuring structural similarity between ArchitectureModels.

Provides fuzzy matching for entity names, layer decomposition analysis,
and overall reproducibility scoring.
"""

from __future__ import annotations

from collections import Counter

from architecture_model.core.types import ArchitectureModel


def compare_models(a: ArchitectureModel, b: ArchitectureModel) -> dict[str, float]:
    """Compare two architecture models structurally.

    Uses fuzzy matching for names (word overlap) and considers both
    .layer field AND allocated-to/contains relationships for decomposition.

    Returns a dict of similarity scores (0-1) across dimensions.
    """
    # Layer similarity (fuzzy: best bipartite matching on word sets)
    a_layers = [_normalize_name(l.name) for l in a.entities.layers]
    b_layers = [_normalize_name(l.name) for l in b.entities.layers]
    layer_sim = fuzzy_set_similarity(a_layers, b_layers)

    # Component similarity (fuzzy matching)
    a_comps = [_normalize_name(c.name) for c in a.entities.components]
    b_comps = [_normalize_name(c.name) for c in b.entities.components]
    comp_sim = fuzzy_set_similarity(a_comps, b_comps)

    # Capability similarity (fuzzy)
    a_caps = [_normalize_name(c.name) for c in a.entities.capabilities]
    b_caps = [_normalize_name(c.name) for c in b.entities.capabilities]
    cap_sim = fuzzy_set_similarity(a_caps, b_caps)

    # Relationship type distribution (cosine similarity)
    a_rel_types = Counter(r.type.value for r in a.relationships)
    b_rel_types = Counter(r.type.value for r in b.relationships)
    rel_type_sim = cosine_counters(a_rel_types, b_rel_types)

    # Relationship density ratio
    a_rels = len(a.relationships)
    b_rels = len(b.relationships)
    density_ratio = min(a_rels, b_rels) / max(a_rels, b_rels) if max(a_rels, b_rels) > 0 else 1.0

    # Decomposition: layer→component groupings
    a_decomp = layer_decomposition(a)
    b_decomp = layer_decomposition(b)
    decomp_sim = decomposition_similarity(a_decomp, b_decomp)

    # Entity count stability (are models at similar granularity?)
    a_total = len(a.entities.components) + len(a.entities.capabilities)
    b_total = len(b.entities.components) + len(b.entities.capabilities)
    granularity = min(a_total, b_total) / max(a_total, b_total) if max(a_total, b_total) > 0 else 1.0

    # Overall weighted score
    overall = (
        0.15 * layer_sim +
        0.25 * comp_sim +
        0.15 * cap_sim +
        0.15 * rel_type_sim +
        0.10 * density_ratio +
        0.10 * decomp_sim +
        0.10 * granularity
    )

    return {
        "layer_similarity": layer_sim,
        "component_similarity": comp_sim,
        "capability_similarity": cap_sim,
        "relationship_type_dist": rel_type_sim,
        "relationship_density": density_ratio,
        "decomposition_similarity": decomp_sim,
        "granularity_match": granularity,
        "overall": overall,
    }


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    return name.lower().replace("-", " ").replace("_", " ").strip()


def jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def cosine_counters(a: Counter, b: Counter) -> float:
    """Cosine similarity between two Counter distributions."""
    all_keys = set(a.keys()) | set(b.keys())
    if not all_keys:
        return 1.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in all_keys)
    mag_a = sum(v**2 for v in a.values()) ** 0.5
    mag_b = sum(v**2 for v in b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def fuzzy_set_similarity(a_names: list[str], b_names: list[str]) -> float:
    """Compute fuzzy set similarity using greedy bipartite word-Jaccard matching.

    For each item in the smaller set, find the best match in the larger set.
    Average the best-match scores. Penalizes size mismatch.
    """
    if not a_names and not b_names:
        return 1.0
    if not a_names or not b_names:
        return 0.0

    # Always match from smaller to larger
    if len(a_names) > len(b_names):
        a_names, b_names = b_names, a_names

    # Greedy matching: for each in A, find best match in B
    used: set[int] = set()
    total_score = 0.0

    for a_item in a_names:
        a_words = set(a_item.split())
        best_score = 0.0
        best_idx = -1

        for i, b_item in enumerate(b_names):
            if i in used:
                continue
            b_words = set(b_item.split())
            score = jaccard(a_words, b_words)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0:
            used.add(best_idx)
        total_score += best_score

    # Penalize size mismatch: average over the larger set size
    return total_score / max(len(a_names), len(b_names))


def layer_decomposition(model: ArchitectureModel) -> dict[str, set[str]]:
    """Map layer names to sets of component names.

    Checks BOTH the .layer field on Component AND allocated-to/contains
    relationships from layers to components.
    """
    layer_id_to_name = {l.id: _normalize_name(l.name) for l in model.entities.layers}
    comp_id_to_name = {c.id: _normalize_name(c.name) for c in model.entities.components}
    layer_ids = set(layer_id_to_name.keys())
    comp_ids = set(comp_id_to_name.keys())

    decomp: dict[str, set[str]] = {}

    # Method 1: .layer field on Component
    for comp in model.entities.components:
        if comp.layer and comp.layer in layer_id_to_name:
            layer_name = layer_id_to_name[comp.layer]
            decomp.setdefault(layer_name, set()).add(_normalize_name(comp.name))

    # Method 2: relationships (contains, allocated-to)
    for rel in model.relationships:
        if rel.type.value in ("contains", "allocated-to"):
            # Layer → Component
            if rel.from_id in layer_ids and rel.to_id in comp_ids:
                layer_name = layer_id_to_name[rel.from_id]
                comp_name = comp_id_to_name[rel.to_id]
                decomp.setdefault(layer_name, set()).add(comp_name)
            # Component → Layer (allocated-to can go either direction)
            elif rel.to_id in layer_ids and rel.from_id in comp_ids:
                layer_name = layer_id_to_name[rel.to_id]
                comp_name = comp_id_to_name[rel.from_id]
                decomp.setdefault(layer_name, set()).add(comp_name)

    return decomp


def decomposition_similarity(a: dict[str, set[str]], b: dict[str, set[str]]) -> float:
    """Compare layer→component groupings using fuzzy layer matching."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    a_layers = list(a.keys())
    b_layers = list(b.keys())
    used_b: set[int] = set()
    total_score = 0.0

    for a_layer in a_layers:
        a_words = set(a_layer.split())
        best_layer_score = 0.0
        best_b_idx = -1

        for i, b_layer in enumerate(b_layers):
            if i in used_b:
                continue
            b_words = set(b_layer.split())
            name_sim = jaccard(a_words, b_words)
            if name_sim > best_layer_score:
                best_layer_score = name_sim
                best_b_idx = i

        if best_b_idx >= 0 and best_layer_score > 0.3:
            used_b.add(best_b_idx)
            a_comps = a[a_layer]
            b_comps = b[b_layers[best_b_idx]]
            comp_sim = fuzzy_set_similarity(
                [c for c in a_comps], [c for c in b_comps]
            )
            total_score += comp_sim

    return total_score / max(len(a_layers), len(b_layers))
