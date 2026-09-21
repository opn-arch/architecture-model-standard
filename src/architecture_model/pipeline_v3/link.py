"""pipeline_v3.link — Relationship inference stage (T0.14 Phase 6.4).

Derives ``depends-on`` :class:`Link` records between :class:`Cluster`
values from import edges reported by the scan stage. Each import in a
module belonging to cluster A that resolves to a module in cluster B
(A ≠ B) contributes a link A → B with weight = distinct
(source_module, target_cluster) pairs.

Resolution rules
----------------

An import string ``imp`` resolves to cluster ``C`` iff ``imp`` starts with
``C.root_prefix`` on a dotted-segment boundary. To bridge the AMS reality
where scanned module names begin with ``src.`` but imports do not, the
resolver also matches after stripping a leading ``src.`` from cluster
prefixes.

When multiple clusters match, the longest matching prefix wins (most-
specific containment). Unresolved imports (stdlib, third-party, or
anything outside the scanned tree) are silently dropped.

Design intent
-------------

Kept deliberately simple: one relationship kind (``depends-on``), one
signal (import edges). Additional relationship kinds — ``exposes``
(interface), ``realizes`` (capability), ``triggers`` (behavior) — come
online in later stages once we know cluster / entity types. The link
stage's contract is: **structural coupling only**.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from architecture_model.pipeline_v3.cluster import Cluster

__all__ = ["Link", "link_clusters"]


@dataclass(frozen=True)
class Link:
    """A directed relationship between two clusters (or entities).

    ``sequence`` is 17a3 flow-ordering metadata: 1-indexed ordinal
    position of the destination in the source's outgoing flow when the
    source is a composite. Non-``None`` only on ``triggers`` edges
    emitted by containerize from composite behaviors (see
    :mod:`architecture_model.pipeline_v3.derive_triggers`).
    """

    from_cluster: str          # source Cluster.id (or entity id)
    to_cluster: str            # target Cluster.id (or entity id)
    kind: str = "depends-on"
    weight: int = 1
    sequence: int | None = None


def _strip_src(prefix: str) -> str:
    """Return prefix without a leading ``src.`` segment, if present."""
    return prefix[4:] if prefix.startswith("src.") else prefix


def _prefix_matches(imp: str, prefix: str) -> bool:
    """True iff ``imp`` starts with ``prefix`` on a dotted-segment boundary."""
    if not prefix:
        return False
    return imp == prefix or imp.startswith(prefix + ".")


def _resolve_import_to_cluster(imp: str, clusters: list[Cluster]) -> Cluster | None:
    """Return the most-specific cluster whose root prefix contains ``imp``.

    Matches ``imp`` against both ``root_prefix`` and its ``src.``-stripped
    form; picks the cluster with the longest matching prefix.
    """
    best: Cluster | None = None
    best_len = -1
    for c in clusters:
        for candidate in (c.root_prefix, _strip_src(c.root_prefix)):
            if _prefix_matches(imp, candidate):
                if len(candidate) > best_len:
                    best = c
                    best_len = len(candidate)
                break
    return best


def link_clusters(clusters: list[Cluster]) -> list[Link]:
    """Infer ``depends-on`` links between clusters from import edges.

    Args:
        clusters: Output from :func:`architecture_model.pipeline_v3.cluster.cluster_modules`.

    Returns:
        List of Links sorted by ``(from_cluster, to_cluster)``.
    """
    if not clusters:
        return []

    # (from_id, to_id) -> set of source module names contributing
    edges: dict[tuple[str, str], set[str]] = defaultdict(set)

    for src_cluster in clusters:
        for m in src_cluster.modules:
            for imp in m.imports:
                target = _resolve_import_to_cluster(imp, clusters)
                if target is None or target.id == src_cluster.id:
                    continue
                edges[(src_cluster.id, target.id)].add(m.name)

    links = [
        Link(from_cluster=f, to_cluster=t, weight=len(sources))
        for (f, t), sources in edges.items()
    ]
    links.sort(key=lambda l: (l.from_cluster, l.to_cluster))
    return links
