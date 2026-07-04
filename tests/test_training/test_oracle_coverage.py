"""Tests for manifest coverage computation."""

import pytest
from architecture_model.training.oracle_coverage import (
    ManifestCoverageComputer,
    CoverageResult,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, Component, Capability, Layer,
    Relationship, RelationType, Status, ModelMeta,
)


def _make_manifest():
    """Create a minimal test manifest."""
    return {
        "modules": [
            {"file": "src/client.py", "name": "HTTP Client", "line_count": 200,
             "functions": ["get", "post", "connect"], "imports": ["src/pool.py"], "status": "active"},
            {"file": "src/pool.py", "name": "Connection Pool", "line_count": 150,
             "functions": ["acquire", "release"], "imports": [], "status": "active"},
            {"file": "src/utils.py", "name": "Utilities", "line_count": 30,
             "functions": ["format_url"], "imports": [], "status": "active"},
        ],
        "interfaces": [
            {"source": "src/client.py", "target": "src/pool.py", "import_path": "pool"},
        ],
        "functional_blocks": {
            "F1": {"name": "networking", "status": "active",
                   "sub_functions": [{"file": "src/client.py"}, {"file": "src/pool.py"}]},
        },
    }


def _make_model_covering_all():
    meta = ModelMeta(schema_version="1.0", project="test")
    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[Capability(id="CAP1", name="networking", status=Status.ACTIVE)],
            layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            components=[
                Component(id="C1", name="HTTP Client", layer="L1", status=Status.ACTIVE),
                Component(id="C2", name="Connection Pool", layer="L1", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="C2"),
        ],
    )


class TestManifestCoverage:
    def test_full_coverage(self):
        manifest = _make_manifest()
        model = _make_model_covering_all()
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert result.module_coverage > 0.8
        assert result.interface_coverage == 1.0
        assert result.block_coverage == 1.0
        assert result.overall > 0.8

    def test_partial_coverage(self):
        manifest = _make_manifest()
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
                components=[
                    Component(id="C1", name="HTTP Client", layer="L1", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert result.module_coverage < 0.8
        assert result.interface_coverage == 0.0
        assert len(result.uncovered_modules) >= 1
        assert len(result.uncovered_interfaces) >= 1

    def test_significance_weighting(self):
        """Large modules (by LOC) matter more than small ones."""
        manifest = _make_manifest()
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
                components=[
                    Component(id="C1", name="Utilities", layer="L1", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        # Utilities is only 30 LOC out of 380 total => covering only it = ~0.079
        assert result.module_coverage < 0.2

    def test_empty_manifest(self):
        manifest = {"modules": [], "interfaces": [], "functional_blocks": {}}
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta, entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[], components=[]),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert result.overall == 1.0

    def test_uncovered_lists(self):
        manifest = _make_manifest()
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta, entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[], components=[]),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert "src/client.py" in result.uncovered_modules
        assert ("src/client.py", "src/pool.py") in result.uncovered_interfaces

    def test_path_based_matching(self):
        """Components with architectural names can cover modules via path-word overlap.

        Module: src/validation/engine.py (name: "Core validation logic")
        Component: "Validation Engine" — name tokens {validation, engine} overlap path tokens.
        """
        manifest = {
            "modules": [
                {"file": "src/validation/engine.py", "name": "Core validation logic",
                 "line_count": 200, "functions": ["validate"], "imports": [], "status": "active"},
                {"file": "src/validation/rules.py", "name": "Rule definitions",
                 "line_count": 100, "functions": ["check_rule"], "imports": ["src/validation/engine.py"],
                 "status": "active"},
            ],
            "interfaces": [
                {"source": "src/validation/rules.py", "target": "src/validation/engine.py",
                 "import_path": "engine"},
            ],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
                components=[
                    Component(id="C1", name="Validation Engine", layer="L1", status=Status.ACTIVE),
                    Component(id="C2", name="Rule Processor", layer="L1", status=Status.ACTIVE),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C2", to_id="C1"),
            ],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        # "Validation Engine" matches "src/validation/engine.py" via path tokens
        # "Rule Processor" matches "src/validation/rules.py" via 'rules' token
        assert result.module_coverage >= 0.5  # At least engine.py covered
        # Interface: rules→engine maps to C2→C1 relationship
        assert result.interface_coverage == 1.0

    def test_explicit_files_strategy(self):
        """Components with explicit files lists get matched first."""
        manifest = {
            "modules": [
                {"file": "src/main.py", "name": "Application Entry",
                 "line_count": 50, "functions": ["main"], "imports": [], "status": "active"},
            ],
            "interfaces": [],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[],
                components=[
                    Component(id="C1", name="Orchestrator", layer="",
                              files=["src/main.py"], status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert result.module_coverage == 1.0

    def test_block_matches_layers_too(self):
        """F-blocks can match against layer names, not just capabilities."""
        manifest = {
            "modules": [],
            "interfaces": [],
            "functional_blocks": {
                "F1": {"name": "data access", "status": "active", "sub_functions": []},
            },
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[Layer(id="L1", name="Data Access Layer", status=Status.ACTIVE)],
                components=[],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert result.block_coverage == 1.0

    def test_internal_dependency_covered(self):
        """If two modules are covered by the SAME component, their edge counts as covered."""
        manifest = {
            "modules": [
                {"file": "src/client/get.py", "name": "GET handler",
                 "line_count": 50, "functions": ["get"], "imports": ["src/client/base.py"],
                 "status": "active"},
                {"file": "src/client/base.py", "name": "Base client",
                 "line_count": 80, "functions": ["request"], "imports": [],
                 "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client/get.py", "target": "src/client/base.py",
                 "import_path": "base"},
            ],
            "functional_blocks": {},
        }
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[],
                components=[
                    Component(id="C1", name="HTTP Client", layer="",
                              files=["src/client/get.py", "src/client/base.py"],
                              status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        # Both modules covered by same component → internal dependency → covered
        assert result.module_coverage == 1.0
        assert result.interface_coverage == 1.0
