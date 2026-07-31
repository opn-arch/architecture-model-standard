"""Test enrichment from SourceGraph data."""
from architecture_model.core.types import (
    ArchitectureModel, Component, ModelMeta, Entities, FunctionSignature, Symbol
)
from architecture_model.manifest.protocol import SourceGraph, SourceUnit, DependencyEdge, ExportedSymbol
from architecture_model.orchestration.auto_enrich import enrich_from_source_graph
from architecture_model.core.confidence import compute_component_confidence


def _make_graph():
    return SourceGraph(
        units=[
            SourceUnit(
                file="src/handler.go",
                has_content=True,
                language="go",
                exports=[
                    ExportedSymbol(name="HandleRequest", kind="function",
                                  signature="(w http.ResponseWriter, r *http.Request)",
                                  doc="Processes incoming HTTP requests."),
                    ExportedSymbol(name="Router", kind="class",
                                  signature="struct",
                                  doc="Manages HTTP route registration."),
                ],
            ),
            SourceUnit(
                file="src/db.go",
                has_content=True,
                language="go",
                exports=[
                    ExportedSymbol(name="Connect", kind="function",
                                  signature="(dsn string) (*DB, error)",
                                  doc="Establishes a database connection."),
                    ExportedSymbol(name="DB", kind="class",
                                  signature="struct", doc="Database pool."),
                ],
            ),
        ],
        edges=[DependencyEdge(source="src/handler.go", target="src/db.go", symbols=["Connect", "DB"])],
    )


def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="COMP-1", name="Handler", status="ACTIVE", files=["src/handler.go"]),
            Component(id="COMP-2", name="Database", status="ACTIVE", files=["src/db.go"]),
        ]),
        relationships=[],
    )


def test_signatures_populated():
    model = _make_model()
    enrich_from_source_graph(model, _make_graph())
    handler = model.entities.components[0]
    assert len(handler.signatures) >= 1
    assert any(s.name == "HandleRequest" for s in handler.signatures)


def test_symbols_populated():
    model = _make_model()
    enrich_from_source_graph(model, _make_graph())
    handler = model.entities.components[0]
    assert any(s.name == "Router" for s in handler.symbols)


def test_contract_from_docs():
    model = _make_model()
    enrich_from_source_graph(model, _make_graph())
    handler = model.entities.components[0]
    assert handler.contract
    assert "HTTP" in handler.contract or "HandleRequest" in handler.contract


def test_confidence_improves():
    model = _make_model()
    baseline = compute_component_confidence(model.entities.components[0])
    enrich_from_source_graph(model, _make_graph())
    enriched = compute_component_confidence(model.entities.components[0])
    assert enriched > baseline


def test_responsibilities_populated():
    model = _make_model()
    enrich_from_source_graph(model, _make_graph())
    db = model.entities.components[1]
    assert "Connect" in (db.responsibilities or [])
