"""Tests for multi-objective loss evaluator with Pareto front computation."""

import pytest

from architecture_model.core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Constraint,
    Entities,
    Interface,
    Layer,
    ModelMeta,
    Priority,
    Relationship,
    RelationType,
    Status,
    Strength,
)
from architecture_model.training.evaluator import (
    Evaluator,
    LossVector,
    compute_entity_f1,
    compute_relationship_f1,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meta() -> ModelMeta:
    return ModelMeta(
        schema_version="1.0",
        project="test-project",
        source_artifacts=["test"],
    )


def _make_model(
    actors=None,
    capabilities=None,
    behaviors=None,
    interfaces=None,
    constraints=None,
    layers=None,
    components=None,
    relationships=None,
) -> ArchitectureModel:
    """Build a minimal ArchitectureModel with given entities/relationships."""
    return ArchitectureModel(
        meta=_make_meta(),
        entities=Entities(
            actors=actors or [],
            capabilities=capabilities or [],
            behaviors=behaviors or [],
            interfaces=interfaces or [],
            constraints=constraints or [],
            layers=layers or [],
            components=components or [],
        ),
        relationships=relationships or [],
    )


# ---------------------------------------------------------------------------
# LossVector tests
# ---------------------------------------------------------------------------


class TestLossVectorDominates:
    def test_loss_vector_dominates(self):
        """A dominates B when better or equal on all, strictly better on at least one."""
        a = LossVector(
            structural_accuracy=0.9,
            completeness=0.8,
            reconstruction_fidelity=0.7,
            validator_score=90.0,
        )
        b = LossVector(
            structural_accuracy=0.8,
            completeness=0.7,
            reconstruction_fidelity=0.6,
            validator_score=80.0,
        )
        assert a.dominates(b) is True
        assert b.dominates(a) is False

    def test_loss_vector_no_dominance(self):
        """Trade-off: neither dominates when each is better on some objective."""
        a = LossVector(
            structural_accuracy=0.9,
            completeness=0.5,
            reconstruction_fidelity=0.7,
            validator_score=90.0,
        )
        b = LossVector(
            structural_accuracy=0.5,
            completeness=0.9,
            reconstruction_fidelity=0.7,
            validator_score=90.0,
        )
        assert a.dominates(b) is False
        assert b.dominates(a) is False

    def test_loss_vector_self_no_dominance(self):
        """Equal vectors don't dominate each other (requires strictly better on at least one)."""
        a = LossVector(
            structural_accuracy=0.8,
            completeness=0.8,
            reconstruction_fidelity=0.8,
            validator_score=80.0,
        )
        b = LossVector(
            structural_accuracy=0.8,
            completeness=0.8,
            reconstruction_fidelity=0.8,
            validator_score=80.0,
        )
        assert a.dominates(b) is False
        assert b.dominates(a) is False


# ---------------------------------------------------------------------------
# Entity F1 tests
# ---------------------------------------------------------------------------


class TestEntityF1:
    def test_entity_f1_perfect_match(self):
        """Identical entities produce F1 of 1.0."""
        actors = [
            Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN),
            Actor(id="a2", name="Admin", status=Status.ACTIVE, type=ActorType.HUMAN),
        ]
        caps = [
            Capability(id="c1", name="Login", status=Status.ACTIVE),
        ]
        local = _make_model(actors=actors, capabilities=caps)
        oracle = _make_model(actors=actors, capabilities=caps)

        assert compute_entity_f1(local, oracle) == 1.0

    def test_entity_f1_partial_match(self):
        """Local has 1 actor, oracle has 2 → F1 between 0.5 and 1.0."""
        local = _make_model(
            actors=[Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)],
        )
        oracle = _make_model(
            actors=[
                Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN),
                Actor(id="a2", name="Admin", status=Status.ACTIVE, type=ActorType.HUMAN),
            ],
        )
        f1 = compute_entity_f1(local, oracle)
        # precision=1.0 (1/1 local matched), recall=0.5 (1/2 oracle matched)
        # F1 = 2*(1.0*0.5)/(1.0+0.5) = 2/3 ≈ 0.667
        assert 0.5 < f1 < 1.0
        assert abs(f1 - 2 / 3) < 0.01

    def test_entity_f1_no_match(self):
        """Completely different entities produce F1 of 0.0."""
        local = _make_model(
            actors=[Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)],
        )
        oracle = _make_model(
            components=[Component(id="comp1", name="Server", status=Status.ACTIVE)],
        )
        assert compute_entity_f1(local, oracle) == 0.0

    def test_entity_f1_name_fallback(self):
        """Entities with different IDs but same type+name match via name similarity."""
        local = _make_model(
            actors=[Actor(id="actor-user", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)],
        )
        oracle = _make_model(
            actors=[Actor(id="a1", name="user", status=Status.ACTIVE, type=ActorType.HUMAN)],
        )
        # Should match via lowercase name comparison
        assert compute_entity_f1(local, oracle) == 1.0

    def test_entity_f1_empty_models(self):
        """Two empty models produce F1 of 1.0 (no entities to mismatch)."""
        local = _make_model()
        oracle = _make_model()
        # Convention: 0 predicted, 0 actual → perfect (vacuously true)
        assert compute_entity_f1(local, oracle) == 1.0


# ---------------------------------------------------------------------------
# Relationship F1 tests
# ---------------------------------------------------------------------------


class TestRelationshipF1:
    def test_relationship_f1_perfect(self):
        """Identical relationships produce F1 of 1.0."""
        rels = [
            Relationship(type=RelationType.REALIZES, from_id="c1", to_id="cap1"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="c1", to_id="c2"),
        ]
        local = _make_model(relationships=rels)
        oracle = _make_model(relationships=rels)
        assert compute_relationship_f1(local, oracle) == 1.0

    def test_relationship_f1_no_match(self):
        """Completely different relationships produce 0.0."""
        local = _make_model(
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="c1", to_id="cap1"),
            ]
        )
        oracle = _make_model(
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="x1", to_id="x2"),
            ]
        )
        assert compute_relationship_f1(local, oracle) == 0.0

    def test_relationship_f1_empty(self):
        """Both empty → 1.0 (vacuously true)."""
        local = _make_model()
        oracle = _make_model()
        assert compute_relationship_f1(local, oracle) == 1.0


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------


class TestEvaluator:
    def test_evaluator_compute_loss(self):
        """Full loss computation with oracle and code."""
        actors = [Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)]
        rels = [Relationship(type=RelationType.REALIZES, from_id="c1", to_id="cap1")]

        local = _make_model(actors=actors, relationships=rels)
        oracle = _make_model(actors=actors, relationships=rels)

        original_code = "def hello():\n    return 'world'\n"
        reconstructed_code = "def hello():\n    return 'world'\n"

        evaluator = Evaluator()
        loss = evaluator.compute_loss(
            local_model=local,
            oracle_model=oracle,
            original_code=original_code,
            reconstructed_code=reconstructed_code,
        )

        assert isinstance(loss, LossVector)
        # Perfect entity + relationship match → L1 = 1.0
        assert loss.structural_accuracy == 1.0
        # Perfect recall → L2 = 1.0
        assert loss.completeness == 1.0
        # Identical code → L3 = 1.0
        assert loss.reconstruction_fidelity == 1.0
        # Validator score should be computed (0-100 normalized to 0-1 not required, raw score)
        assert 0.0 <= loss.validator_score <= 100.0

    def test_evaluator_compute_loss_no_oracle(self):
        """Without oracle, L1 and L2 default to 0.0."""
        actors = [Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)]
        local = _make_model(actors=actors)

        evaluator = Evaluator()
        loss = evaluator.compute_loss(local_model=local)

        assert loss.structural_accuracy == 0.0
        assert loss.completeness == 0.0
        assert loss.reconstruction_fidelity == 0.0
        # Validator always runs
        assert 0.0 <= loss.validator_score <= 100.0

    def test_entity_recall_no_double_match(self):
        """A local entity matched by ID in Pass 1 should not re-match by name in Pass 2."""
        # local has 1 entity that could match two oracle entities
        local = _make_model(actors=[
            Actor(id="ACT-1", name="Admin", status=Status.ACTIVE, type=ActorType.HUMAN),
        ])
        oracle = _make_model(actors=[
            Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN),
            Actor(id="ACT-2", name="Admin", status=Status.ACTIVE, type=ActorType.HUMAN),
        ])
        # local[0] matches oracle[0] by ID. It should NOT also match oracle[1] by name.
        # Recall should be 1/2 = 0.5 (only 1 of 2 oracle entities found)
        evaluator = Evaluator()
        loss = evaluator.compute_loss(local_model=local, oracle_model=oracle)
        assert loss.completeness == pytest.approx(0.5)

    def test_evaluator_compute_loss_no_code(self):
        """Without code args, L3 defaults to 0.0."""
        actors = [Actor(id="a1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)]
        local = _make_model(actors=actors)
        oracle = _make_model(actors=actors)

        evaluator = Evaluator()
        loss = evaluator.compute_loss(local_model=local, oracle_model=oracle)

        assert loss.structural_accuracy == 1.0
        assert loss.completeness == 1.0
        assert loss.reconstruction_fidelity == 0.0


# ---------------------------------------------------------------------------
# Pareto front tests
# ---------------------------------------------------------------------------


class TestParetoFront:
    def test_pareto_front_filters_dominated(self):
        """Dominated points are removed from the Pareto front."""
        # Point A dominates point C; B is a trade-off with A
        a = LossVector(
            structural_accuracy=0.9,
            completeness=0.9,
            reconstruction_fidelity=0.9,
            validator_score=90.0,
        )
        b = LossVector(
            structural_accuracy=0.95,
            completeness=0.6,
            reconstruction_fidelity=0.95,
            validator_score=95.0,
        )
        c = LossVector(
            structural_accuracy=0.5,
            completeness=0.5,
            reconstruction_fidelity=0.5,
            validator_score=50.0,
        )

        evaluator = Evaluator()
        front = evaluator.compute_pareto_front([a, b, c])

        # C is dominated by A (A >= C on all, strictly > on all)
        assert c not in front
        # A and B are non-dominated (trade-off)
        assert a in front
        assert b in front
        assert len(front) == 2

    def test_pareto_front_all_non_dominated(self):
        """If no point dominates another, all are on the front."""
        points = [
            LossVector(structural_accuracy=1.0, completeness=0.0, reconstruction_fidelity=0.5, validator_score=50.0),
            LossVector(structural_accuracy=0.0, completeness=1.0, reconstruction_fidelity=0.5, validator_score=50.0),
            LossVector(structural_accuracy=0.5, completeness=0.5, reconstruction_fidelity=1.0, validator_score=50.0),
        ]

        evaluator = Evaluator()
        front = evaluator.compute_pareto_front(points)
        assert len(front) == 3

    def test_pareto_front_single_point(self):
        """Single point is always on the front."""
        p = LossVector(structural_accuracy=0.5, completeness=0.5, reconstruction_fidelity=0.5, validator_score=50.0)
        evaluator = Evaluator()
        front = evaluator.compute_pareto_front([p])
        assert front == [p]

    def test_pareto_front_empty(self):
        """Empty input returns empty front."""
        evaluator = Evaluator()
        front = evaluator.compute_pareto_front([])
        assert front == []
