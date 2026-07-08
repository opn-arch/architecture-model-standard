"""Tests for the artifact context assembler."""

import pytest

from architecture_model.artifacts.context import (
    assemble_artifact_context,
    _extract_section_data,
)
from architecture_model.artifacts.templates import ArtifactTemplate, TemplateSection, get_template
from architecture_model.core.types import (
    ArchitectureModel,
    Behavior,
    BehaviorPattern,
    Capability,
    Component,
    ComponentKind,
    Constraint,
    ConstraintType,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Priority as EntityPriority,
    Relationship,
    RelationType,
    Status,
    Strength,
)


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _make_model(**kwargs) -> ArchitectureModel:
    """Create a minimal model with specified entity lists."""
    entities = Entities(
        components=kwargs.get("components", []),
        interfaces=kwargs.get("interfaces", []),
        capabilities=kwargs.get("capabilities", []),
        behaviors=kwargs.get("behaviors", []),
        constraints=kwargs.get("constraints", []),
        layers=kwargs.get("layers", []),
    )
    return ArchitectureModel(
        meta=ModelMeta(
            schema_version="1.4", project="test-project", system="Test System"
        ),
        entities=entities,
        relationships=kwargs.get("relationships", []),
    )


def _make_component(id: str, **kwargs) -> Component:
    return Component(
        id=id,
        name=f"Comp {id}",
        status=Status.ACTIVE,
        kind=kwargs.get("kind", ComponentKind.MODULE),
        layer=kwargs.get("layer", "core"),
        files=kwargs.get("files", ["src/main.py"]),
        responsibilities=kwargs.get("responsibilities", ["Process data"]),
    )


def _make_interface(id: str, **kwargs) -> Interface:
    return Interface(
        id=id,
        name=f"Interface {id}",
        status=Status.ACTIVE,
        type=kwargs.get("type", InterfaceType.REST),
        protocol=kwargs.get("protocol", "HTTP"),
        provider=kwargs.get("provider", "COMP-1"),
        consumer=kwargs.get("consumer", "COMP-2"),
        endpoints=kwargs.get("endpoints", [{"method": "GET", "path": "/api/v1"}]),
    )


SAMPLE_MANIFEST = {
    "metrics": {
        "total_lines": 5000,
        "total_files": 40,
        "total_modules": 8,
        "avg_complexity": 3.2,
    },
    "test_files": [
        "tests/test_main.py",
        "tests/test_utils.py",
    ],
}


def _simple_template() -> ArtifactTemplate:
    """A minimal template for testing."""
    return ArtifactTemplate(
        artifact_id="test-artifact",
        filename="test-artifact.md",
        system_prompt="You are a test writer.",
        sections=[
            TemplateSection(
                heading="## Components",
                source="components",
                instructions="List all components.",
            ),
            TemplateSection(
                heading="## Relationships",
                source="relationships",
                instructions="Show all relationships.",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Tests: assemble_artifact_context
# ---------------------------------------------------------------------------


class TestAssembleBasic:
    """Test basic context assembly."""

    def test_assemble_basic_context(self):
        """Given system-overview template + model with components, returns
        string containing system prompt, section headings, and component data."""
        model = _make_model(components=[_make_component("COMP-1")])
        template = get_template("system-overview")
        assert template is not None

        result = assemble_artifact_context(template, model)

        # Should contain system prompt
        assert template.system_prompt in result
        # Should contain section headings
        assert "## Key Components" in result
        # Should contain component data
        assert "COMP-1" in result

    def test_assemble_includes_system_prompt(self):
        """Output starts with the template's system_prompt."""
        model = _make_model()
        template = _simple_template()

        result = assemble_artifact_context(template, model)

        # System prompt should appear at the start
        assert result.startswith("SYSTEM: You are a test writer.")

    def test_assemble_includes_section_headings(self):
        """Each section heading appears in output."""
        model = _make_model(
            components=[_make_component("COMP-1")],
            relationships=[
                Relationship(
                    type=RelationType.DEPENDS_ON,
                    from_id="COMP-1",
                    to_id="COMP-2",
                )
            ],
        )
        template = _simple_template()

        result = assemble_artifact_context(template, model)

        assert "## Components" in result
        assert "## Relationships" in result

    def test_assemble_includes_instructions(self):
        """Section instructions appear in output."""
        model = _make_model(components=[_make_component("COMP-1")])
        template = _simple_template()

        result = assemble_artifact_context(template, model)

        assert "INSTRUCTIONS: List all components." in result
        assert "INSTRUCTIONS: Show all relationships." in result

    def test_assemble_missing_data_graceful(self):
        """If model has no interfaces but template has interface section,
        produces 'No data available' gracefully."""
        model = _make_model()  # No interfaces
        template = ArtifactTemplate(
            artifact_id="api-test",
            filename="api-test.md",
            system_prompt="API doc writer.",
            sections=[
                TemplateSection(
                    heading="## Interfaces",
                    source="interfaces",
                    instructions="Document interfaces.",
                )
            ],
        )

        result = assemble_artifact_context(template, model)

        assert "No data available" in result
        # Should not crash
        assert "## Interfaces" in result

    def test_assemble_respects_token_budget(self):
        """With very low budget, output is truncated but still valid."""
        # Create a model with many components to generate lots of data
        components = [_make_component(f"COMP-{i}") for i in range(50)]
        model = _make_model(components=components)
        template = _simple_template()

        # Very low budget: ~100 tokens = ~400 chars
        result = assemble_artifact_context(template, model, max_tokens=100)

        # Should be within budget (approximate)
        assert len(result) <= 100 * 4 + 100  # some tolerance
        # Should still contain structure
        assert "SYSTEM:" in result


# ---------------------------------------------------------------------------
# Tests: _extract_section_data
# ---------------------------------------------------------------------------


class TestExtractSectionData:
    """Test individual section data extraction."""

    def test_extract_components_format(self):
        """_extract_section_data('components', model, None) returns formatted list."""
        model = _make_model(
            components=[
                _make_component("COMP-1", layer="web", kind=ComponentKind.SERVICE),
                _make_component("COMP-2", layer="core", kind=ComponentKind.MODULE),
            ]
        )

        result = _extract_section_data("components", model, None)

        assert "COMP-1" in result
        assert "COMP-2" in result
        assert "service" in result
        assert "module" in result
        assert "web" in result
        assert "core" in result
        assert "src/main.py" in result

    def test_extract_relationships_format(self):
        """_extract_section_data('relationships', ...) returns formatted arrows."""
        model = _make_model(
            relationships=[
                Relationship(
                    type=RelationType.DEPENDS_ON,
                    from_id="COMP-1",
                    to_id="COMP-2",
                ),
                Relationship(
                    type=RelationType.REALIZES,
                    from_id="COMP-1",
                    to_id="CAP-1",
                ),
            ]
        )

        result = _extract_section_data("relationships", model, None)

        assert "COMP-1" in result
        assert "COMP-2" in result
        assert "depends-on" in result
        assert "realizes" in result
        # Arrow format
        assert "--" in result
        assert "-->" in result

    def test_extract_manifest_metrics(self):
        """_extract_section_data('manifest.metrics', ...) returns formatted metrics."""
        model = _make_model()

        result = _extract_section_data("manifest.metrics", model, SAMPLE_MANIFEST)

        assert "total_lines" in result
        assert "5000" in result
        assert "total_files" in result
        assert "40" in result

    def test_extract_manifest_tests(self):
        """_extract_section_data('manifest.tests', ...) returns test file summary."""
        model = _make_model()

        result = _extract_section_data("manifest.tests", model, SAMPLE_MANIFEST)

        assert "test_main.py" in result
        assert "test_utils.py" in result
        assert "2" in result  # count of test files

    def test_extract_unknown_source(self):
        """_extract_section_data('unknown', ...) returns 'No data available'."""
        model = _make_model()

        result = _extract_section_data("unknown", model, None)

        assert "No data available" in result

    def test_extract_meta_format(self):
        """_extract_section_data('meta', ...) returns formatted metadata."""
        model = _make_model()

        result = _extract_section_data("meta", model, None)

        assert "test-project" in result
        assert "Test System" in result
        assert "1.4" in result

    def test_extract_capabilities_format(self):
        """_extract_section_data('capabilities', ...) returns formatted capabilities."""
        model = _make_model(
            capabilities=[
                Capability(
                    id="CAP-1",
                    name="User Auth",
                    status=Status.ACTIVE,
                    priority=EntityPriority.HIGH,
                    f_block="F1",
                ),
            ]
        )

        result = _extract_section_data("capabilities", model, None)

        assert "CAP-1" in result
        assert "User Auth" in result
        assert "high" in result
        assert "F1" in result

    def test_extract_behaviors_format(self):
        """_extract_section_data('behaviors', ...) returns formatted behaviors."""
        model = _make_model(
            behaviors=[
                Behavior(
                    id="BEH-1",
                    name="Login Flow",
                    status=Status.ACTIVE,
                    trigger="user_click",
                    pattern=BehaviorPattern.SEQUENTIAL,
                    steps=["Validate input", "Check credentials"],
                ),
            ]
        )

        result = _extract_section_data("behaviors", model, None)

        assert "BEH-1" in result
        assert "Login Flow" in result
        assert "user_click" in result
        assert "sequential" in result
        assert "Validate input" in result

    def test_extract_constraints_format(self):
        """_extract_section_data('constraints', ...) returns formatted constraints."""
        model = _make_model(
            constraints=[
                Constraint(
                    id="CON-1",
                    name="Response Time",
                    status=Status.ACTIVE,
                    type=ConstraintType.PERFORMANCE,
                    metric="p99_latency",
                    threshold="200ms",
                ),
            ]
        )

        result = _extract_section_data("constraints", model, None)

        assert "CON-1" in result
        assert "Response Time" in result
        assert "performance" in result
        assert "p99_latency" in result
        assert "200ms" in result

    def test_extract_layers_format(self):
        """_extract_section_data('layers', ...) returns formatted layers."""
        model = _make_model(
            layers=[
                Layer(
                    id="L-WEB",
                    name="Web Layer",
                    status=Status.ACTIVE,
                    order=1,
                    technology=["React", "TypeScript"],
                ),
            ]
        )

        result = _extract_section_data("layers", model, None)

        assert "L-WEB" in result
        assert "Web Layer" in result
        assert "1" in result
        assert "React" in result

    def test_extract_manifest_metrics_none_manifest(self):
        """manifest.metrics with None manifest returns 'No data available'."""
        model = _make_model()

        result = _extract_section_data("manifest.metrics", model, None)

        assert "No data available" in result

    def test_extract_manifest_tests_none_manifest(self):
        """manifest.tests with None manifest returns 'No data available'."""
        model = _make_model()

        result = _extract_section_data("manifest.tests", model, None)

        assert "No data available" in result
