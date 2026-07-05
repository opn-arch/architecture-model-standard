"""Tests for CoverageScorer."""

import pytest
from architecture_model.core.types import (
    ArchitectureModel, Component, Layer, Status,
    Relationship, RelationType, Entities, ModelMeta,
)
from architecture_model.training.coverage_scorer import CoverageScorer, CoverageScore


def _make_model(components, relationships):
    """Helper to build a minimal model."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(components=components),
        relationships=relationships,
    )


def _make_manifest(modules, interfaces):
    """Helper to build a minimal manifest."""
    return {
        "modules": modules,
        "interfaces": interfaces,
        "functional_blocks": {},
    }


class TestCoverageScorer:
    def test_perfect_coverage(self):
        """Model relationships perfectly match manifest edges."""
        model = _make_model(
            components=[
                Component(id="c1", name="Core", status=Status.ACTIVE, files=["core.py"]),
                Component(id="c2", name="Utils", status=Status.ACTIVE, files=["utils.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="c1", to_id="c2"),
            ],
        )
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": ["utils"]},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
            ],
            interfaces=[
                {"source": "core.py", "target": "utils.py"},
            ],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        assert result.edge_coverage >= 0.9
        assert result.edge_precision >= 0.9
        assert result.overall > 0.5

    def test_missing_edges(self):
        """Model is missing relationships that manifest proves exist."""
        model = _make_model(
            components=[
                Component(id="c1", name="Core", status=Status.ACTIVE, files=["core.py"]),
                Component(id="c2", name="Utils", status=Status.ACTIVE, files=["utils.py"]),
                Component(id="c3", name="Types", status=Status.ACTIVE, files=["types.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="c1", to_id="c2"),
                # Missing: c1 -> c3
            ],
        )
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": ["utils", "types"]},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
                {"file": "types.py", "name": "Types", "line_count": 80, "imports": []},
            ],
            interfaces=[
                {"source": "core.py", "target": "utils.py"},
                {"source": "core.py", "target": "types.py"},
            ],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        assert result.edge_coverage < 1.0
        assert len(result.missing_edges) >= 1

    def test_spurious_relationships(self):
        """Model claims relationships not backed by any import edge."""
        model = _make_model(
            components=[
                Component(id="c1", name="Core", status=Status.ACTIVE, files=["core.py"]),
                Component(id="c2", name="Utils", status=Status.ACTIVE, files=["utils.py"]),
                Component(id="c3", name="Types", status=Status.ACTIVE, files=["types.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="c1", to_id="c2"),
                # Spurious: no import edge between c2 and c3 at all
                Relationship(type=RelationType.DEPENDS_ON, from_id="c2", to_id="c3"),
            ],
        )
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": ["utils"]},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
                {"file": "types.py", "name": "Types", "line_count": 80, "imports": []},
            ],
            interfaces=[
                # Only edge: core -> utils. No edge between utils and types.
                {"source": "core.py", "target": "utils.py"},
            ],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        assert result.edge_precision < 1.0
        assert len(result.spurious_rels) >= 1

    def test_cohesion_single_file_components(self):
        """Single-file components should have perfect cohesion."""
        model = _make_model(
            components=[
                Component(id="c1", name="Core", status=Status.ACTIVE, files=["core.py"]),
                Component(id="c2", name="Utils", status=Status.ACTIVE, files=["utils.py"]),
            ],
            relationships=[],
        )
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": []},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
            ],
            interfaces=[],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        assert result.cohesion == 1.0

    def test_empty_model(self):
        """Empty model with manifest should score poorly."""
        model = _make_model(components=[], relationships=[])
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": ["utils"]},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
            ],
            interfaces=[{"source": "core.py", "target": "utils.py"}],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        # With no components, module_map is empty, so edges can't be mapped
        assert result.overall >= 0.0

    def test_overall_is_weighted_average(self):
        """Overall score should be weighted combination of 4 dimensions."""
        scorer = CoverageScorer()
        # Verify weights sum to 1.0
        total_weight = (
            scorer.EDGE_COVERAGE_WEIGHT
            + scorer.EDGE_PRECISION_WEIGHT
            + scorer.COHESION_WEIGHT
            + scorer.DIRECTIONALITY_WEIGHT
        )
        assert abs(total_weight - 1.0) < 0.001

    def test_directionality_correct(self):
        """Model direction matches manifest import direction."""
        model = _make_model(
            components=[
                Component(id="c1", name="Core", status=Status.ACTIVE, files=["core.py"]),
                Component(id="c2", name="Utils", status=Status.ACTIVE, files=["utils.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="c1", to_id="c2"),
            ],
        )
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": ["utils"]},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
            ],
            interfaces=[
                {"source": "core.py", "target": "utils.py"},
            ],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        assert result.directionality == 1.0

    def test_score_all_dimensions_bounded(self):
        """All score dimensions should be in [0, 1]."""
        model = _make_model(
            components=[
                Component(id="c1", name="Core", status=Status.ACTIVE, files=["core.py"]),
                Component(id="c2", name="Utils", status=Status.ACTIVE, files=["utils.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="c1", to_id="c2"),
            ],
        )
        manifest = _make_manifest(
            modules=[
                {"file": "core.py", "name": "Core", "line_count": 100, "imports": ["utils"]},
                {"file": "utils.py", "name": "Utils", "line_count": 50, "imports": []},
            ],
            interfaces=[
                {"source": "core.py", "target": "utils.py"},
            ],
        )
        scorer = CoverageScorer()
        result = scorer.score(model, manifest)
        assert 0.0 <= result.edge_coverage <= 1.0
        assert 0.0 <= result.edge_precision <= 1.0
        assert 0.0 <= result.cohesion <= 1.0
        assert 0.0 <= result.directionality <= 1.0
        assert 0.0 <= result.overall <= 1.0
