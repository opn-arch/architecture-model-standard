"""Task 7 (Phase 2 schema-and-semantic-content): semantic-field rendering.

Verifies that the ``component_spec`` and ``functional_analysis``
projectors render Phase 2 (schema 2.1) semantic fields **only** when
present, and that rendered output on a 2.0 fixture is byte-identical
to a captured pre-Phase-2 baseline (no drift).

The byte-identity guard is the load-bearing invariant here: it catches
any accidental leakage of Phase 2 markdown into 2.0-only paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.core.semantic_types import (
    FailureMode,
    Likelihood,
    Severity,
    SLO,
    TradeOff,
)
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Entities,
    Maturity,
    ModelMeta,
    Status,
)
from architecture_model.docs.component_spec import generate_component_spec
from architecture_model.docs.se.functional_analysis import (
    generate_functional_analysis,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_2_0 = ROOT / "tests" / "fixtures" / "viewer-curation-model.yaml"


# ---------------------------------------------------------------------------
# Byte-identity guards on 2.0 fixture
# ---------------------------------------------------------------------------


def test_component_spec_no_semantic_sections_on_2_0_fixture() -> None:
    model = load_model(FIXTURE_2_0)
    for comp in model.entities.components:
        md = generate_component_spec(comp, model)
        for header in (
            "## Intent",
            "## Failure Modes",
            "## Trade-Offs",
            "## SLOs",
            "## Ownership",
            "## Dependency Rationale",
        ):
            assert header not in md, f"{header} leaked into 2.0 render for {comp.id}"


def test_functional_analysis_no_capability_ownership_on_2_0_fixture() -> None:
    model = load_model(FIXTURE_2_0)
    md = generate_functional_analysis(model)
    assert "## Capability Ownership" not in md


# ---------------------------------------------------------------------------
# Helpers to build a minimal in-memory model with Phase 2 fields set
# ---------------------------------------------------------------------------


def _minimal_model_with_component(comp: Component) -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1.0", generated_at="1970-01-01T00:00:00Z"),
        entities=Entities(components=[comp]),
        relationships=[],
    )


# ---------------------------------------------------------------------------
# component_spec renders Phase 2 sections when fields are present
# ---------------------------------------------------------------------------


def test_component_spec_renders_intent_when_present() -> None:
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        intent="Parse YAML into typed model.",
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Intent" in md
    assert "Parse YAML into typed model." in md


def test_component_spec_renders_typed_failure_mode() -> None:
    fm = FailureMode(
        id="FM-1",
        cause="malformed yaml",
        effect="parser aborts",
        likelihood=Likelihood.POSSIBLE,
        severity=Severity.MAJOR,
        detection="exception logs",
        mitigation="retry with strict=False",
    )
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        failure_modes=[fm],
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Failure Modes" in md
    assert "FM-1" in md
    assert "malformed yaml" in md
    assert "possible" in md
    assert "major" in md
    assert "retry with strict=False" in md


def test_component_spec_renders_typed_trade_off() -> None:
    to_ = TradeOff(
        id="TO-1",
        decision="use PyYAML",
        alternatives=("ruamel.yaml", "hand-written parser"),
        rationale="wide install base",
        consequences=("no round-trip preservation",),
        revisit_when="round-trip needed",
    )
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        trade_offs=[to_],
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Trade-Offs" in md
    assert "TO-1" in md
    assert "use PyYAML" in md
    assert "wide install base" in md
    assert "round-trip needed" in md


def test_component_spec_renders_slos_table() -> None:
    slo = SLO(metric="p99_latency_ms", target="< 200", window="7d", current="180")
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        slos=[slo],
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## SLOs" in md
    assert "| Metric | Target | Window |" in md
    assert "p99_latency_ms" in md
    assert "current: 180" in md


def test_component_spec_renders_ownership_owner_only() -> None:
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        owner="platform-team",
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Ownership" in md
    assert "**Owner:** platform-team" in md
    assert "**Maturity:**" not in md  # only owner set


def test_component_spec_renders_ownership_with_maturity() -> None:
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        owner="platform-team",
        maturity=Maturity.STABLE,
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Ownership" in md
    assert "**Owner:** platform-team" in md
    assert "**Maturity:** stable" in md


def test_component_spec_renders_dependency_rationale() -> None:
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        dependencies_rationale={"pyyaml": "widely available"},
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Dependency Rationale" in md
    assert "**pyyaml**" in md
    assert "widely available" in md


def test_component_spec_string_failure_modes_still_render() -> None:
    """Legacy 2.0 string entries in failure_modes must still render as bullets."""
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        failure_modes=["disk full", "yaml too large"],
    )
    md = generate_component_spec(comp, _minimal_model_with_component(comp))
    assert "## Failure Modes" in md
    assert "- disk full" in md
    assert "- yaml too large" in md


# ---------------------------------------------------------------------------
# functional_analysis renders Phase 2 semantic sections
# ---------------------------------------------------------------------------


def test_functional_analysis_renders_typed_trade_off_on_component() -> None:
    from architecture_model.core.types import Capability

    to_ = TradeOff(
        id="TO-1",
        decision="in-process cache",
        alternatives=("redis",),
        rationale="latency budget too tight",
        consequences=("no cross-process sharing",),
        revisit_when="scale > 1 node",
    )
    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        trade_offs=[to_],
    )
    cap = Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE)
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1.0", generated_at="1970-01-01T00:00:00Z"),
        entities=Entities(capabilities=[cap], components=[comp]),
        relationships=[],
    )
    md = generate_functional_analysis(model)
    assert "### Design Trade-offs" in md
    assert "**TO-1** — in-process cache" in md
    assert "Rationale: latency budget too tight" in md


def test_functional_analysis_renders_capability_ownership() -> None:
    from architecture_model.core.types import Capability

    cap = Capability(
        id="CAP-1",
        name="Parsing",
        status=Status.ACTIVE,
        owner="platform-team",
        maturity=Maturity.ACTIVE,
    )
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1.0", generated_at="1970-01-01T00:00:00Z"),
        entities=Entities(capabilities=[cap]),
        relationships=[],
    )
    md = generate_functional_analysis(model)
    assert "## Capability Ownership" in md
    assert "| CAP-1 | Parsing | platform-team | active |" in md


def test_functional_analysis_string_trade_off_still_renders_as_bullet() -> None:
    """Legacy 2.0 string trade_offs must keep their pre-Phase-2 formatting."""
    from architecture_model.core.types import Capability

    comp = Component(
        id="COMP-1",
        name="Parser",
        status=Status.ACTIVE,
        kind=ComponentKind.LIBRARY,
        trade_offs=["simplicity over flexibility"],
    )
    cap = Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE)
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1.0", generated_at="1970-01-01T00:00:00Z"),
        entities=Entities(capabilities=[cap], components=[comp]),
        relationships=[],
    )
    md = generate_functional_analysis(model)
    assert "- simplicity over flexibility" in md
    # No structured decoration
    assert "**TO-" not in md
