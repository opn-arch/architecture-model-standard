"""Module-level import-graph clustering.

Groups modules by import affinity using greedy modularity clustering
with support for target cluster count and minimum group size.
"""
from __future__ import annotations

from collections import defaultdict
from math import ceil


def cluster_modules(
    modules: list[str],
    edges: list[tuple[str, str]],
    *,
    target_k: int = 5,
    min_cluster_size: int = 3,
) -> list[list[str]]:
    """Cluster modules into groups by import-graph affinity.

    Args:
        modules: List of module file paths.
        edges: List of (source, target) import edges.
        target_k: Target number of clusters.
        min_cluster_size: Merge clusters smaller than this.

    Returns:
        List of module groups (each group is a list of file paths).
    """
    if len(modules) <= target_k:
        return [[m] for m in modules]

    max_cluster_size = ceil(len(modules) / target_k)

    # Build undirected adjacency
    adj: dict[str, set[str]] = defaultdict(set)
    module_set = set(modules)
    for src, tgt in edges:
        if src in module_set and tgt in module_set:
            adj[src].add(tgt)
            adj[tgt].add(src)

    # Sort by degree (most connected first = cluster seeds)
    sorted_modules = sorted(modules, key=lambda m: len(adj.get(m, set())), reverse=True)

    assigned: dict[str, int] = {}
    clusters: list[list[str]] = []

    for mod in sorted_modules:
        if mod in assigned:
            continue
        idx = len(clusters)
        cluster = [mod]
        assigned[mod] = idx

        # BFS growth: expand cluster via neighbors until max size
        frontier = list(adj.get(mod, set()))
        visited = {mod}
        while frontier and len(cluster) < max_cluster_size:
            # Score candidates by connectivity to current cluster
            frontier = [n for n in frontier if n not in assigned and n not in visited]
            if not frontier:
                break
            cluster_set = set(cluster)
            frontier.sort(key=lambda n: len(adj.get(n, set()) & cluster_set), reverse=True)
            best = frontier.pop(0)
            visited.add(best)
            cluster.append(best)
            assigned[best] = idx
            # Add best's neighbors to frontier
            for neighbor in adj.get(best, set()):
                if neighbor not in visited and neighbor not in assigned:
                    frontier.append(neighbor)

        clusters.append(cluster)

    # Assign unassigned (isolated) modules to nearest cluster
    for mod in modules:
        if mod not in assigned:
            merged = False
            for src, tgt in edges:
                if src == mod and tgt in assigned:
                    clusters[assigned[tgt]].append(mod)
                    assigned[mod] = assigned[tgt]
                    merged = True
                    break
                if tgt == mod and src in assigned:
                    clusters[assigned[src]].append(mod)
                    assigned[mod] = assigned[src]
                    merged = True
                    break
            if not merged:
                smallest = min(range(len(clusters)), key=lambda i: len(clusters[i]))
                clusters[smallest].append(mod)
                assigned[mod] = smallest

    # Merge tiny clusters into nearest neighbor
    merged_clusters: list[list[str]] = []
    for cluster in clusters:
        if len(cluster) >= min_cluster_size:
            merged_clusters.append(cluster)
        else:
            cluster_set = set(cluster)
            best_target = None
            best_score = -1
            for i, other in enumerate(merged_clusters):
                other_set = set(other)
                score = sum(
                    1 for src, tgt in edges
                    if (src in cluster_set and tgt in other_set)
                    or (tgt in cluster_set and src in other_set)
                )
                if score > best_score:
                    best_score = score
                    best_target = i
            if best_target is not None:
                merged_clusters[best_target].extend(cluster)
            elif merged_clusters:
                merged_clusters[0].extend(cluster)
            else:
                merged_clusters.append(cluster)

    return merged_clusters
