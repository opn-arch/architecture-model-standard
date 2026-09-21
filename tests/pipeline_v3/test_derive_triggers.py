"""Tests for pipeline_v3.derive_triggers — Part 17a2.

derive_triggers consumes a ScanResult + list[BehaviorCandidate] and
produces list[TriggerEdge] connecting behaviors whose functions call
each other. Resolution rules:

    - Local: callee name == BehaviorCandidate in same module.
    - Imported: ``from M import x`` → M/x behavior.
    - Imported: ``import M`` → any behavior in M matching callee_name.
    - Ambiguous callees (multiple matches) silently skipped.
    - Self-triggers (A → A) dropped.

Determinism: output sorted by (from_behavior, to_behavior); dedup at
edge level.
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.pipeline_v3.derive_behaviors import (
    BehaviorCandidate,
    _behavior_id,
)
from architecture_model.pipeline_v3.derive_triggers import (
    COMPOSITE_MIN_TRIGGERS,
    TriggerEdge,
    derive_triggers,
)
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult


def _mod(
    name: str,
    functions: list[dict] | None = None,
    classes: list[dict] | None = None,
    imports: list[str] | None = None,
) -> ScannedModule:
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring=None,
        functions=functions or [],
        classes=classes or [],
        imports=imports or [],
        line_count=0,
    )


def _fn(name: str, calls: list[str] | None = None) -> dict:
    return {"name": name, "signature": f"def {name}()", "calls": calls or []}


def _cand(module: str, fname: str) -> BehaviorCandidate:
    return BehaviorCandidate(
        id=_behavior_id(module, fname),
        name=fname,
        description=f"Do {fname}.",
        owner_module=module,
        function_name=fname,
    )


def _scan(modules: list[ScannedModule]) -> ScanResult:
    return ScanResult(source_root=Path("/tmp"), modules=modules)


# ---------------------------------------------------------------------------
# Local resolution (same module)
# ---------------------------------------------------------------------------


def test_local_call_produces_trigger_edge():
    mod = _mod("pkg.a", functions=[_fn("caller", ["callee"]), _fn("callee")])
    behs = [_cand("pkg.a", "caller"), _cand("pkg.a", "callee")]
    edges = derive_triggers(_scan([mod]), behs)
    assert edges == [
        TriggerEdge(
            from_behavior=_behavior_id("pkg.a", "caller"),
            to_behavior=_behavior_id("pkg.a", "callee"),
        )
    ]


def test_self_trigger_is_dropped():
    # A function that calls itself (recursion) should not emit A → A.
    mod = _mod("pkg.a", functions=[_fn("recur", ["recur"])])
    behs = [_cand("pkg.a", "recur")]
    assert derive_triggers(_scan([mod]), behs) == []


def test_unresolved_callee_is_silently_skipped():
    # ``stdlib_thing`` is neither a local function nor a behavior — no
    # edge emitted, no error.
    mod = _mod("pkg.a", functions=[_fn("caller", ["stdlib_thing"])])
    behs = [_cand("pkg.a", "caller")]
    assert derive_triggers(_scan([mod]), behs) == []


# ---------------------------------------------------------------------------
# Imported resolution — from M import x
# ---------------------------------------------------------------------------


def test_from_import_resolves_to_target_module_behavior():
    caller_mod = _mod(
        "pkg.a",
        functions=[_fn("caller", ["helper"])],
        imports=["from pkg.b import helper"],
    )
    target_mod = _mod("pkg.b", functions=[_fn("helper")])
    behs = [_cand("pkg.a", "caller"), _cand("pkg.b", "helper")]
    edges = derive_triggers(_scan([caller_mod, target_mod]), behs)
    assert edges == [
        TriggerEdge(
            from_behavior=_behavior_id("pkg.a", "caller"),
            to_behavior=_behavior_id("pkg.b", "helper"),
        )
    ]


def test_from_import_multi_symbol_resolves():
    caller_mod = _mod(
        "pkg.a",
        functions=[_fn("caller", ["h1"])],
        imports=["from pkg.b import h1, h2"],
    )
    target_mod = _mod("pkg.b", functions=[_fn("h1"), _fn("h2")])
    behs = [
        _cand("pkg.a", "caller"),
        _cand("pkg.b", "h1"),
        _cand("pkg.b", "h2"),
    ]
    edges = derive_triggers(_scan([caller_mod, target_mod]), behs)
    assert TriggerEdge(
        from_behavior=_behavior_id("pkg.a", "caller"),
        to_behavior=_behavior_id("pkg.b", "h1"),
    ) in edges


# ---------------------------------------------------------------------------
# Imported resolution — import M
# ---------------------------------------------------------------------------


def test_import_module_resolves_matching_callee():
    caller_mod = _mod(
        "pkg.a",
        functions=[_fn("caller", ["helper"])],
        imports=["import pkg.b"],
    )
    target_mod = _mod("pkg.b", functions=[_fn("helper")])
    behs = [_cand("pkg.a", "caller"), _cand("pkg.b", "helper")]
    edges = derive_triggers(_scan([caller_mod, target_mod]), behs)
    assert edges == [
        TriggerEdge(
            from_behavior=_behavior_id("pkg.a", "caller"),
            to_behavior=_behavior_id("pkg.b", "helper"),
        )
    ]


def test_ambiguous_imported_callee_is_skipped():
    # ``helper`` exists in both pkg.b and pkg.c, and the caller
    # imports both modules → ambiguous, edge is NOT emitted.
    caller_mod = _mod(
        "pkg.a",
        functions=[_fn("caller", ["helper"])],
        imports=["import pkg.b", "import pkg.c"],
    )
    b_mod = _mod("pkg.b", functions=[_fn("helper")])
    c_mod = _mod("pkg.c", functions=[_fn("helper")])
    behs = [
        _cand("pkg.a", "caller"),
        _cand("pkg.b", "helper"),
        _cand("pkg.c", "helper"),
    ]
    assert derive_triggers(_scan([caller_mod, b_mod, c_mod]), behs) == []


# ---------------------------------------------------------------------------
# Class methods
# ---------------------------------------------------------------------------


def test_class_method_calls_emit_triggers():
    mod = _mod(
        "pkg.a",
        classes=[
            {
                "name": "Runner",
                "method_details": [
                    {
                        "name": "run",
                        "signature": "def run(self)",
                        "docstring": "Run.",
                        "calls": ["helper"],
                    },
                ],
            }
        ],
        functions=[_fn("helper")],
    )
    behs = [
        BehaviorCandidate(
            id=_behavior_id("pkg.a", "run"),
            name="run",
            description="Run.",
            owner_module="pkg.a",
            function_name="run",
            class_name="Runner",
        ),
        _cand("pkg.a", "helper"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    assert edges == [
        TriggerEdge(
            from_behavior=_behavior_id("pkg.a", "run"),
            to_behavior=_behavior_id("pkg.a", "helper"),
        )
    ]


# ---------------------------------------------------------------------------
# Determinism & edge cases
# ---------------------------------------------------------------------------


def test_output_is_sorted_by_from_then_to():
    mod = _mod(
        "pkg.a",
        functions=[
            _fn("z_caller", ["a_callee"]),
            _fn("a_caller", ["z_callee"]),
            _fn("a_callee"),
            _fn("z_callee"),
        ],
    )
    behs = [
        _cand("pkg.a", "z_caller"),
        _cand("pkg.a", "a_caller"),
        _cand("pkg.a", "a_callee"),
        _cand("pkg.a", "z_callee"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    ids = [(e.from_behavior, e.to_behavior) for e in edges]
    assert ids == sorted(ids)


def test_empty_behaviors_returns_empty():
    mod = _mod("pkg.a", functions=[_fn("f", ["g"])])
    assert derive_triggers(_scan([mod]), []) == []


def test_duplicate_calls_collapse_to_single_edge():
    # A function calling ``callee`` twice should produce only one edge.
    mod = _mod(
        "pkg.a",
        functions=[_fn("caller", ["callee", "callee"]), _fn("callee")],
    )
    behs = [_cand("pkg.a", "caller"), _cand("pkg.a", "callee")]
    edges = derive_triggers(_scan([mod]), behs)
    assert len(edges) == 1


def test_trigger_edge_is_frozen_hashable():
    e = TriggerEdge(from_behavior="BEH-a", to_behavior="BEH-b")
    {e}  # hashable
    import pytest
    with pytest.raises((AttributeError, Exception)):
        e.from_behavior = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Part 17a3: composite behavior detection + sequence emission
# ---------------------------------------------------------------------------


def test_below_threshold_source_emits_no_sequence():
    # 2 resolved outgoing triggers (< COMPOSITE_MIN_TRIGGERS = 3):
    # sequence must be None on every edge.
    mod = _mod(
        "pkg.a",
        functions=[
            _fn("caller", ["a", "b"]),
            _fn("a"),
            _fn("b"),
        ],
    )
    behs = [
        _cand("pkg.a", "caller"),
        _cand("pkg.a", "a"),
        _cand("pkg.a", "b"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    assert all(e.sequence is None for e in edges)


def test_at_threshold_source_emits_sequences_in_call_order():
    # 3 resolved outgoing triggers → composite. Sequences 1..3 in
    # call-site order (the ``calls`` list from the AST scan).
    mod = _mod(
        "pkg.a",
        functions=[
            _fn("orchestrator", ["step1", "step2", "step3"]),
            _fn("step1"),
            _fn("step2"),
            _fn("step3"),
        ],
    )
    behs = [
        _cand("pkg.a", "orchestrator"),
        _cand("pkg.a", "step1"),
        _cand("pkg.a", "step2"),
        _cand("pkg.a", "step3"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    # Locate the three composite edges (from == orchestrator) and
    # index them by target id.
    orch_id = _behavior_id("pkg.a", "orchestrator")
    composite = {e.to_behavior: e.sequence for e in edges if e.from_behavior == orch_id}
    assert composite[_behavior_id("pkg.a", "step1")] == 1
    assert composite[_behavior_id("pkg.a", "step2")] == 2
    assert composite[_behavior_id("pkg.a", "step3")] == 3


def test_sequence_reflects_calls_list_order_not_id_order():
    # Reverse the calls list; sequences should follow the calls list,
    # NOT the sorted target-id order.
    mod = _mod(
        "pkg.a",
        functions=[
            _fn("orchestrator", ["zeta", "mu", "alpha"]),
            _fn("zeta"),
            _fn("mu"),
            _fn("alpha"),
        ],
    )
    behs = [
        _cand("pkg.a", "orchestrator"),
        _cand("pkg.a", "zeta"),
        _cand("pkg.a", "mu"),
        _cand("pkg.a", "alpha"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    orch_id = _behavior_id("pkg.a", "orchestrator")
    composite = {e.to_behavior: e.sequence for e in edges if e.from_behavior == orch_id}
    assert composite[_behavior_id("pkg.a", "zeta")] == 1
    assert composite[_behavior_id("pkg.a", "mu")] == 2
    assert composite[_behavior_id("pkg.a", "alpha")] == 3


def test_unresolved_calls_do_not_consume_sequence_slots():
    # calls = [x, unresolved, y, z] where ``unresolved`` doesn't match
    # any behavior. Sequences must be 1, 2, 3 across x, y, z — the
    # unresolved call is silently skipped (not a phantom "slot 2").
    mod = _mod(
        "pkg.a",
        functions=[
            _fn("orchestrator", ["x", "unresolved", "y", "z"]),
            _fn("x"),
            _fn("y"),
            _fn("z"),
        ],
    )
    behs = [
        _cand("pkg.a", "orchestrator"),
        _cand("pkg.a", "x"),
        _cand("pkg.a", "y"),
        _cand("pkg.a", "z"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    orch_id = _behavior_id("pkg.a", "orchestrator")
    seqs = sorted(
        (e.to_behavior, e.sequence)
        for e in edges if e.from_behavior == orch_id
    )
    assert [s for (_t, s) in seqs] != [None, None, None]  # composite
    # All three targets have sequences in {1, 2, 3}, no gaps
    seq_values = sorted(s for (_t, s) in seqs)
    assert seq_values == [1, 2, 3]


def test_composite_threshold_constant_is_three():
    # Guard against silent threshold drift — documented value is 3.
    assert COMPOSITE_MIN_TRIGGERS == 3


def test_mixed_composite_and_noncomposite_sources_coexist():
    # Two source behaviors: one composite (3 targets), one not (1
    # target). Only the composite's edges get sequences.
    mod = _mod(
        "pkg.a",
        functions=[
            _fn("orch", ["a", "b", "c"]),
            _fn("small", ["a"]),
            _fn("a"),
            _fn("b"),
            _fn("c"),
        ],
    )
    behs = [
        _cand("pkg.a", "orch"),
        _cand("pkg.a", "small"),
        _cand("pkg.a", "a"),
        _cand("pkg.a", "b"),
        _cand("pkg.a", "c"),
    ]
    edges = derive_triggers(_scan([mod]), behs)
    orch_id = _behavior_id("pkg.a", "orch")
    small_id = _behavior_id("pkg.a", "small")
    orch_seqs = [e.sequence for e in edges if e.from_behavior == orch_id]
    small_seqs = [e.sequence for e in edges if e.from_behavior == small_id]
    assert sorted(s for s in orch_seqs) == [1, 2, 3]
    assert small_seqs == [None]


def test_trigger_edge_sequence_defaults_to_none():
    e = TriggerEdge(from_behavior="BEH-a", to_behavior="BEH-b")
    assert e.sequence is None
