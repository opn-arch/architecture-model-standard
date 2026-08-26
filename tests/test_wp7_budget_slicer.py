"""WP-7: Budget-aware slicing."""
from architecture_model.core.budget import estimate_tokens, reduce_to_budget
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
    FunctionSignature,
)


class TestTokenEstimation:
    def test_empty_model_small(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(),
            relationships=[],
        )
        tokens = estimate_tokens(model)
        assert tokens < 500

    def test_model_with_signatures_larger(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Big", status=Status.ACTIVE,
                          signatures=[FunctionSignature(name=f"fn_{i}", params=["a", "b"])
                                      for i in range(100)]),
            ]),
            relationships=[],
        )
        tokens = estimate_tokens(model)
        assert tokens > 1000


class TestBudgetReduction:
    def test_reduce_drops_signatures_first(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Big", status=Status.ACTIVE,
                          signatures=[FunctionSignature(name=f"fn_{i}", params=["a", "b"])
                                      for i in range(100)]),
            ]),
            relationships=[],
        )
        reduced = reduce_to_budget(model, max_tokens=500)
        assert estimate_tokens(reduced) <= 500
        assert len(reduced.entities.components[0].signatures) < 100
