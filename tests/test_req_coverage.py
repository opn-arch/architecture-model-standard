"""Tests for requirement traceability coverage (dimension 8)."""

from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Requirement, Relationship,
)
from architecture_model.core.coverage import _check_requirement_traceability


class TestRequirementCoverage:
    def test_no_requirements_returns_not_run(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(components=[]),
            relationships=[],
        )
        result = _check_requirement_traceability(model)
        assert result.score == 100
        assert result.total == 0
        assert "not_run" in result.details or "no requirements" in result.details

    def test_all_satisfied(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                components=[Component(id="COMP-1", name="A", status="ACTIVE")],
                requirements=[Requirement(id="REQ-001", name="Auth", status="ACTIVE", text="Must auth")],
            ),
            relationships=[
                Relationship(from_id="COMP-1", to_id="REQ-001", type="satisfies"),
            ],
        )
        result = _check_requirement_traceability(model)
        assert result.score == 100
        assert result.matched == 1
        assert result.total == 1
        assert len(result.missing) == 0

    def test_orphan_requirement(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                components=[Component(id="COMP-1", name="A", status="ACTIVE")],
                requirements=[
                    Requirement(id="REQ-001", name="Auth", status="ACTIVE", text="Must auth"),
                    Requirement(id="REQ-002", name="Logging", status="ACTIVE", text="Must log"),
                ],
            ),
            relationships=[
                Relationship(from_id="COMP-1", to_id="REQ-001", type="satisfies"),
            ],
        )
        result = _check_requirement_traceability(model)
        assert result.score == 50
        assert result.matched == 1
        assert result.total == 2
        assert any("REQ-002" in m for m in result.missing)

    def test_deprecated_requirements_excluded(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                components=[],
                requirements=[
                    Requirement(id="REQ-001", name="Old", status="DEPRECATED", text="Deprecated"),
                ],
            ),
            relationships=[],
        )
        result = _check_requirement_traceability(model)
        assert result.score == 100
        assert result.total == 0
