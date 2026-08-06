"""Tests for Mermaid diagram generation."""
import pytest
from architecture_model.docs.diagrams import (
    generate_component_diagram,
    generate_use_case_diagram,
    generate_system_boundary_diagram,
    generate_all_diagrams,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Behavior,
    Relationship, RelationType, System,
)

@pytest.fixture
def model():
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Auth", status="ACTIVE"),
                Component(id="COMP-2", name="API", status="ACTIVE"),
            ],
            systems=[
                System(id="SYS-1", name="Backend", status="ACTIVE", component_ids=["COMP-1", "COMP-2"]),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="login", status="ACTIVE", steps=["validate", "create_token"]),
                Behavior(id="BEH-2", name="create_token", status="ACTIVE"),
                Behavior(id="UC-1", name="login (end-to-end)", status="ACTIVE",
                         steps=["login", "create_token"], trigger="POST /login", actor="User"),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-2", to_id="COMP-1"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="BEH-1"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-2", to_id="BEH-2"),
        ],
    )

class TestComponentDiagram:
    def test_produces_mermaid(self, model):
        md = generate_component_diagram(model)
        assert "```mermaid" in md
        assert "graph TD" in md
        assert "Auth" in md
        assert "API" in md

class TestUseCaseDiagram:
    def test_produces_sequence_diagram(self, model):
        md = generate_use_case_diagram(model)
        assert "sequenceDiagram" in md
        assert "UC-1" in md or "login" in md

    def test_no_use_cases_handled(self):
        m = ArchitectureModel(
            meta=ModelMeta(project="t", schema_version="1.3"),
            entities=Entities(components=[], behaviors=[]),
            relationships=[],
        )
        md = generate_use_case_diagram(m)
        assert "No use cases" in md

class TestSystemBoundaryDiagram:
    def test_produces_subgraphs(self, model):
        md = generate_system_boundary_diagram(model)
        assert "subgraph" in md
        assert "Backend" in md

class TestGenerateAll:
    def test_writes_files(self, tmp_path, model):
        paths = generate_all_diagrams(model, tmp_path)
        assert len(paths) >= 2
        assert all(p.exists() for p in paths)
