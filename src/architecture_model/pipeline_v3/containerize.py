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
from architecture_model.pipeline_v3.derive_behaviors import (
    BehaviorCandidate,
    derive_promises_for_behavior,
)
from architecture_model.pipeline_v3.derive_triggers import TriggerEdge
from architecture_model.pipeline_v3.link import Link

__all__ = [
    "ContainerizedBehavior",
    "ContainerizedComponent",
    "ContainerizedModel",
    "containerize",
]

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
class ContainerizedBehavior:
    """A v3 behavior rebound to its owning component (Part 17a1).

    Attributes:
        id: The ``BEH-<sha1[:8]>`` id carried over from the
            :class:`BehaviorCandidate` (identity is module+function-
            derived, not component-derived, so ids survive
            rebinding without recomputation).
        name: Function name.
        description: First docstring line.
        owner_component: Component (cluster) id that owns the source
            module. Empty string if the source module was not resolved
            to any cluster (defensive; should not occur in practice).
        owner_module: Original source module dotted name.
        function_name: Source symbol name.
        class_name: Owning class name if the source was a method,
            otherwise ``None``.
        promises: Promises owned by this behavior (R9). Populated by
            :func:`containerize` via :func:`derive_promises_for_behavior`.
            Sorted by ``(attribute, id)`` for stable YAML output.
    """

    id: str
    name: str
    description: str
    owner_component: str
    owner_module: str
    function_name: str
    class_name: str | None = None
    promises: tuple[Promise, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ContainerizedModel:
    """A v3 model ready for chain-closure verification and YAML emit."""

    components: list[ContainerizedComponent] = field(default_factory=list)
    relationships: list[Link] = field(default_factory=list)
    behaviors: list[ContainerizedBehavior] = field(default_factory=list)


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
    behaviors: list[BehaviorCandidate] | None = None,
    trigger_edges: list[TriggerEdge] | None = None,
) -> ContainerizedModel:
    """Compose scan/derive/cluster/link outputs into a v3-shaped model.

    Args:
        clusters: Output of :func:`architecture_model.pipeline_v3.cluster.cluster_modules`.
        promises: Output of :func:`architecture_model.pipeline_v3.derive_promises.derive_promises`
            (Promises owned by module dotted names).
        relationships: Output of :func:`architecture_model.pipeline_v3.link.link_clusters`.
        behaviors: Optional list of BehaviorCandidates from
            :func:`architecture_model.pipeline_v3.derive_behaviors.derive_behaviors`.
            When provided, each candidate is rebound to its owning
            cluster and one ``traces-to`` :class:`Link`
            (component → behavior) is emitted per behavior.
        trigger_edges: Optional list of :class:`TriggerEdge` values
            from :func:`architecture_model.pipeline_v3.derive_triggers.derive_triggers`.
            Each edge is emitted as a BEH→BEH :class:`Link` with
            ``kind="triggers"``. Edges whose endpoints did not survive
            behavior rebinding (e.g. source module not in any cluster)
            are silently dropped.

    Returns:
        A :class:`ContainerizedModel` with Promises rebound to component
        ownership. Relationships carry through unchanged plus any
        ``traces-to`` edges (from behaviors) and ``triggers`` edges
        (from trigger_edges).
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

    # Rebind behaviors + emit traces-to edges.
    #
    # Composite call-chain assembly (Part 17a4): every source behavior
    # whose outgoing trigger edges carry ``sequence`` values is treated
    # as composite. Build ``composite_chains`` = ``{src_id: (tgt_id,
    # tgt_id, ...)}`` sorted by sequence so we can attach the ordered
    # downstream ids to the composite's outgoing ``traces-to`` edge.
    # Uses the raw ``trigger_edges`` (pre-survivorship-filter) so the
    # chain reflects the source function's intent even if some target
    # behaviors were dropped later. Target-survivorship checks happen
    # separately when emitting the ``triggers`` edges themselves.
    composite_chains: dict[str, tuple[str, ...]] = {}
    if trigger_edges:
        _by_src: dict[str, list[TriggerEdge]] = {}
        for e in trigger_edges:
            if e.sequence is not None:
                _by_src.setdefault(e.from_behavior, []).append(e)
        for src_id, edges in _by_src.items():
            ordered = sorted(edges, key=lambda e: e.sequence)  # type: ignore[arg-type,return-value]
            composite_chains[src_id] = tuple(e.to_behavior for e in ordered)

    rebound_behaviors: list[ContainerizedBehavior] = []
    traces_to_edges: list[Link] = []
    for cand in behaviors or []:
        target = module_to_cluster.get(cand.owner_module)
        if target is None:
            # Source module wasn't in any cluster — skip silently to
            # mirror the promise-rebinding contract above.
            continue
        rebound_behaviors.append(
            ContainerizedBehavior(
                id=cand.id,
                name=cand.name,
                description=cand.description,
                owner_component=target.id,
                owner_module=cand.owner_module,
                function_name=cand.function_name,
                class_name=cand.class_name,
                promises=tuple(
                    sorted(
                        derive_promises_for_behavior(cand),
                        key=lambda p: (p.attribute, p.id),
                    )
                ),
            )
        )
        traces_to_edges.append(
            Link(
                from_cluster=target.id,
                to_cluster=cand.id,
                kind="traces-to",
                weight=1,
                call_chain=composite_chains.get(cand.id),
            )
        )

    rebound_behaviors.sort(key=lambda b: b.id)

    # Trigger edges: emit BEH→BEH ``triggers`` Links, but only when both
    # endpoints correspond to behaviors that survived rebinding (i.e.
    # their owner module was resolved to a cluster). This mirrors the
    # silent-drop semantics of promise + behavior rebinding above.
    surviving_behavior_ids = {b.id for b in rebound_behaviors}
    trigger_links: list[Link] = []
    for edge in trigger_edges or []:
        if (
            edge.from_behavior in surviving_behavior_ids
            and edge.to_behavior in surviving_behavior_ids
        ):
            trigger_links.append(
                Link(
                    from_cluster=edge.from_behavior,
                    to_cluster=edge.to_behavior,
                    kind="triggers",
                    weight=1,
                    sequence=edge.sequence,
                )
            )

    combined_relationships = list(relationships) + traces_to_edges + trigger_links

    return ContainerizedModel(
        components=components,
        relationships=combined_relationships,
        behaviors=rebound_behaviors,
    )
