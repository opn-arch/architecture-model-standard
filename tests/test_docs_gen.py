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
                source_block="S1", pattern="provider",
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
                source_block="S1", pattern="router",
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
        assert "# Component: JsonProvider (COMP-1)" in md
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


class TestDependencyMatrix:
    def test_generates_table(self, sample_model):
        from architecture_model.docs.dependency_matrix import generate_dependency_matrix
        md = generate_dependency_matrix(sample_model)
        assert "COMP-1" in md or "JsonProvider" in md

    def test_shows_direction(self, sample_model):
        from architecture_model.docs.dependency_matrix import generate_dependency_matrix
        md = generate_dependency_matrix(sample_model)
        assert "\u2192" in md or "\u2190" in md


class TestICD:
    def test_generates_interfaces(self, sample_model):
        from architecture_model.docs.icd import generate_icd
        md = generate_icd(sample_model)
        assert "JsonProvider" in md
        assert "dumps" in md


class TestHealthReport:
    def test_includes_confidence(self, sample_model):
        from architecture_model.docs.health import generate_health_report
        md = generate_health_report(sample_model)
        assert "85%" in md

    def test_includes_components(self, sample_model):
        from architecture_model.docs.health import generate_health_report
        md = generate_health_report(sample_model)
        assert "JsonProvider" in md
        assert "Router" in md


class TestDriftReport:
    def test_detects_added(self, sample_model):
        from copy import deepcopy
        from architecture_model.docs.drift import generate_drift_report
        old = deepcopy(sample_model)
        old.entities.components = [old.entities.components[0]]
        md = generate_drift_report(old, sample_model)
        assert "Added" in md or "added" in md
        assert "Router" in md or "COMP-2" in md

    def test_no_changes(self, sample_model):
        from architecture_model.docs.drift import generate_drift_report
        md = generate_drift_report(sample_model, sample_model)
        assert "No changes" in md


class TestIndex:
    def test_generates_index(self, sample_model, tmp_path):
        result = generate_docs(sample_model, output_dir=tmp_path)
        readme = (tmp_path / "README.md").read_text()
        assert "test-project" in readme
        assert "Component Specifications" in readme


class TestFullGeneration:
    def test_all_docs_generated(self, sample_model, tmp_path):
        result = generate_docs(sample_model, output_dir=tmp_path)
        assert (tmp_path / "README.md").exists()
        assert (tmp_path / "dependency-matrix.md").exists()
        assert (tmp_path / "icd.md").exists()
        assert (tmp_path / "health.md").exists()
        assert (tmp_path / "components" / "COMP-1.md").exists()


class TestDocsCLI:
    def test_cli_generates_docs(self, tmp_path):
        from architecture_model.core.types import ArchitectureModel, Component, Entities, ModelMeta
        from architecture_model.core.parser import save_model

        model = ArchitectureModel(
            meta=ModelMeta(project="cli-test", schema_version="1.3"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status="ACTIVE", files=["core.py"], contract="Core logic.")
            ]),
            relationships=[],
        )
        save_model(model, tmp_path / ".architecture-model-extracted.yaml")

        # Import and call the CLI handler directly
        from architecture_model.cli.main import main
        import sys
        old_argv = sys.argv
        sys.argv = ["architecture-model", "docs", str(tmp_path)]
        try:
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        assert (tmp_path / ".architecture-models" / "docs" / "README.md").exists()
