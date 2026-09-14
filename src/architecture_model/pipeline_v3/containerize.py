"""pipeline_v3.containerize — Component packaging stage (T0.14 Phase 6.5).

Composes the outputs of :mod:`scan`, :mod:`derive_promises`, :mod:`cluster`,
and :mod:`link` into a coherent :class:`ContainerizedModel` — the v3 shape
consumed by :mod:`verify` (chain-closure) and :mod:`publish` (YAML emit).

Core operation: **Promise ownership rebinding**
------------------------------------------------

``derive_promises`` produces Promises owned by *modules* (dotted names).
v3 architecture entities are *components*, not modules. Containerize
walks each cluster, rebinds every Promise owned by one of its member
modules to ``owner_entity = cluster.id``, and recomputes the Promise id
against the new owner via :func:`compute_promise_id`.

Because the identity triple ``(attribute, content, owner)`` changes, ids
change. Two Promises that were distinct at the module level but become
identical at the component level (e.g. both modules had
``delivers=[]`` typed-gap) collapse to one record via id-set dedup.

Provenance is enriched to capture the originating module(s) so audit
tools can trace a component-level Promise back to its module sources.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace

from architecture_model.core.promise import Promise, compute_promise_id
from architecture_model.pipeline_v3.cluster import Cluster
from architecture_model.pipeline_v3.link import Link

__all__ = ["ContainerizedComponent", "ContainerizedModel", "containerize"]

_PROVENANCE = "pipeline_v3.containerize"


@dataclass(frozen=True)
class ContainerizedComponent:
    """A v3 component: a Cluster with its rebound Promises attached."""

    id: str
    name: str
    root_prefix: str
    module_names: list[str] = field(default_factory=list)
    promises: list[Promise] = field(default_factory=list)


@dataclass(frozen=True)
class ContainerizedModel:
    """A v3 model ready for chain-closure verification and YAML emit."""

    components: list[ContainerizedComponent] = field(default_factory=list)
    relationships: list[Link] = field(default_factory=list)


def _rebind_promise(p: Promise, new_owner: str) -> Promise:
    """Rebind ``p`` to ``new_owner``, recomputing id and enriching provenance.

    Preserves attribute, content, status, gap_type, delivered_from,
    verified_by unchanged. Enriches ``provenance`` with the containerize
    stage tag and the original module owner for audit traceability.
    """
    new_id = compute_promise_id(p.attribute, p.content, new_owner)
    original_owner = p.owner_entity
    prior_provenance = p.provenance or ""
    new_provenance = f"{_PROVENANCE}; src={original_owner}; via={prior_provenance}"
    return replace(
        p,
        owner_entity=new_owner,
        id=new_id,
        provenance=new_provenance,
    )


def containerize(
    clusters: list[Cluster],
    promises: list[Promise],
    relationships: list[Link],
) -> ContainerizedModel:
    """Compose scan/derive/cluster/link outputs into a v3-shaped model.

    Args:
        clusters: Output of :func:`architecture_model.pipeline_v3.cluster.cluster_modules`.
        promises: Output of :func:`architecture_model.pipeline_v3.derive_promises.derive_promises`
            (Promises owned by module dotted names).
        relationships: Output of :func:`architecture_model.pipeline_v3.link.link_clusters`.

    Returns:
        A :class:`ContainerizedModel` with Promises rebound to component
        ownership. Relationships pass through unchanged (they already
        speak in cluster ids).
    """
    # Build reverse index: module name → cluster
    module_to_cluster: dict[str, Cluster] = {}
    for c in clusters:
        for m in c.modules:
            module_to_cluster[m.name] = c

    # Group promises by target cluster, rebinding + dedup
    per_cluster: dict[str, dict[str, Promise]] = defaultdict(dict)
    for p in promises:
        target = module_to_cluster.get(p.owner_entity)
        if target is None:
            # Module wasn't in any cluster (should not happen given the same
            # scan drove both); silently skip rather than corrupt the model.
            continue
        rebound = _rebind_promise(p, target.id)
        # Dedup by id (natural collapse of identical rebound Promises)
        per_cluster[target.id][rebound.id] = rebound

    components: list[ContainerizedComponent] = []
    for c in clusters:
        prom_map = per_cluster.get(c.id, {})
        promises_sorted = sorted(prom_map.values(), key=lambda p: (p.attribute, p.id))
        components.append(
            ContainerizedComponent(
                id=c.id,
                name=c.name,
                root_prefix=c.root_prefix,
                module_names=sorted(m.name for m in c.modules),
                promises=promises_sorted,
            )
        )

    return ContainerizedModel(components=components, relationships=list(relationships))
