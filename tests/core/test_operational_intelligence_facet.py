"""Tests for the Operational Intelligence component facet (C15).

Four blocks per component: Logging (SI&L), LLM (meta.provider), Learning
(pipeline-history), Measurement (test coverage). Blocks without evidence
render with a grey CSS class so the facet layout stays stable and audit
gaps are surfaced rather than hidden.
"""

from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component,
)
from architecture_model.core.visualize import (
    _operational_intelligence_facet_lines,
)


def _model_with_evidence(evidence: dict | None, provider: dict | None = None) -> ArchitectureModel:
    meta_kwargs = {"project": "Test", "schema_version": "2.1"}
    if provider is not None:
        meta_kwargs["provider"] = provider
    return ArchitectureModel(
        meta=ModelMeta(**meta_kwargs),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Core", status="ACTIVE", evidence=evidence),
            ],
        ),
        relationships=[],
    )


def test_operational_intelligence_renders_all_four_blocks_when_present():
    """When SI&L, provider, and test_coverage are all present, every block
    carries live data and receives the ``oi_live`` CSS class."""
    ev = {
        "sil": {"invocations": 1284, "failure_rate": 0.0078, "avg_duration_ms": 42.16},
        "test_coverage": {"test_count": 25},
    }
    model = _model_with_evidence(ev, provider={"name": "anthropic", "model": "claude-opus"})
    out = _operational_intelligence_facet_lines(model, "COMP-1", "Core", ev)
    assert out is not None
    # Live blocks
    assert "Logging: 1284 invocations" in out
    assert "0.78% fail" in out
    assert "LLM: anthropic" in out
    assert "25 tests" in out
    # CSS classes emitted
    assert "classDef oi_live" in out
    assert "classDef oi_grey" in out
    # Learning is not stamped per-component yet — must be grey
    assert "Learning: absent" in out


def test_operational_intelligence_grey_fallback_for_absent_evidence():
    """A component with no evidence emits four grey blocks — never omits any."""
    model = _model_with_evidence(evidence=None)
    out = _operational_intelligence_facet_lines(model, "COMP-1", "Core", {})
    assert out is not None
    for label in ("Logging: absent", "LLM: absent",
                  "Learning: absent", "Measurement: absent"):
        assert label in out
    # All four should carry the grey style class
    grey_lines = [ln for ln in out.split("\n") if "class OI_" in ln and "oi_grey" in ln]
    assert len(grey_lines) == 4


def test_operational_intelligence_partial_evidence_mixes_live_and_grey():
    """Only ``test_coverage`` present → Measurement live, others grey."""
    ev = {"test_coverage": {"test_count": 19}}
    model = _model_with_evidence(ev)
    out = _operational_intelligence_facet_lines(model, "COMP-1", "Core", ev)
    assert out is not None
    assert "19 tests" in out
    # SI&L, LLM, Learning grey
    assert "Logging: absent" in out
    assert "LLM: absent" in out
    assert "Learning: absent" in out
    # Exactly one live and three grey
    live = [ln for ln in out.split("\n") if "class OI_" in ln and "oi_live" in ln]
    grey = [ln for ln in out.split("\n") if "class OI_" in ln and "oi_grey" in ln]
    assert len(live) == 1
    assert len(grey) == 3
