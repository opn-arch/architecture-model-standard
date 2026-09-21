"""Tests for pipeline_v3 behavior emission across containerize + publish
(Part 17a1).

Covers:
    - containerize() accepts behaviors=None (backward compat, existing
      call sites unaffected).
    - containerize() with behaviors emits ContainerizedBehavior with
      owner_component rebound to the owning cluster.
    - containerize() emits one traces-to Link per behavior.
    - Behavior with unresolved owner_module is silently skipped.
    - publish emits entities.behaviors when non-empty; omits when empty.
    - publish sorts behaviors by id; traces-to relationships flow through.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from architecture_model.pipeline_v3.cluster import Cluster
from architecture_model.pipeline_v3.containerize import (
    ContainerizedBehavior,
    ContainerizedModel,
    containerize,
)
from architecture_model.pipeline_v3.derive_behaviors import BehaviorCandidate
from architecture_model.pipeline_v3.derive_triggers import TriggerEdge
from architecture_model.pipeline_v3.link import Link
from architecture_model.pipeline_v3.publish import serialize_model
from architecture_model.pipeline_v3.scan import ScannedModule


def _mod(name: str) -> ScannedModule:
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring=None,
        functions=[],
        classes=[],
        imports=[],
        line_count=0,
    )


def _cluster(cid: str, prefix: str, modules: list[str]) -> Cluster:
    return Cluster(
        id=cid,
        name=prefix,
        root_prefix=prefix,
        modules=[_mod(m) for m in modules],
    )


def _cand(module: str, fname: str) -> BehaviorCandidate:
    from architecture_model.pipeline_v3.derive_behaviors import _behavior_id
    return BehaviorCandidate(
        id=_behavior_id(module, fname),
        name=fname,
        description=f"Do {fname}.",
        owner_module=module,
        function_name=fname,
    )


# ---------------------------------------------------------------------------
# containerize behavior handling
# ---------------------------------------------------------------------------


def test_containerize_accepts_no_behaviors_default():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    model = containerize(clusters, [], [])
    assert model.behaviors == []
    # Traces-to edges absent when no behaviors provided
    assert all(r.kind != "traces-to" for r in model.relationships)


def test_containerize_rebinds_behavior_owner_to_component():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    cand = _cand("pkg.a.x", "scan_repo")
    model = containerize(clusters, [], [], [cand])
    assert len(model.behaviors) == 1
    b = model.behaviors[0]
    assert b.owner_component == "COMP-1"
    assert b.owner_module == "pkg.a.x"
    assert b.id == cand.id  # id survives rebinding


def test_containerize_emits_traces_to_edge_per_behavior():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    cand = _cand("pkg.a.x", "scan_repo")
    model = containerize(clusters, [], [], [cand])
    traces = [r for r in model.relationships if r.kind == "traces-to"]
    assert len(traces) == 1
    assert traces[0].from_cluster == "COMP-1"
    assert traces[0].to_cluster == cand.id


def test_containerize_skips_behavior_with_unresolved_module():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    orphan = _cand("pkg.z.unknown", "f")
    model = containerize(clusters, [], [], [orphan])
    assert model.behaviors == []
    assert all(r.kind != "traces-to" for r in model.relationships)


def test_containerize_behaviors_sorted_by_id():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    cands = [
        _cand("pkg.a.x", "zeta"),
        _cand("pkg.a.x", "alpha"),
        _cand("pkg.a.x", "mu"),
    ]
    model = containerize(clusters, [], [], cands)
    ids = [b.id for b in model.behaviors]
    assert ids == sorted(ids)


def test_containerize_preserves_existing_relationships_alongside_traces_to():
    clusters = [
        _cluster("COMP-1", "pkg.a", ["pkg.a.x"]),
        _cluster("COMP-2", "pkg.b", ["pkg.b.y"]),
    ]
    existing = [Link(from_cluster="COMP-1", to_cluster="COMP-2")]
    cand = _cand("pkg.a.x", "f")
    model = containerize(clusters, [], existing, [cand])
    kinds = sorted(r.kind for r in model.relationships)
    assert kinds == ["depends-on", "traces-to"]


# ---------------------------------------------------------------------------
# publish YAML shape
# ---------------------------------------------------------------------------


def test_publish_omits_behaviors_key_when_empty():
    model = ContainerizedModel(components=[], relationships=[], behaviors=[])
    doc = yaml.safe_load(serialize_model(model))
    assert "behaviors" not in doc["entities"]


def test_publish_includes_behaviors_when_present():
    b = ContainerizedBehavior(
        id="BEH-abc12345",
        name="scan",
        description="Scan repo.",
        owner_component="COMP-1",
        owner_module="pkg.a.x",
        function_name="scan",
    )
    model = ContainerizedModel(
        components=[], relationships=[], behaviors=[b]
    )
    doc = yaml.safe_load(serialize_model(model))
    assert "behaviors" in doc["entities"]
    assert doc["entities"]["behaviors"] == [
        {
            "id": "BEH-abc12345",
            "name": "scan",
            "description": "Scan repo.",
            "owner_component": "COMP-1",
            "owner_module": "pkg.a.x",
            "function_name": "scan",
        }
    ]


def test_publish_behaviors_sorted_by_id():
    behaviors = [
        ContainerizedBehavior(
            id=f"BEH-{n:08x}",
            name=f"b{n}",
            description=f"B{n}.",
            owner_component="COMP-1",
            owner_module="pkg.a",
            function_name=f"b{n}",
        )
        for n in (3, 1, 2)
    ]
    model = ContainerizedModel(
        components=[], relationships=[], behaviors=behaviors
    )
    doc = yaml.safe_load(serialize_model(model))
    ids = [b["id"] for b in doc["entities"]["behaviors"]]
    assert ids == sorted(ids)


def test_publish_includes_class_name_only_when_set():
    b_no_class = ContainerizedBehavior(
        id="BEH-11111111",
        name="f",
        description="F.",
        owner_component="COMP-1",
        owner_module="pkg.a",
        function_name="f",
    )
    b_with_class = ContainerizedBehavior(
        id="BEH-22222222",
        name="run",
        description="R.",
        owner_component="COMP-1",
        owner_module="pkg.a",
        function_name="run",
        class_name="Runner",
    )
    model = ContainerizedModel(
        components=[], relationships=[], behaviors=[b_no_class, b_with_class]
    )
    doc = yaml.safe_load(serialize_model(model))
    beh_dicts = doc["entities"]["behaviors"]
    assert "class_name" not in beh_dicts[0]
    assert beh_dicts[1]["class_name"] == "Runner"


def test_publish_traces_to_relationships_serialized_with_type():
    model = ContainerizedModel(
        components=[],
        relationships=[
            Link(from_cluster="COMP-1", to_cluster="BEH-abc12345",
                 kind="traces-to", weight=1),
        ],
        behaviors=[],
    )
    doc = yaml.safe_load(serialize_model(model))
    assert doc["relationships"] == [
        {
            "from": "COMP-1",
            "to": "BEH-abc12345",
            "type": "traces-to",
            "weight": 1,
        }
    ]


# ---------------------------------------------------------------------------
# Part 17a2: trigger edge emission through containerize
# ---------------------------------------------------------------------------


def test_containerize_emits_triggers_edge_beh_to_beh():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    src = _cand("pkg.a.x", "caller")
    dst = _cand("pkg.a.x", "callee")
    trig = TriggerEdge(from_behavior=src.id, to_behavior=dst.id)
    model = containerize(clusters, [], [], [src, dst], [trig])
    triggers = [r for r in model.relationships if r.kind == "triggers"]
    assert len(triggers) == 1
    assert triggers[0].from_cluster == src.id
    assert triggers[0].to_cluster == dst.id


def test_containerize_skips_trigger_when_endpoint_not_containerized():
    # ``dst`` behavior's owner module isn't in any cluster → dst does
    # not survive rebinding → trigger edge is silently dropped.
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    src = _cand("pkg.a.x", "caller")
    orphan_dst = _cand("pkg.z.unknown", "callee")
    trig = TriggerEdge(from_behavior=src.id, to_behavior=orphan_dst.id)
    model = containerize(clusters, [], [], [src, orphan_dst], [trig])
    assert all(r.kind != "triggers" for r in model.relationships)


def test_containerize_accepts_no_triggers_default():
    clusters = [_cluster("COMP-1", "pkg.a", ["pkg.a.x"])]
    model = containerize(clusters, [], [], [_cand("pkg.a.x", "f")])
    assert all(r.kind != "triggers" for r in model.relationships)
