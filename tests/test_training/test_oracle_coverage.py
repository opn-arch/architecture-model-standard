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
