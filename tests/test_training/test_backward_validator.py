"""Tests for BackwardValidator — validates model against repo tests and docs."""

import pytest
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, Entities, Component, Capability, Layer,
    ModelMeta, Status,
)
from architecture_model.training.backward_validator import (
    BackwardValidator, BackwardResult,
)


def _make_meta():
    return ModelMeta(schema_version="1.0", project="test")


def _make_manifest_with_modules(files: list[str]) -> dict:
    """Build a minimal manifest with given module files."""
    return {
        "modules": [
            {"file": f, "name": f, "line_count": 100,
             "functions": [], "imports": [], "status": "active"}
            for f in files
        ],
        "interfaces": [],
        "functional_blocks": {},
    }


class TestTestMapping:
    """Check 1: Test structure mapping."""

    def test_test_mapping_finds_tested_components(self, tmp_path):
        """Test file that imports a module maps to the owning component."""
        # Setup repo structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "client.py").write_text("class HTTPClient: pass\n")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_client.py").write_text(
            "from src.client import HTTPClient\n"
            "def test_client(): pass\n"
        )

        # Model: one component owns src/client.py
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[
                    Component(
                        id="C1", name="HTTP Client", layer="L1",
                        status=Status.ACTIVE, files=["src/client.py"],
                    ),
                ],
                capabilities=[],
                layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            ),
        )

        manifest = _make_manifest_with_modules(["src/client.py"])

        validator = BackwardValidator()
        result = validator._check_test_mapping(model, manifest, tmp_path)

        score, tested, untested = result
        assert score == 1.0
        assert "HTTP Client" in tested
        assert untested == []

    def test_test_mapping_identifies_untested(self, tmp_path):
        """Component with no test importing its modules is untested."""
        # Setup repo structure — no test files at all
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "secret.py").write_text("class Secret: pass\n")

        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[
                    Component(
                        id="C1", name="Secret Module", layer="L1",
                        status=Status.ACTIVE, files=["src/secret.py"],
                    ),
                ],
                capabilities=[],
                layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            ),
        )

        manifest = _make_manifest_with_modules(["src/secret.py"])

        validator = BackwardValidator()
        score, tested, untested = validator._check_test_mapping(model, manifest, tmp_path)

        assert score == 0.0
        assert tested == []
        assert "Secret Module" in untested


class TestDocCoverage:
    """Check 2: README/docs feature coverage."""

    def test_doc_coverage_matches_capabilities(self, tmp_path):
        """Feature heading in README matches a capability name."""
        (tmp_path / "README.md").write_text(
            "# My Project\n\n"
            "## Data Validation\n\n"
            "Validates incoming data.\n"
        )

        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[],
                capabilities=[
                    Capability(id="CAP1", name="Data Validation", status=Status.ACTIVE),
                ],
                layers=[],
            ),
        )

        validator = BackwardValidator()
        score, matched, unmatched = validator._check_doc_coverage(model, tmp_path)

        assert score == 1.0
        assert "Data Validation" in matched
        assert unmatched == []

    def test_doc_coverage_skips_generic_headings(self, tmp_path):
        """Generic headings like Installation and License are not features."""
        (tmp_path / "README.md").write_text(
            "# My Project\n\n"
            "## Installation\n\nRun pip install.\n\n"
            "## License\n\nMIT\n"
        )

        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[],
                capabilities=[
                    Capability(id="CAP1", name="Something", status=Status.ACTIVE),
                ],
                layers=[],
            ),
        )

        validator = BackwardValidator()
        score, matched, unmatched = validator._check_doc_coverage(model, tmp_path)

        # No features extracted from generic headings → vacuously satisfied
        assert score == 1.0
        assert matched == []
        assert unmatched == []

    def test_doc_coverage_no_docs_is_vacuous(self, tmp_path):
        """No README at all means doc_coverage = 1.0 (vacuously satisfied)."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[],
                capabilities=[
                    Capability(id="CAP1", name="Anything", status=Status.ACTIVE),
                ],
                layers=[],
            ),
        )

        validator = BackwardValidator()
        score, matched, unmatched = validator._check_doc_coverage(model, tmp_path)

        assert score == 1.0
        assert matched == []
        assert unmatched == []


class TestValidateCombined:
    """Full validate() integration."""

    def test_validate_combines_all_checks(self, tmp_path):
        """Full validate returns BackwardResult with all fields populated."""
        # Setup minimal repo
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "engine.py").write_text("class Engine: pass\n")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_engine.py").write_text(
            "from src.engine import Engine\n"
            "def test_engine(): pass\n"
        )

        (tmp_path / "README.md").write_text(
            "# Project\n\n## Processing Engine\n\nDoes processing.\n"
        )

        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[
                    Component(
                        id="C1", name="Processing Engine", layer="L1",
                        status=Status.ACTIVE, files=["src/engine.py"],
                    ),
                ],
                capabilities=[
                    Capability(id="CAP1", name="Processing Engine", status=Status.ACTIVE),
                ],
                layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            ),
        )

        manifest = {
            "modules": [
                {"file": "src/engine.py", "name": "Engine", "line_count": 100,
                 "functions": ["process"], "imports": [], "status": "active"},
            ],
            "interfaces": [],
            "functional_blocks": {},
        }

        validator = BackwardValidator()
        result = validator.validate(
            model=model,
            manifest=manifest,
            repo_path=tmp_path,
            consistency_score=0.8,
        )

        assert isinstance(result, BackwardResult)
        assert result.test_coverage == 1.0
        assert result.doc_coverage == 1.0
        assert result.structural_coverage >= 0.0
        assert result.consistency == 0.8
        assert "Processing Engine" in result.tested_components
        assert result.untested_components == []


class TestOverallWeightedAverage:
    """BackwardResult.overall property."""

    def test_overall_weighted_average(self):
        """Verify weighted formula: 0.3*structural + 0.25*test + 0.2*doc + 0.25*consistency."""
        result = BackwardResult(
            test_coverage=1.0,
            doc_coverage=0.5,
            structural_coverage=0.8,
            consistency=0.6,
        )

        expected = 0.30 * 0.8 + 0.25 * 1.0 + 0.20 * 0.5 + 0.25 * 0.6
        assert abs(result.overall - expected) < 1e-9

    def test_overall_all_zeros(self):
        """All zeros should produce zero."""
        result = BackwardResult()
        assert result.overall == 0.0

    def test_overall_all_ones(self):
        """All 1.0 should produce 1.0."""
        result = BackwardResult(
            test_coverage=1.0,
            doc_coverage=1.0,
            structural_coverage=1.0,
            consistency=1.0,
        )
        assert abs(result.overall - 1.0) < 1e-9
