"""Tests for per-subsystem update summary generation."""
from architecture_model.quality.update_summary import (
    subsystem_summary, format_summaries,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Interface, Constraint, Status, InterfaceType, ConstraintType,
)


def _make_model(*, intent=False, moes=False, trade_offs=False, failure_modes=False, contract=False):
    comps = [
        Component(
            id="COMP-1", name="Alpha", status=Status.ACTIVE,
            intent="Parse YAML" if intent else "",
            trade_offs=["Speed vs safety"] if trade_offs else [],
            failure_modes=["Corrupt YAML"] if failure_modes else [],
        ),
    ]
    caps = [
        Capability(
            id="CAP-1", name="Parsing", status=Status.ACTIVE,
            intent="Parse models" if intent else "",
            moes=["<1s parse time"] if moes else [],
        ),
    ]
    ifaces = [
        Interface(
            id="IF-1", name="Parse API", type=InterfaceType.INTERNAL,
            status=Status.ACTIVE,
            contract={"input": "str", "output": "Model"} if contract else None,
        ),
    ]
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.1", project="test-sub", generated_at="2026-01-01"),
        entities=Entities(components=comps, capabilities=caps, interfaces=ifaces),
        relationships=[],
    )


class TestSubsystemSummary:
    def test_empty_model_shows_zeros(self):
        model = _make_model()
        summary = subsystem_summary("TestSub", model)
        assert summary["name"] == "TestSub"
        assert summary["intent"] == "0/2"
        assert summary["moes"] == "0/1"

    def test_populated_model_shows_counts(self):
        model = _make_model(intent=True, moes=True, trade_offs=True, failure_modes=True, contract=True)
        summary = subsystem_summary("TestSub", model)
        assert summary["intent"] == "2/2"
        assert summary["moes"] == "1/1"
        assert summary["trade_offs"] == "1/1"
        assert summary["failure_modes"] == "1/1"
        assert summary["contracts"] == "1/1"


class TestFormatSummaries:
    def test_renders_markdown_table(self):
        model = _make_model(intent=True, moes=True)
        summaries = [subsystem_summary("Core", model)]
        md = format_summaries(summaries)
        assert "| Core" in md
        assert "Subsystem" in md
        assert "Intent" in md
