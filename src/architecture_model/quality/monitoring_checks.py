"""Automated consistency and quality checks for monitoring.

These checks provide automated quality scoring without an external oracle:
- Idempotency: same input -> same output (decomposition stability)
- Stability: small perturbations -> similar clusters
- Pattern matching: assigned patterns match actual code indicators
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsistencyResult:
    """Result of an automated consistency check."""
    metric_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: dict[str, Any] = field(default_factory=dict)


def check_decompose_idempotency(manifest, *, block_id: str, block_name: str, runs: int = 3) -> ConsistencyResult:
    """Run iterative_decompose multiple times, check outputs match."""
    from architecture_model.orchestration.deep_decompose import iterative_decompose
    from architecture_model.quality.monitoring import get_collector

    results = []
    for _ in range(runs):
        # Drain metrics to avoid accumulation from repeated runs
        get_collector().drain()
        r = iterative_decompose(manifest, block_id=block_id, block_name=block_name)
        clusters = []
        for decomp in r:
            for sc in decomp.sub_components:
                clusters.append(frozenset(sc.files))
        results.append(frozenset(clusters))

    unique = len(set(str(r) for r in results))
    passed = unique == 1
    return ConsistencyResult(
        metric_name="decompose_idempotency",
        passed=passed,
        score=1.0 if passed else 1.0 / unique,
        details={"runs": runs, "unique_outputs": unique},
    )


def check_cluster_stability(modules: list[str], edges: list[tuple[str, str]], perturbations: int = 5) -> ConsistencyResult:
    """Check that removing one edge doesn't drastically change clusters."""
    from architecture_model.core.cluster import cluster_modules
    from architecture_model.quality.monitoring import get_collector
    import random

    if not edges:
        return ConsistencyResult(metric_name="cluster_stability", passed=True, score=1.0, details={"reason": "no edges"})

    get_collector().drain()
    base_clusters = cluster_modules(modules, edges, target_k=4, min_cluster_size=2)
    base_sets = [frozenset(c) for c in base_clusters]

    similarities = []
    rng = random.Random(42)
    for _ in range(min(perturbations, len(edges))):
        perturbed = edges[:]
        idx = rng.randint(0, len(perturbed) - 1)
        perturbed.pop(idx)
        get_collector().drain()
        new_clusters = cluster_modules(modules, perturbed, target_k=4, min_cluster_size=2)
        new_sets = [frozenset(c) for c in new_clusters]

        same_count = 0
        for m in modules:
            base_cluster = next((s for s in base_sets if m in s), None)
            new_cluster = next((s for s in new_sets if m in s), None)
            if base_cluster and new_cluster and base_cluster == new_cluster:
                same_count += 1
        similarities.append(same_count / len(modules) if modules else 1.0)

    avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
    get_collector().drain()  # clean up monitoring noise
    return ConsistencyResult(
        metric_name="cluster_stability",
        passed=avg_similarity >= 0.7,
        score=avg_similarity,
        details={"perturbations": len(similarities), "avg_similarity": avg_similarity},
    )


def check_pattern_indicators(pattern_name: str, file_contents: dict[str, str]) -> ConsistencyResult:
    """Check if assigned pattern's indicators appear in file contents."""
    from architecture_model.patterns import get_pattern

    pattern = get_pattern(pattern_name)
    if not pattern:
        return ConsistencyResult(metric_name="pattern_indicators", passed=False, score=0.0, details={"error": f"unknown pattern: {pattern_name}"})

    indicators = pattern.get("indicators", [])
    if not indicators:
        return ConsistencyResult(metric_name="pattern_indicators", passed=True, score=1.0)

    all_content = "\n".join(file_contents.values())
    matched = 0
    for indicator in indicators:
        search = indicator.strip("*").strip()
        if search in all_content:
            matched += 1

    score = matched / len(indicators) if indicators else 1.0
    return ConsistencyResult(
        metric_name="pattern_indicators",
        passed=score >= 0.3,
        score=score,
        details={"indicators_total": len(indicators), "indicators_matched": matched},
    )
