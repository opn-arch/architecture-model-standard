"""Tests for ArtifactSpec DAG + rebuild plan (T19)."""
from __future__ import annotations

import pytest

from architecture_model.lifecycle.artifact_dag import (
    ArtifactDAGCycle,
    BuildStep,
    MissingArtifactRef,
    RebuildPlan,
    build_artifact_dag,
    rebuild_plan,
)
from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef
from architecture_model.lifecycle.stale import StaleSet


def _view(vid: str = "v1", rev: str = "r1") -> ViewRef:
    return ViewRef(view_id=vid, model_revision=rev)


def _leaf(aid: str, renderer: str = "svg") -> ArtifactSpec:
    return ArtifactSpec(id=aid, renderer=renderer, view_ref=_view(aid))


def _zip(aid: str, refs: list[str]) -> ArtifactSpec:
    return ArtifactSpec(id=aid, renderer="zip", bundle_refs=refs)


# --- build_artifact_dag ------------------------------------------------


def test_build_dag_three_leaves_and_one_zip():
    a = _leaf("a", "svg")
    b = _leaf("b", "markdown")
    c = _leaf("c", "html")
    z = _zip("z", ["a", "b", "c"])
    dag = build_artifact_dag([a, b, c, z])
    order = dag.topological_order()
    # z must come after each of a, b, c
    assert order.index("z") > order.index("a")
    assert order.index("z") > order.index("b")
    assert order.index("z") > order.index("c")
    assert set(order) == {"a", "b", "c", "z"}


def test_build_dag_cycle_detected():
    # Both zips (each requires non-empty bundle_refs). Note this is contrived.
    z1 = _zip("z1", ["z2"])
    z2 = _zip("z2", ["z1"])
    with pytest.raises(ArtifactDAGCycle):
        build_artifact_dag([z1, z2])


def test_build_dag_missing_bundle_ref():
    a = _leaf("a")
    z = _zip("z", ["a", "does_not_exist"])
    with pytest.raises(MissingArtifactRef) as ei:
        build_artifact_dag([a, z])
    assert "does_not_exist" in str(ei.value)
    assert "z" in str(ei.value)


# --- rebuild_plan ------------------------------------------------------


def test_rebuild_plan_none_stale_full_rebuild_topological():
    a = _leaf("a", "svg")
    b = _leaf("b", "markdown")
    z = _zip("z", ["a", "b"])
    plan = rebuild_plan([a, b, z])
    assert isinstance(plan, RebuildPlan)
    ids = [s.artifact_id for s in plan.steps]
    assert set(ids) == {"a", "b", "z"}
    assert ids.index("z") > ids.index("a")
    assert ids.index("z") > ids.index("b")
    assert plan.skipped_up_to_date == ()


def test_rebuild_plan_stale_only_emits_relevant():
    a = _leaf("a", "svg")
    b = _leaf("b", "markdown")
    c = _leaf("c", "html")
    z = _zip("z", ["a", "b", "c"])
    stale = StaleSet(nodes=frozenset({"artifact:z", "artifact:a"}))
    plan = rebuild_plan([a, b, c, z], stale=stale)
    built_ids = {s.artifact_id for s in plan.steps}
    assert built_ids == {"a", "z"}
    assert set(plan.skipped_up_to_date) == {"b", "c"}


def test_rebuild_plan_output_path_extensions():
    svg = ArtifactSpec(id="s", renderer="svg", view_ref=_view("v"))
    md = ArtifactSpec(id="m", renderer="markdown", view_ref=_view("v"))
    html = ArtifactSpec(id="h", renderer="html", view_ref=_view("v"))
    ai = ArtifactSpec(id="ai", renderer="ai-context", view_ref=_view("v"))
    zp = _zip("zp", ["s"])
    plan = rebuild_plan([svg, md, html, ai, zp], output_dir="build")
    by_id = {s.artifact_id: s for s in plan.steps}
    assert by_id["s"].output_path == "build/s.svg"
    assert by_id["m"].output_path == "build/m.md"
    assert by_id["h"].output_path == "build/h.html"
    assert by_id["ai"].output_path == "build/ai.txt"
    assert by_id["zp"].output_path == "build/zp.zip"


def test_rebuild_plan_inputs_populated_for_zip_and_empty_for_leaf():
    a = _leaf("a")
    b = _leaf("b")
    z = _zip("z", ["b", "a"])  # unsorted bundle_refs
    plan = rebuild_plan([a, b, z])
    by_id = {s.artifact_id: s for s in plan.steps}
    assert by_id["a"].inputs == ()
    assert by_id["b"].inputs == ()
    # inputs sorted regardless of bundle_refs order
    assert by_id["z"].inputs == ("a", "b")
    assert by_id["z"].bundle_refs == ("b", "a")


def test_rebuild_plan_deterministic():
    a = _leaf("a")
    b = _leaf("b")
    c = _leaf("c")
    z = _zip("z", ["c", "a", "b"])
    p1 = rebuild_plan([z, c, b, a])
    p2 = rebuild_plan([a, b, c, z])
    assert [s.artifact_id for s in p1.steps] == [s.artifact_id for s in p2.steps]
    assert p1 == p2


def test_build_step_kind_matches_renderer():
    a = _leaf("a", "svg")
    z = _zip("z", ["a"])
    plan = rebuild_plan([a, z])
    by_id = {s.artifact_id: s for s in plan.steps}
    assert by_id["a"].kind == "svg"
    assert by_id["z"].kind == "zip"
    assert by_id["a"].view_ref is not None
    assert by_id["z"].view_ref is None
    assert by_id["z"].bundle_refs == ("a",)
