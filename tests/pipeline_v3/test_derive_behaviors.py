"""Tests for pipeline_v3.derive_behaviors — Part 17a1.

derive_behaviors consumes a ScanResult and produces list[BehaviorCandidate].
One BehaviorCandidate per public documented function (module-level) or
class method. Private (``_``-prefix) and undocumented functions are
excluded. Ids are deterministic (BEH-<sha1(module:function)[:8]>).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from architecture_model.pipeline_v3.derive_behaviors import (
    BehaviorCandidate,
    derive_behaviors,
    derive_behaviors_for_module,
)
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult


def _mod(
    name: str,
    functions: list[dict] | None = None,
    classes: list[dict] | None = None,
) -> ScannedModule:
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring=None,
        functions=functions or [],
        classes=classes or [],
        imports=[],
        line_count=0,
    )


def _fn(name: str, doc: str | None = "One-line doc.") -> dict:
    d: dict = {"name": name, "signature": f"def {name}()"}
    if doc:
        d["docstring"] = doc
    return d


# ---------------------------------------------------------------------------
# Filtering: public + documented
# ---------------------------------------------------------------------------


def test_public_documented_function_produces_candidate():
    m = _mod("pkg.core", functions=[_fn("scan_repo", "Scan a repository.")])
    cands = derive_behaviors_for_module(m)
    assert len(cands) == 1
    assert cands[0].name == "scan_repo"
    assert cands[0].description == "Scan a repository."


def test_private_function_is_excluded():
    m = _mod("pkg.core", functions=[_fn("_helper", "Private helper.")])
    assert derive_behaviors_for_module(m) == []


def test_undocumented_function_is_excluded():
    m = _mod("pkg.core", functions=[_fn("public", doc=None)])
    assert derive_behaviors_for_module(m) == []


def test_blank_docstring_is_excluded():
    m = _mod("pkg.core", functions=[_fn("public", doc="   \n\n   ")])
    assert derive_behaviors_for_module(m) == []


# ---------------------------------------------------------------------------
# Id / description / determinism
# ---------------------------------------------------------------------------


def test_id_is_deterministic_sha1_of_module_and_function():
    m = _mod("pkg.core", functions=[_fn("scan_repo", "Scan.")])
    cand = derive_behaviors_for_module(m)[0]
    expected = "BEH-" + hashlib.sha1(b"pkg.core:scan_repo").hexdigest()[:8]
    assert cand.id == expected


def test_description_uses_first_nonempty_docstring_line():
    m = _mod(
        "pkg.core",
        functions=[_fn("f", "\n\nFirst real line.\nSecond line.\n")],
    )
    cand = derive_behaviors_for_module(m)[0]
    assert cand.description == "First real line."


def test_module_level_functions_sorted_by_name():
    m = _mod(
        "pkg.core",
        functions=[
            _fn("zeta", "Z."),
            _fn("alpha", "A."),
            _fn("mu", "M."),
        ],
    )
    cands = derive_behaviors_for_module(m)
    assert [c.name for c in cands] == ["alpha", "mu", "zeta"]


# ---------------------------------------------------------------------------
# Class methods
# ---------------------------------------------------------------------------


def test_class_method_with_docstring_produces_candidate():
    m = _mod(
        "pkg.core",
        classes=[
            {
                "name": "Runner",
                "method_details": [
                    {"name": "run", "signature": "def run(self)", "docstring": "Run."},
                ],
            }
        ],
    )
    cands = derive_behaviors_for_module(m)
    assert len(cands) == 1
    assert cands[0].class_name == "Runner"
    assert cands[0].name == "run"


def test_private_class_is_excluded():
    m = _mod(
        "pkg.core",
        classes=[
            {
                "name": "_Internal",
                "method_details": [
                    {"name": "run", "signature": "def run(self)", "docstring": "R."},
                ],
            }
        ],
    )
    assert derive_behaviors_for_module(m) == []


def test_class_without_method_details_is_ignored():
    m = _mod(
        "pkg.core",
        classes=[{"name": "Runner", "methods": ["run"]}],  # no method_details
    )
    assert derive_behaviors_for_module(m) == []


# ---------------------------------------------------------------------------
# Full ScanResult
# ---------------------------------------------------------------------------


def test_derive_behaviors_walks_all_modules():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[
            _mod("pkg.a", functions=[_fn("f1", "F1.")]),
            _mod("pkg.b", functions=[_fn("f2", "F2.")]),
        ],
    )
    cands = derive_behaviors(scan)
    assert {c.name for c in cands} == {"f1", "f2"}


def test_derive_behaviors_dedups_colliding_ids():
    # Two modules with the same dotted name (pathological) + same function
    # name → identical id. Should collapse to first-seen.
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[
            _mod("pkg.a", functions=[_fn("f", "First.")]),
            _mod("pkg.a", functions=[_fn("f", "Second.")]),
        ],
    )
    cands = derive_behaviors(scan)
    assert len(cands) == 1
    assert cands[0].description == "First."


def test_derive_behaviors_empty_scan_returns_empty():
    assert derive_behaviors(ScanResult(source_root=Path("/tmp"), modules=[])) == []


def test_behavior_candidate_is_frozen_hashable():
    m = _mod("pkg.core", functions=[_fn("f", "F.")])
    cand = derive_behaviors_for_module(m)[0]
    # Should be usable in a set (frozen dataclass)
    {cand}
    # And immutable
    import pytest
    with pytest.raises((AttributeError, Exception)):
        cand.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# R9: intent Promise emission per BehaviorCandidate
# ---------------------------------------------------------------------------


def test_derive_promises_for_behavior_emits_one_intent_promise():
    """Every BehaviorCandidate yields a single intent Promise whose
    content = the candidate description. Owner = candidate id (behaviors
    are first-class entities at v3 YAML emission time)."""
    from architecture_model.core.promise import PromiseStatus
    from architecture_model.pipeline_v3.derive_behaviors import (
        derive_promises_for_behavior,
    )

    m = _mod("pkg.core", functions=[_fn("scan_repo", "Scan a repository.")])
    cand = derive_behaviors_for_module(m)[0]
    promises = derive_promises_for_behavior(cand)
    assert len(promises) == 1
    p = promises[0]
    assert p.attribute == "intent"
    assert p.content == "Scan a repository."
    assert p.owner_entity == cand.id
    assert p.status == PromiseStatus.OPEN
    assert p.provenance == "pipeline_v3.derive_behaviors"


def test_derive_promises_for_behavior_is_deterministic():
    """Same input → identical Promise id (id is deterministic from
    (attribute, content, owner))."""
    from architecture_model.pipeline_v3.derive_behaviors import (
        derive_promises_for_behavior,
    )

    m = _mod("pkg.core", functions=[_fn("scan_repo", "Scan a repository.")])
    cand = derive_behaviors_for_module(m)[0]
    p1 = derive_promises_for_behavior(cand)[0]
    p2 = derive_promises_for_behavior(cand)[0]
    assert p1.id == p2.id
