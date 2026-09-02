"""Tests for architecture_model.core.validator."""

from __future__ import annotations

import pytest

from architecture_model.core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Entities,
    ModelMeta,
    Priority,
    Relationship,
    RelationType,
    Status,
    Strength,
)
from architecture_model.core.validator import (
    Severity,
    ValidationResult,
    validate_model,
)

from .conftest import requires_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meta(**overrides) -> ModelMeta:
    defaults = {
        "schema_version": "0.1.0",
        "project": "test-project",
        "system": "test-system",
        "generated_at": "2024-01-01T00:00:00Z",
        "source_artifacts": ["functional-architecture"],
    }
    defaults.update(overrides)
    return ModelMeta(**defaults)


def _make_perfect_model() -> ArchitectureModel:
    """Create a model that should score 100/100 — no errors, no warnings."""
    cap = Capability(
        id="CAP-S1",
        name="Ingest Data",
        status=Status.ACTIVE,
        source_block="S1",
        priority=Priority.HIGH,
    )
    behavior = Behavior(
        id="UC-01",
        name="Ingest Log",
        status=Status.ACTIVE,
        actor="actor-dev",
        tags=["S1"],
    )
    actor = Actor(
        id="actor-dev",
        name="Developer",
        status=Status.ACTIVE,
        type=ActorType.HUMAN,
    )
    component = Component(
        id="comp-ingest",
        name="ingest.py",
        status=Status.ACTIVE,
        layer="pipeline-layer",
        source_block="S1",
    )
    realizes_rel = Relationship(
        type=RelationType.REALIZES,
        from_id="UC-01",
        to_id="CAP-S1",
        description="UC realizes capability",
    )
    comp_realizes_rel = Relationship(
        type=RelationType.REALIZES,
        from_id="comp-ingest",
        to_id="CAP-S1",
        description="Component realizes capability",
    )
    return ArchitectureModel(
        meta=_make_meta(),
        entities=Entities(
            actors=[actor],
            capabilities=[cap],
            behaviors=[behavior],
            components=[component],
        ),
        relationships=[realizes_rel, comp_realizes_rel],
    )


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestScoring:
    """Test the scoring mechanism of ValidationResult."""

    def test_perfect_model_scores_100(self):
        """A model with no issues scores 100/100."""
        model = _make_perfect_model()
        result = validate_model(model)
        assert result.score == 100, f"Expected 100, got {result.score}. Issues: {result.issues}"

    def test_score_deducts_10_per_error(self):
        """Each ERROR deducts 10 points."""
        result = ValidationResult()
        from architecture_model.core.validator import ValidationIssue

        result.issues.append(
            ValidationIssue(severity=Severity.ERROR, code="TEST", message="test error")
        )
        assert result.score == 90

    def test_score_deducts_2_per_warning(self):
        """Each WARNING deducts 2 points."""
        result = ValidationResult()
        from architecture_model.core.validator import ValidationIssue

        result.issues.append(
            ValidationIssue(severity=Severity.WARNING, code="TEST", message="test warning")
        )
        assert result.score == 98

    def test_score_floors_at_zero(self):
        """Score never goes below 0."""
        result = ValidationResult()
        from architecture_model.core.validator import ValidationIssue

        for i in range(20):
            result.issues.append(
                ValidationIssue(severity=Severity.ERROR, code="TEST", message=f"error {i}")
            )
        assert result.score == 0

    def test_info_does_not_affect_score(self):
        """INFO issues don't reduce score."""
        result = ValidationResult()
        from architecture_model.core.validator import ValidationIssue

        result.issues.append(
            ValidationIssue(severity=Severity.INFO, code="TEST", message="info note")
        )
        assert result.score == 100


# ---------------------------------------------------------------------------
# Duplicate ID detection
# ---------------------------------------------------------------------------


class TestDuplicateIDs:
    """Test that duplicate entity IDs produce ERROR."""

    def test_duplicate_id_across_types_errors(self):
        """Same ID used in two entity types → ERROR."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                actors=[
                    Actor(id="shared-id", name="Actor", status=Status.ACTIVE, type=ActorType.HUMAN)
                ],
                capabilities=[
                    Capability(
                        id="shared-id", name="Capability", status=Status.ACTIVE, source_block="S1"
                    )
                ],
            ),
            relationships=[
                Relationship(
                    type=RelationType.REALIZES,
                    from_id="shared-id",
                    to_id="shared-id",
                )
            ],
        )
        result = validate_model(model)
        dup_errors = [i for i in result.issues if i.code == "DUPLICATE_ID"]
        assert len(dup_errors) >= 1
        assert dup_errors[0].severity == Severity.ERROR

    def test_duplicate_id_within_same_type_errors(self):
        """Same ID used twice within components → ERROR."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[
                    Component(id="comp-a", name="CompA", status=Status.ACTIVE),
                    Component(id="comp-a", name="CompB", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        result = validate_model(model)
        dup_errors = [i for i in result.issues if i.code == "DUPLICATE_ID"]
        assert len(dup_errors) >= 1

    def test_unique_ids_no_duplicates(self):
        """Unique IDs across all types → no DUPLICATE_ID issues."""
        model = _make_perfect_model()
        result = validate_model(model)
        dup_errors = [i for i in result.issues if i.code == "DUPLICATE_ID"]
        assert len(dup_errors) == 0


# ---------------------------------------------------------------------------
# Dangling reference detection
# ---------------------------------------------------------------------------


class TestDanglingRefs:
    @pytest.mark.parametrize("field, reference", [
        ("actor_id", "ACT-404"),
        ("capability_id", "CAP-404"),
    ])
    def test_dangling_behavior_linkage_is_error(self, field, reference):
        behavior = Behavior(id="BEH-1", name="Flow", status=Status.ACTIVE)
        setattr(behavior, field, reference)
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="2.0.0"),
            entities=Entities(behaviors=[behavior]),
            relationships=[],
        )

        result = validate_model(model)

        assert any(
            issue.severity == Severity.ERROR
            and issue.code == "DANGLING_REF"
            and issue.context == field
            for issue in result.issues
        )
    """Test detection of relationships referencing non-existent entities."""

    def test_dangling_from_ref(self):
        """Relationship with non-existent from_id → DANGLING_REF warning."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                capabilities=[
                    Capability(id="CAP-S1", name="Cap", status=Status.ACTIVE, source_block="S1")
                ],
            ),
            relationships=[
                Relationship(
                    type=RelationType.REALIZES,
                    from_id="nonexistent-entity",
                    to_id="CAP-S1",
                )
            ],
        )
        result = validate_model(model)
        dangling = [i for i in result.issues if i.code == "DANGLING_REF"]
        assert len(dangling) >= 1

    def test_dangling_to_ref(self):
        """Relationship with non-existent to_id → DANGLING_REF warning."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                behaviors=[Behavior(id="UC-01", name="UC", status=Status.ACTIVE, tags=["S1"])],
            ),
            relationships=[
                Relationship(
                    type=RelationType.REALIZES,
                    from_id="UC-01",
                    to_id="nonexistent-cap",
                )
            ],
        )
        result = validate_model(model)
        dangling = [i for i in result.issues if i.code == "DANGLING_REF"]
        assert len(dangling) >= 1

    def test_known_external_not_dangling(self):
        """References to known external IDs should not trigger DANGLING_REF."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[Component(id="comp-a", name="CompA", status=Status.ACTIVE)],
            ),
            relationships=[
                Relationship(
                    type=RelationType.DEPENDS_ON,
                    from_id="comp-a",
                    to_id="external-llm",
                )
            ],
        )
        result = validate_model(model)
        dangling = [i for i in result.issues if i.code == "DANGLING_REF"]
        assert len(dangling) == 0


# ---------------------------------------------------------------------------
# Orphan entity detection
# ---------------------------------------------------------------------------


class TestOrphans:
    """Test detection of orphan entities (no relationships)."""

    def test_orphan_component_produces_info(self):
        """Active component with no relationships → INFO issue."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[Component(id="orphan-comp", name="Orphan", status=Status.ACTIVE)],
            ),
            relationships=[],
        )
        result = validate_model(model)
        orphans = [i for i in result.issues if i.code == "ORPHAN_COMPONENT"]
        assert len(orphans) >= 1
        assert orphans[0].severity == Severity.INFO

    def test_orphan_behavior_produces_info(self):
        """Active behavior with no relationships → INFO issue."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                behaviors=[Behavior(id="orphan-beh", name="Orphan UC", status=Status.ACTIVE)],
            ),
            relationships=[],
        )
        result = validate_model(model)
        orphans = [i for i in result.issues if i.code == "ORPHAN_BEHAVIOR"]
        assert len(orphans) >= 1
        assert orphans[0].severity == Severity.INFO

    def test_dormant_component_not_orphan(self):
        """DORMANT component with no relationships → no ORPHAN issue."""
        model = ArchitectureModel(
            meta=_make_meta(),
            entities=Entities(
                components=[Component(id="dormant-comp", name="Dormant", status=Status.DORMANT)],
            ),
            relationships=[],
        )
        result = validate_model(model)
        orphans = [i for i in result.issues if i.code == "ORPHAN_COMPONENT"]
        assert len(orphans) == 0


# ---------------------------------------------------------------------------
# Real model validation
# ---------------------------------------------------------------------------


@requires_model
class TestRealModel:
    """Test that the real architecture model validates well."""

    def test_real_model_is_valid(self, model: ArchitectureModel):
        """Real model has no errors (is_valid=True)."""
        result = validate_model(model)
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        assert result.is_valid, f"Model invalid. Errors: {errors}"

    def test_real_model_scores_high(self, model: ArchitectureModel):
        """Real model scores >= 80/100."""
        result = validate_model(model)
        assert result.score >= 80, f"Score too low: {result.score}. Summary: {result.summary()}"

    def test_strict_mode_promotes_warnings(self):
        """Strict mode promotes all warnings to errors."""
        model = _make_perfect_model()
        # Remove realizing relationship to create a warning
        model.relationships = []
        result = validate_model(model, strict=True)
        warnings_as_errors = [
            i
            for i in result.issues
            if i.severity == Severity.ERROR and i.code == "UNREALIZED_CAPABILITY"
        ]
        assert len(warnings_as_errors) >= 1
