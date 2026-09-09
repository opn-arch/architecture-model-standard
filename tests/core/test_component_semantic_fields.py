"""Component gains 9 optional semantic fields on top of BaseEntity legacy fields.

Plan reference: ``docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md``
Task 2. See the "Deviation from spec" note under that task: BaseEntity's five
legacy list[str] fields (intent, goals, requirements, failure_modes, trade_offs)
are preserved untouched for back-compat; the parser widens the last three to
accept dict entries (2.1 style) which are promoted to typed objects
(FailureMode / TradeOff / RequirementRef) stored alongside legacy strings.
"""

from __future__ import annotations

from architecture_model.core.parser import _parse_component
from architecture_model.core.semantic_types import (
    FailureMode,
    RequirementRef,
    SLO,
    TradeOff,
    VerificationRef,
)
from architecture_model.core.types import ArchitectureModel, Entities, Maturity, ModelMeta


def _make(**overrides):
    d = {"id": "COMP-1", "name": "X", "kind": "module", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_component(d)


def test_component_defaults_preserve_baseentity_shape():
    c = _make()
    # Legacy BaseEntity fields (unchanged: list[str], "" defaults)
    assert c.intent == ""
    assert c.goals == []
    assert c.requirements == []
    assert c.failure_modes == []
    assert c.trade_offs == []
    # New Phase 2 fields on Component
    assert c.stakeholders == []
    assert c.success_criteria == []
    assert c.assumptions == []
    assert c.open_questions == []
    assert c.verification == []
    assert c.slos == []
    assert c.owner is None
    assert c.maturity is None
    assert c.dependencies_rationale == {}


def test_component_accepts_typed_failure_modes_via_parser_promotion():
    c = _make(
        failure_modes=[
            {
                "id": "FM-1",
                "cause": "Malformed YAML",
                "effect": "ParseError raised",
                "likelihood": "possible",
                "severity": "minor",
                "detection": "Schema validation",
                "mitigation": "Wrap with try/except",
            }
        ]
    )
    assert len(c.failure_modes) == 1
    assert isinstance(c.failure_modes[0], FailureMode)
    assert c.failure_modes[0].id == "FM-1"
    assert c.failure_modes[0].likelihood.value == "possible"


def test_component_accepts_typed_trade_offs_via_parser_promotion():
    c = _make(
        trade_offs=[
            {
                "id": "TO-1",
                "decision": "PyYAML over ruamel",
                "alternatives": ["ruamel.yaml"],
                "rationale": "Fewer deps",
                "consequences": ["No round-trip preservation"],
                "revisit_when": "Round-trip needed",
                "status": "active",
            }
        ]
    )
    assert isinstance(c.trade_offs[0], TradeOff)
    assert c.trade_offs[0].id == "TO-1"


def test_component_accepts_typed_requirements_via_parser_promotion():
    c = _make(requirements=[{"id": "REQ-1", "note": "must be idempotent"}])
    assert isinstance(c.requirements[0], RequirementRef)
    assert c.requirements[0].id == "REQ-1"
    assert c.requirements[0].note == "must be idempotent"


def test_component_backward_compat_string_entries_still_accepted():
    """2.0 fixtures use bare strings in these fields; must still parse."""
    c = _make(
        failure_modes=["timeout", "invalid input"],
        trade_offs=["chose speed over accuracy"],
        requirements=["REQ-legacy"],
    )
    assert c.failure_modes == ["timeout", "invalid input"]
    assert c.trade_offs == ["chose speed over accuracy"]
    assert c.requirements == ["REQ-legacy"]


def test_component_new_fields_parse_correctly():
    c = _make(
        stakeholders=["core-team"],
        success_criteria=["parses in <50ms"],
        assumptions=["YAML input is UTF-8"],
        open_questions=["Do we support anchors?"],
        slos=[{"metric": "parse latency", "target": "50ms", "window": "p99"}],
        verification=[{"id": "VER-1", "method": "pytest"}],
        owner="core-team",
        maturity="stable",
        dependencies_rationale={"COMP-2": "Uses type system for validation"},
    )
    assert c.stakeholders == ["core-team"]
    assert c.success_criteria == ["parses in <50ms"]
    assert c.assumptions == ["YAML input is UTF-8"]
    assert c.open_questions == ["Do we support anchors?"]
    assert isinstance(c.slos[0], SLO)
    assert c.slos[0].metric == "parse latency"
    assert isinstance(c.verification[0], VerificationRef)
    assert c.verification[0].method == "pytest"
    assert c.owner == "core-team"
    assert c.maturity == Maturity.STABLE
    assert c.dependencies_rationale == {"COMP-2": "Uses type system for validation"}


def test_component_verification_accepts_bare_string_ids():
    c = _make(verification=["VER-1", "VER-2"])
    assert all(isinstance(v, VerificationRef) for v in c.verification)
    assert [v.id for v in c.verification] == ["VER-1", "VER-2"]


def test_component_dump_round_trip_with_typed_entries():
    """Typed entries in failure_modes/trade_offs/verification/slos should
    serialize back to dicts via the model-level dump path so YAML round-trip
    is deterministic.
    """
    c = _make(
        failure_modes=[
            {
                "id": "FM-1",
                "cause": "x",
                "effect": "y",
                "likelihood": "rare",
                "severity": "minor",
                "detection": "d",
                "mitigation": "m",
            }
        ],
        slos=[{"metric": "lat", "target": "50ms", "window": "p99"}],
        owner="team",
        maturity="active",
    )
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.1"),
        entities=Entities(components=[c]),
    )
    d = model.to_dict()
    comp_dict = d["entities"]["components"][0]
    assert comp_dict["failure_modes"][0]["id"] == "FM-1"
    assert comp_dict["slos"][0]["metric"] == "lat"
    assert comp_dict["owner"] == "team"
    assert comp_dict["maturity"] == "active"


def test_component_omits_new_semantic_fields_when_empty():
    c = _make()
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.1"),
        entities=Entities(components=[c]),
    )
    d = model.to_dict()
    comp_dict = d["entities"]["components"][0]
    for key in (
        "stakeholders",
        "success_criteria",
        "assumptions",
        "open_questions",
        "verification",
        "slos",
        "owner",
        "maturity",
        "dependencies_rationale",
    ):
        assert key not in comp_dict, f"expected {key!r} omitted, got: {comp_dict}"
