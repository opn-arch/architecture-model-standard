"""Tests for pipeline_v3.verify — T0.14 Phase 6.6.

verify.py runs chain-closure over a ContainerizedModel, invoking the
existing quality.chain_closure engine. Two entry points:

    verify_model(model, *, root_owner_ids=None) -> ChainClosureReport
    verify_per_component(model, *, root_owner_ids=None) -> dict[str, ChainClosureReport]

Root owners default to *every component* — after containerize, every
Promise's owner IS a component; there is no higher entity for them to
be delivered from. verify uses component ids as roots when the caller
does not override.
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.pipeline_v3.cluster import cluster_modules
from architecture_model.pipeline_v3.containerize import containerize
from architecture_model.pipeline_v3.derive_promises import derive_promises
from architecture_model.pipeline_v3.link import link_clusters
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult
from architecture_model.pipeline_v3.verify import (
    verify_model,
    verify_per_component,
)
from architecture_model.quality.chain_closure import (
    GAP_DELIVERY,
    GAP_OPEN_Q,
    GAP_VERIFY,
    ChainClosureReport,
)


_SENTINEL = object()


def _mod(
    name: str,
    docstring: str | None = "d",
    functions=_SENTINEL,
    imports: list[str] | None = None,
) -> ScannedModule:
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


def _model(*modules: ScannedModule, depth: int = 2):
    scan = ScanResult(source_root=Path("/tmp"), modules=list(modules))
    clusters = cluster_modules(scan, depth=depth)
    ps = derive_promises(scan)
    links = link_clusters(clusters)
    return containerize(clusters, ps, links)


# ---------------------------------------------------------------------------
# verify_model
# ---------------------------------------------------------------------------


def test_verify_model_returns_chain_closure_report():
    model = _model(_mod("a.b.x"))
    report = verify_model(model)
    assert isinstance(report, ChainClosureReport)


def test_verify_model_counts_total_promises():
    model = _model(_mod("a.b.x"))
    report = verify_model(model)
    total = sum(len(c.promises) for c in model.components)
    assert report.total_promises == total


def test_verify_model_uses_component_ids_as_roots_by_default():
    """After containerize, every Promise owner IS a component. When no
    explicit roots are given, verify should treat all component ids as
    roots so open Promises don't spuriously flag G-DELIVERY."""
    model = _model(_mod("a.b.x", docstring="hi"))
    report = verify_model(model)
    # The intent Promise is open with no delivered_from; owner=comp.id.
    # With component ids as roots, that must NOT produce G-DELIVERY.
    delivery_gaps = [g for g in report.gaps if g.gap == GAP_DELIVERY]
    assert delivery_gaps == []


def test_verify_model_flags_verify_gap_on_open_promise():
    """A non-typed-gap Promise with no verified_by should produce G-VERIFY."""
    model = _model(_mod("a.b.x", docstring="hi"))
    report = verify_model(model)
    verify_gaps = [g for g in report.gaps if g.gap == GAP_VERIFY]
    # intent + delivers + provides are all OPEN and have no verified_by
    assert len(verify_gaps) >= 1


def test_verify_model_typed_gap_is_not_flagged():
    """TYPED_GAP promises are named absences, not gaps to close."""
    model = _model(_mod("a.b.x", docstring=None, functions=[]))
    report = verify_model(model)
    # intent + delivers = 2 typed gaps; provides is also typed (no classes)
    # None should appear in gaps list
    for g in report.gaps:
        pids = {p.id for c in model.components for p in c.promises
                if p.status.value == "typed-gap"}
        assert g.promise_id not in pids


def test_verify_model_explicit_root_owner_override():
    """Caller can override root set (e.g. for testing external actors)."""
    model = _model(_mod("a.b.x", docstring="hi"))
    # Empty root set → EVERY open Promise flags G-DELIVERY
    report = verify_model(model, root_owner_ids=frozenset())
    delivery_gaps = [g for g in report.gaps if g.gap == GAP_DELIVERY]
    assert len(delivery_gaps) > 0


def test_verify_model_empty_model():
    empty = _model()
    report = verify_model(empty)
    assert report.total_promises == 0
    assert report.gaps == []


def test_verify_model_closure_pct_is_in_range():
    model = _model(_mod("a.b.x"))
    report = verify_model(model)
    assert 0.0 <= report.closure_pct <= 100.0


# ---------------------------------------------------------------------------
# verify_per_component
# ---------------------------------------------------------------------------


def test_verify_per_component_returns_dict_keyed_by_component_id():
    model = _model(_mod("a.b.x"), _mod("a.c.y"))
    per = verify_per_component(model)
    assert isinstance(per, dict)
    assert set(per) == {c.id for c in model.components}
    for report in per.values():
        assert isinstance(report, ChainClosureReport)


def test_verify_per_component_counts_only_that_components_promises():
    model = _model(_mod("a.b.x"), _mod("a.c.y"))
    per = verify_per_component(model)
    for comp in model.components:
        assert per[comp.id].total_promises == len(comp.promises)


def test_verify_per_component_uses_per_component_root_by_default():
    """Each component's report treats only its own id as the root — so
    open Promises within that component don't flag G-DELIVERY."""
    model = _model(_mod("a.b.x", docstring="hi"))
    per = verify_per_component(model)
    for report in per.values():
        assert not any(g.gap == GAP_DELIVERY for g in report.gaps)


def test_verify_per_component_empty_model_returns_empty_dict():
    assert verify_per_component(_model()) == {}
