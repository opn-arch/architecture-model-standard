import pytest
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, FunctionSignature,
    ModelMeta, Symbol, SymbolKind, TestContract, ComponentInterface,
)
from architecture_model.docs.component_spec import generate_component_spec
from architecture_model.docs.generator import generate_docs


@pytest.fixture
def sample_model():
    return ArchitectureModel(
        meta=ModelMeta(project="test-project", schema_version="1.3"),
        entities=Entities(components=[
            Component(
                id="COMP-1", name="JsonProvider", status="ACTIVE",
                f_block="F1", pattern="provider",
                files=["src/flask/json/__init__.py", "src/flask/json/provider.py"],
                contract="Provides JSON serialization for Flask applications.",
                responsibilities=["serialize", "deserialize", "configure"],
                signatures=[
                    FunctionSignature(name="dumps", params=["obj", "**kwargs"], returns="str",
                                    body_hint="Serialize obj to JSON string."),
                    FunctionSignature(name="loads", params=["s", "**kwargs"], returns="Any",
                                    body_hint="Deserialize JSON string."),
                ],
                symbols=[
                    Symbol(name="JSONProvider", kind=SymbolKind.CLASS,
                          supers=["object"], members=["dumps", "loads", "response"]),
                ],
                interfaces=[
                    ComponentInterface(name="json_api", kind="provides",
                                     target_component="COMP-2", symbols=["dumps", "loads"]),
                ],
                test_contracts=[
                    TestContract(test_file="test_json.py", test_method="test_dumps",
                               assertion="result == '{}'", contract_type="value_equality"),
                ],
                confidence=0.85,
            ),
            Component(
                id="COMP-2", name="Router", status="ACTIVE",
                f_block="F1", pattern="router",
                files=["src/flask/routing.py"],
                contract="URL routing and dispatch.",
                interfaces=[
                    ComponentInterface(name="json_dep", kind="requires",
                                     target_component="COMP-1", symbols=["dumps"]),
                ],
                confidence=0.72,
            ),
        ]),
        relationships=[],
    )


class TestComponentSpec:
    def test_generates_markdown(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "# COMP-1: JsonProvider" in md
        assert "ACTIVE" in md
        assert "provider" in md

    def test_includes_signatures(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "dumps" in md
        assert "loads" in md

    def test_includes_dependencies(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "COMP-2" in md or "Router" in md

    def test_deterministic(self, sample_model):
        comp = sample_model.entities.components[0]
        assert generate_component_spec(comp, sample_model) == generate_component_spec(comp, sample_model)


class TestDocGenerator:
    def test_generates_component_docs(self, sample_model, tmp_path):
        result = generate_docs(sample_model, output_dir=tmp_path)
        assert (tmp_path / "components" / "COMP-1.md").exists()
        assert (tmp_path / "components" / "COMP-2.md").exists()

    def test_returns_paths(self, sample_model, tmp_path):
        result = generate_docs(sample_model, output_dir=tmp_path)
        assert "components" in result
        assert len(result["components"]) == 2
