"""Tests for pipeline_v3.derive_promises — T0.14 Phase 6.2.

derive_promises consumes a ScanResult and produces list[Promise] using the
Promise shape from Phase 1. Each ScannedModule contributes three Promises
(one per canonical scan-derived attribute):

    - intent    ← module docstring (TYPED_GAP: missing-intent when absent)
    - delivers  ← list of public function names (TYPED_GAP: no-public-functions)
    - provides  ← list of public class names   (TYPED_GAP: no-public-classes)

"Public" = name does not start with underscore. Owner entity = module's
dotted name (as computed by scan._dotted_name).
"""

from __future__ import annotations

from architecture_model.core.promise import Promise, PromiseStatus, compute_promise_id
from architecture_model.pipeline_v3.derive_promises import (
    derive_promises,
    derive_promises_for_module,
)
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult
from pathlib import Path


def _mod(
    name: str,
    docstring: str | None = None,
    functions: list[dict] | None = None,
    classes: list[dict] | None = None,
) -> ScannedModule:
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring=docstring,
        functions=functions or [],
        classes=classes or [],
        imports=[],
        line_count=0,
    )


# ---------------------------------------------------------------------------
# Per-module derivation
# ---------------------------------------------------------------------------


def test_derive_module_with_docstring_produces_intent_open():
    m = _mod("pkg.core", docstring="Core reality-scan bridge.")
    ps = derive_promises_for_module(m)
    intents = [p for p in ps if p.attribute == "intent"]
    assert len(intents) == 1
    p = intents[0]
    assert p.status == PromiseStatus.OPEN
    assert p.content == "Core reality-scan bridge."
    assert p.owner_entity == "pkg.core"
    assert p.gap_type is None


def test_derive_module_without_docstring_produces_intent_gap():
    m = _mod("pkg.core", docstring=None)
    ps = derive_promises_for_module(m)
    p = next(x for x in ps if x.attribute == "intent")
    assert p.status == PromiseStatus.TYPED_GAP
    assert p.gap_type == "missing-intent"
    assert p.content == ""


def test_derive_module_with_functions_produces_delivers_open():
    m = _mod(
        "pkg.core",
        functions=[
            {"name": "public_a"},
            {"name": "_private"},
            {"name": "public_b"},
        ],
    )
    ps = derive_promises_for_module(m)
    p = next(x for x in ps if x.attribute == "delivers")
    assert p.status == PromiseStatus.OPEN
    # public only, sorted for determinism
    assert p.content == ["public_a", "public_b"]


def test_derive_module_without_public_functions_produces_delivers_gap():
    m = _mod("pkg.core", functions=[{"name": "_only_private"}])
    ps = derive_promises_for_module(m)
    p = next(x for x in ps if x.attribute == "delivers")
    assert p.status == PromiseStatus.TYPED_GAP
    assert p.gap_type == "no-public-functions"
    assert p.content == []


def test_derive_module_with_classes_produces_provides_open():
    m = _mod(
        "pkg.core",
        classes=[
            {"name": "PublicX"},
            {"name": "_Private"},
            {"name": "PublicA"},
        ],
    )
    ps = derive_promises_for_module(m)
    p = next(x for x in ps if x.attribute == "provides")
    assert p.status == PromiseStatus.OPEN
    assert p.content == ["PublicA", "PublicX"]


def test_derive_module_without_public_classes_produces_provides_gap():
    m = _mod("pkg.core", classes=[{"name": "_Hidden"}])
    ps = derive_promises_for_module(m)
    p = next(x for x in ps if x.attribute == "provides")
    assert p.status == PromiseStatus.TYPED_GAP
    assert p.gap_type == "no-public-classes"


def test_derive_module_produces_exactly_three_promises_per_attribute():
    m = _mod("pkg.core", docstring="d", functions=[{"name": "f"}], classes=[{"name": "C"}])
    ps = derive_promises_for_module(m)
    attrs = sorted(p.attribute for p in ps)
    assert attrs == ["delivers", "intent", "provides"]


def test_derive_ids_are_deterministic():
    m = _mod("pkg.core", docstring="d")
    ps1 = derive_promises_for_module(m)
    ps2 = derive_promises_for_module(m)
    assert [p.id for p in ps1] == [p.id for p in ps2]


def test_derive_id_matches_compute_promise_id():
    m = _mod("pkg.core", docstring="hello")
    p = next(x for x in derive_promises_for_module(m) if x.attribute == "intent")
    assert p.id == compute_promise_id("intent", "hello", "pkg.core")


def test_derive_owner_entity_is_module_dotted_name():
    m = _mod("pkg.sub.mod", docstring="d")
    for p in derive_promises_for_module(m):
        assert p.owner_entity == "pkg.sub.mod"


def test_derive_provenance_is_stamped():
    m = _mod("pkg.core", docstring="d")
    p = derive_promises_for_module(m)[0]
    assert "pipeline_v3.derive_promises" in p.provenance


# ---------------------------------------------------------------------------
# Whole ScanResult derivation
# ---------------------------------------------------------------------------


def test_derive_promises_on_scan_result_returns_flat_list():
    scan = ScanResult(
        source_root=Path("/tmp/repo"),
        modules=[
            _mod("pkg.a", docstring="A"),
            _mod("pkg.b", docstring="B"),
        ],
    )
    ps = derive_promises(scan)
    assert isinstance(ps, list)
    assert all(isinstance(p, Promise) for p in ps)
    # 2 modules * 3 attributes = 6 promises
    assert len(ps) == 6


def test_derive_promises_ordering_is_deterministic():
    scan = ScanResult(
        source_root=Path("/tmp/repo"),
        modules=[
            _mod("pkg.b", docstring="B"),
            _mod("pkg.a", docstring="A"),
        ],
    )
    ps = derive_promises(scan)
    # By module (in scan order — scan already sorts), then by attribute
    owners = [p.owner_entity for p in ps]
    # Scan doesn't re-sort here; caller responsibility. But within a module,
    # attribute order should be stable: intent, delivers, provides.
    per_module_attrs = {}
    for p in ps:
        per_module_attrs.setdefault(p.owner_entity, []).append(p.attribute)
    for attrs in per_module_attrs.values():
        assert attrs == ["intent", "delivers", "provides"]


def test_derive_promises_on_empty_scan_returns_empty_list():
    scan = ScanResult(source_root=Path("/tmp/repo"), modules=[])
    assert derive_promises(scan) == []
