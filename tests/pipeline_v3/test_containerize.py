"""Tests for pipeline_v3.containerize — T0.14 Phase 6.5.

containerize packages Clusters + module-owned Promises + Links into a
ContainerizedModel: a coherent v3-shape where Promises are re-owned by
their containing component (cluster) rather than their source module.

Rebinding rules:
    - Each module-owned Promise is re-emitted with owner_entity = cluster.id.
    - Because owner_entity changes, the Promise id is recomputed (per
      compute_promise_id's identity triple).
    - Identical rebound Promises within the same cluster collapse (same id).
    - source_module is captured in provenance for auditability.
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.core.promise import Promise, PromiseStatus, compute_promise_id
from architecture_model.pipeline_v3.cluster import Cluster, cluster_modules
from architecture_model.pipeline_v3.containerize import (
    ContainerizedComponent,
    ContainerizedModel,
    containerize,
)
from architecture_model.pipeline_v3.derive_promises import derive_promises
from architecture_model.pipeline_v3.link import link_clusters
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult


_SENTINEL = object()


def _mod(name: str, docstring: str | None = "d",
         functions=_SENTINEL,
         imports: list[str] | None = None) -> ScannedModule:
    if functions is _SENTINEL:
        functions = [{"name": "f"}]
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring=docstring,
        functions=functions,
        classes=[],
        imports=imports or [],
        line_count=1,
    )


def _pipeline(scan: ScanResult, *, depth: int = 3):
    clusters = cluster_modules(scan, depth=depth)
    promises = derive_promises(scan)
    links = link_clusters(clusters)
    return clusters, promises, links


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------


def test_containerize_returns_model_with_components_and_relationships():
    scan = ScanResult(source_root=Path("/tmp"), modules=[_mod("a.b.x")])
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    assert isinstance(model, ContainerizedModel)
    assert isinstance(model.components, list)
    assert isinstance(model.relationships, list)


def test_containerize_produces_one_component_per_cluster():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[_mod("a.b.x"), _mod("a.c.y")],
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    assert len(model.components) == len(clusters)
    assert {c.id for c in model.components} == {c.id for c in clusters}


def test_component_carries_name_root_prefix_and_module_names():
    scan = ScanResult(source_root=Path("/tmp"), modules=[_mod("a.b.x"), _mod("a.b.y")])
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    comp = model.components[0]
    assert comp.name == "b"
    assert comp.root_prefix == "a.b"
    assert comp.module_names == ["a.b.x", "a.b.y"]  # sorted


# ---------------------------------------------------------------------------
# Promise rebinding
# ---------------------------------------------------------------------------


def test_promises_are_rebound_to_component_ownership():
    scan = ScanResult(source_root=Path("/tmp"), modules=[_mod("a.b.x")])
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    comp = model.components[0]
    for p in comp.promises:
        assert p.owner_entity == comp.id
        # id is recomputed against new owner
        assert p.id == compute_promise_id(p.attribute, p.content, comp.id)


def test_rebound_promises_preserve_status_gap_type_content():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[_mod("a.b.x", docstring=None, functions=[])],  # both gaps
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    comp = model.components[0]
    by_attr = {p.attribute: p for p in comp.promises}
    intent = by_attr["intent"]
    delivers = by_attr["delivers"]
    assert intent.status == PromiseStatus.TYPED_GAP
    assert intent.gap_type == "missing-intent"
    assert intent.content == ""
    assert delivers.status == PromiseStatus.TYPED_GAP
    assert delivers.gap_type == "no-public-functions"


def test_identical_rebound_promises_collapse_within_cluster():
    """Two modules with identical typed-gap Promises (same attribute, empty
    content, same cluster owner) collapse to one after rebinding."""
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[
            _mod("a.b.x", docstring=None, functions=[]),
            _mod("a.b.y", docstring=None, functions=[]),
        ],
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    comp = model.components[0]
    # 2 modules × 3 attrs = 6 raw; after cluster rebind + dedup,
    # all three gaps collapse to one each → 3
    ids = [p.id for p in comp.promises]
    assert len(ids) == len(set(ids))
    assert len(comp.promises) == 3


def test_promise_provenance_captures_source_modules():
    scan = ScanResult(source_root=Path("/tmp"), modules=[_mod("a.b.x", docstring="hi")])
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    comp = model.components[0]
    intent = next(p for p in comp.promises if p.attribute == "intent")
    assert "a.b.x" in intent.provenance
    assert "containerize" in intent.provenance


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def test_relationships_are_passed_through():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[
            _mod("a.b.x", imports=["a.c.y"]),
            _mod("a.c.y"),
        ],
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    assert model.relationships == links


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_containerize_output_is_deterministic():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[_mod("a.b.x"), _mod("a.b.y"), _mod("a.c.z")],
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    m1 = containerize(clusters, ps, links)
    m2 = containerize(clusters, ps, links)
    ids1 = [c.id for c in m1.components]
    ids2 = [c.id for c in m2.components]
    assert ids1 == ids2
    for c1, c2 in zip(m1.components, m2.components):
        assert [p.id for p in c1.promises] == [p.id for p in c2.promises]


def test_containerize_component_ordering_matches_cluster_ordering():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[_mod("z.a.m"), _mod("a.a.m"), _mod("m.a.m")],
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    assert [c.id for c in model.components] == [c.id for c in clusters]


def test_containerize_empty_inputs():
    model = containerize([], [], [])
    assert model.components == []
    assert model.relationships == []


def test_containerize_promises_within_component_sorted_by_attribute():
    scan = ScanResult(source_root=Path("/tmp"), modules=[_mod("a.b.x", docstring="d")])
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    attrs = [p.attribute for p in model.components[0].promises]
    assert attrs == sorted(attrs)


# ---------------------------------------------------------------------------
# R9: behavior intent Promise attachment
# ---------------------------------------------------------------------------


def test_containerize_attaches_intent_promise_to_each_behavior():
    """Each ContainerizedBehavior carries a promises list containing at
    least an intent Promise derived from its description."""
    from architecture_model.pipeline_v3.derive_behaviors import (
        BehaviorCandidate,
        derive_behaviors,
    )

    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[
            _mod(
                "a.b.x",
                docstring="mod",
                functions=[
                    {"name": "scan_repo", "docstring": "Scan a repository."}
                ],
            ),
        ],
    )
    clusters, ps, links = _pipeline(scan, depth=2)
    behaviors = derive_behaviors(scan)
    model = containerize(clusters, ps, links, behaviors=behaviors)
    assert len(model.behaviors) == 1
    beh = model.behaviors[0]
    assert hasattr(beh, "promises")
    intents = [p for p in beh.promises if p.attribute == "intent"]
    assert len(intents) == 1
    assert intents[0].content == "Scan a repository."
    assert intents[0].owner_entity == beh.id


def test_containerize_behavior_promises_empty_when_no_behaviors_passed():
    """Backward-compat: containerize called without behaviors still works
    (behaviors list is empty; nothing to attach)."""
    scan = ScanResult(source_root=Path("/tmp"), modules=[_mod("a.b.x")])
    clusters, ps, links = _pipeline(scan, depth=2)
    model = containerize(clusters, ps, links)
    assert model.behaviors == []
