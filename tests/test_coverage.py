"""Tests for coverage analysis module."""
import hashlib
import json

import pytest

from architecture_model.core.coverage import (
    CoverageCheck,
    CoverageResult,
    coverage_report,
    _check_component_coverage,
    _check_relationship_accuracy,
    _check_capability_coverage,
    _check_interface_coverage,
    _check_staleness,
)
from architecture_model.core.types import (
    ArchitectureModel,
    ModelMeta,
    Entities,
    Component,
    Capability,
    Interface,
    Relationship,
    RelationType,
    Status,
    InterfaceType,
)


def _make_model(
    components=None,
    capabilities=None,
    interfaces=None,
    relationships=None,
    manifest_hash="",
):
    meta = ModelMeta(schema_version="1.4", project="test", manifest_hash=manifest_hash)
    entities = Entities(
        components=components or [],
        capabilities=capabilities or [],
        interfaces=interfaces or [],
    )
    return ArchitectureModel(
        meta=meta,
        entities=entities,
        relationships=relationships or [],
    )


# --- Dataclass construction ---


class TestDataclasses:
    def test_coverage_check_defaults(self):
        c = CoverageCheck(name="test", score=50.0, matched=1, total=2)
        assert c.missing == []
        assert c.extra == []
        assert c.details == ""

    def test_coverage_result_defaults(self):
        r = CoverageResult()
        assert r.checks == []
        assert r.overall_score == 0.0

    def test_coverage_result_summary(self):
        r = CoverageResult(
            checks=[
                CoverageCheck(name="Full", score=100.0, matched=3, total=3),
                CoverageCheck(name="Partial", score=50.0, matched=1, total=2, missing=["x"]),
            ],
            overall_score=75.0,
        )
        s = r.summary()
        assert "✓ Full" in s
        assert "✗ Partial" in s
        assert "⚠ Missing: x" in s
        assert "75%" in s


# --- Component coverage ---


class TestComponentCoverage:
    def test_full_coverage(self):
        model = _make_model(components=[
            Component(id="C1", name="parser", status=Status.ACTIVE),
            Component(id="C2", name="validator", status=Status.ACTIVE),
        ])
        manifest = {"modules": ["src/parser.py", "src/validator.py"]}
        result = _check_component_coverage(model, manifest)
        assert result.score == 100.0
        assert result.matched == 2
        assert result.missing == []
        assert result.extra == []

    def test_missing_component(self):
        model = _make_model(components=[
            Component(id="C1", name="parser", status=Status.ACTIVE),
        ])
        manifest = {"modules": ["src/parser.py", "src/validator.py"]}
        result = _check_component_coverage(model, manifest)
        assert result.score == 50.0
        assert "validator" in result.missing

    def test_extra_component(self):
        model = _make_model(components=[
            Component(id="C1", name="parser", status=Status.ACTIVE),
            Component(id="C2", name="extra", status=Status.ACTIVE),
        ])
        manifest = {"modules": ["src/parser.py"]}
        result = _check_component_coverage(model, manifest)
        assert result.score == 100.0
        assert "extra" in result.extra

    def test_skips_init(self):
        model = _make_model(components=[
            Component(id="C1", name="parser", status=Status.ACTIVE),
        ])
        manifest = {"modules": ["src/__init__.py", "src/parser.py"]}
        result = _check_component_coverage(model, manifest)
        assert result.score == 100.0
        assert result.total == 1

    def test_dict_modules(self):
        model = _make_model(components=[
            Component(id="C1", name="utils", status=Status.ACTIVE),
        ])
        manifest = {"modules": [{"file": "src/utils.py", "exports": ["foo"]}]}
        result = _check_component_coverage(model, manifest)
        assert result.score == 100.0


# --- Relationship accuracy ---


class TestRelationshipAccuracy:
    def test_matching(self):
        model = _make_model(
            components=[
                Component(id="C1", name="parser", status=Status.ACTIVE),
                Component(id="C2", name="validator", status=Status.ACTIVE),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="C2"),
            ],
        )
        manifest = {
            "interfaces": [{"source": "src/parser.py", "target": "src/validator.py"}]
        }
        result = _check_relationship_accuracy(model, manifest)
        assert result.score == 100.0
        assert result.matched == 1

    def test_missing_dependency(self):
        model = _make_model(components=[
            Component(id="C1", name="parser", status=Status.ACTIVE),
            Component(id="C2", name="validator", status=Status.ACTIVE),
        ])
        manifest = {
            "interfaces": [{"source": "src/parser.py", "target": "src/validator.py"}]
        }
        result = _check_relationship_accuracy(model, manifest)
        assert result.score == 0.0
        assert "parser → validator" in result.missing

    def test_extra_relationship(self):
        model = _make_model(
            components=[
                Component(id="C1", name="parser", status=Status.ACTIVE),
                Component(id="C2", name="validator", status=Status.ACTIVE),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="C2"),
            ],
        )
        manifest = {"interfaces": []}
        result = _check_relationship_accuracy(model, manifest)
        assert result.score == 0.0  # no manifest edges, so matched=0/total=1
        assert "parser → validator" in result.extra


# --- Capability coverage ---


class TestCapabilityCoverage:
    def test_all_covered(self):
        model = _make_model(capabilities=[
            Capability(id="CAP1", name="Cap1", status=Status.ACTIVE, f_block="core"),
            Capability(id="CAP2", name="Cap2", status=Status.ACTIVE, f_block="utils"),
        ])
        manifest = {"functional_blocks": {"core": {}, "utils": {}}}
        result = _check_capability_coverage(model, manifest)
        assert result.score == 100.0
        assert result.matched == 2

    def test_missing_fblock(self):
        model = _make_model(capabilities=[
            Capability(id="CAP1", name="Cap1", status=Status.ACTIVE, f_block="core"),
        ])
        manifest = {"functional_blocks": {"core": {}, "utils": {}}}
        result = _check_capability_coverage(model, manifest)
        assert result.score == 50.0
        assert "utils" in result.missing

    def test_extra_fblock(self):
        model = _make_model(capabilities=[
            Capability(id="CAP1", name="Cap1", status=Status.ACTIVE, f_block="core"),
            Capability(id="CAP2", name="Cap2", status=Status.ACTIVE, f_block="extra"),
        ])
        manifest = {"functional_blocks": {"core": {}}}
        result = _check_capability_coverage(model, manifest)
        assert result.score == 100.0
        assert "extra" in result.extra


# --- Interface coverage ---


class TestInterfaceCoverage:
    def test_with_exposes(self):
        model = _make_model(
            components=[
                Component(id="C1", name="parser", status=Status.ACTIVE),
            ],
            interfaces=[
                Interface(id="I1", name="ParserAPI", status=Status.ACTIVE),
            ],
            relationships=[
                Relationship(type=RelationType.EXPOSES, from_id="C1", to_id="I1"),
            ],
        )
        manifest = {"modules": [{"file": "src/parser.py", "exports": ["parse"]}]}
        result = _check_interface_coverage(model, manifest)
        assert result.score == 100.0
        assert result.matched == 1

    def test_without_exposes(self):
        model = _make_model(
            components=[
                Component(id="C1", name="parser", status=Status.ACTIVE),
            ],
        )
        manifest = {"modules": [{"file": "src/parser.py", "exports": ["parse"]}]}
        result = _check_interface_coverage(model, manifest)
        assert result.score == 0.0
        assert "parser" in result.missing

    def test_no_exports(self):
        model = _make_model(components=[
            Component(id="C1", name="parser", status=Status.ACTIVE),
        ])
        manifest = {"modules": [{"file": "src/parser.py", "exports": []}]}
        result = _check_interface_coverage(model, manifest)
        # No exporting modules so total defaults to 1, matched=0
        assert result.score == 0.0
        assert result.total == 1


# --- Staleness ---


class TestStaleness:
    def _hash_manifest(self, manifest):
        return hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest()[:16]

    def test_current_hash(self):
        manifest = {"modules": ["a.py"]}
        h = self._hash_manifest(manifest)
        model = _make_model(manifest_hash=h)
        result = _check_staleness(model, manifest)
        assert result.score == 100.0

    def test_stale_hash(self):
        manifest = {"modules": ["a.py"]}
        model = _make_model(manifest_hash="deadbeef12345678")
        result = _check_staleness(model, manifest)
        assert result.score == 0.0
        assert any("mismatch" in m.lower() for m in result.missing)

    def test_no_hash(self):
        manifest = {"modules": ["a.py"]}
        model = _make_model(manifest_hash="")
        result = _check_staleness(model, manifest)
        assert result.score == 0.0
        assert any("not set" in m for m in result.missing)


# --- Full report ---


class TestCoverageReport:
    def test_full_report(self):
        manifest = {"modules": ["src/parser.py"], "interfaces": [], "functional_blocks": {"core": {}}}
        h = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
        model = _make_model(
            components=[Component(id="C1", name="parser", status=Status.ACTIVE)],
            capabilities=[Capability(id="CAP1", name="Cap", status=Status.ACTIVE, f_block="core")],
            manifest_hash=h,
        )
        result = coverage_report(model, manifest)
        assert len(result.checks) == 7
        assert result.overall_score > 0
        check_names = [c.name for c in result.checks]
        assert "F-Block Quality" in check_names
        assert "requirement_traceability" in check_names
