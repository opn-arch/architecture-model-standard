"""Tests for iterative model refinement."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from architecture_model.training.refiner import ModelRefiner
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Actor, Status,
    Component, Layer, Relationship, RelationType,
)


def _make_model(actors=None, components=None, layers=None, relationships=None):
    """Build a minimal model."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(
            actors=actors or [],
            components=components or [],
            layers=layers or [],
        ),
        relationships=relationships or [],
    )


@pytest.fixture
def mock_client():
    client = MagicMock()
    client._chat = AsyncMock()
    return client


class TestModelRefiner:
    def test_init(self, mock_client):
        """Accepts client and max_rounds."""
        refiner = ModelRefiner(mock_client, max_rounds=3)
        assert refiner._max_rounds == 3

    @pytest.mark.asyncio
    async def test_no_refinement_needed_for_high_score(self, mock_client):
        """Model with score >= 95 is returned immediately without LLM calls."""
        model = _make_model(
            actors=[Actor(id="A1", name="User", status=Status.ACTIVE)],
            components=[Component(id="C1", name="API", status=Status.ACTIVE, layer="L1")],
            layers=[Layer(id="L1", name="Web", status=Status.ACTIVE)],
            relationships=[
                Relationship(type=RelationType.CONTAINS, from_id="L1", to_id="C1"),
            ],
        )
        refiner = ModelRefiner(mock_client, max_rounds=3)
        result = await refiner.refine(model, "some code context")
        # Should not call client since score is already high
        mock_client._chat.assert_not_called()
        assert result is model or result.entity_count >= model.entity_count

    @pytest.mark.asyncio
    async def test_refines_model_with_low_score(self, mock_client):
        """Model with dangling references gets refined."""
        # Dangling references → warnings → low score
        model = _make_model(
            components=[
                Component(id="C1", name="API", status=Status.ACTIVE, layer="L1"),
                Component(id="C2", name="DB", status=Status.ACTIVE, layer="L2"),
            ],
            relationships=[
                # 3 dangling refs = 6 warnings = score 88
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="NONEXIST1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C2", to_id="NONEXIST2"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="NONEXIST3", to_id="C1"),
            ],
        )
        # Mock the refinement response — add the missing entities
        mock_client._chat.return_value = {"message": {"content": (
            "layers:\n"
            "  - id: L1\n    name: Web\n    status: ACTIVE\n"
            "  - id: L2\n    name: Data\n    status: ACTIVE\n"
            "components:\n"
            "  - id: NONEXIST1\n    name: Cache\n    status: ACTIVE\n    layer: L1\n"
            "  - id: NONEXIST2\n    name: Queue\n    status: ACTIVE\n    layer: L2\n"
            "  - id: NONEXIST3\n    name: Gateway\n    status: ACTIVE\n    layer: L1"
        )}}
        refiner = ModelRefiner(mock_client, max_rounds=3)
        result = await refiner.refine(model, "some code")
        # Should have called client at least once
        assert mock_client._chat.called
        # Result should have more entities
        assert result.entity_count > model.entity_count

    @pytest.mark.asyncio
    async def test_respects_max_rounds(self, mock_client):
        """Stops after max_rounds even if score hasn't improved."""
        # Create model with dangling refs to ensure score < 95
        model = _make_model(
            components=[Component(id="C1", name="API", status=Status.ACTIVE, layer="L1")],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="BAD1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="BAD2"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="BAD3"),
            ],
        )
        # Always return empty (won't improve score)
        mock_client._chat.return_value = {"message": {"content": "relationships: []"}}
        refiner = ModelRefiner(mock_client, max_rounds=2)
        await refiner.refine(model, "code")
        # Should have called at most max_rounds times
        assert mock_client._chat.call_count <= 2

    @pytest.mark.asyncio
    async def test_feedback_includes_validator_issues(self, mock_client):
        """The refinement prompt includes specific validator issues."""
        # Dangling refs create DANGLING_REF warnings that appear in prompt
        model = _make_model(
            components=[Component(id="C1", name="Orphan", status=Status.ACTIVE, layer="X")],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="MISSING1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="MISSING2"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="MISSING3"),
            ],
        )
        mock_client._chat.return_value = {"message": {"content": "relationships: []"}}
        refiner = ModelRefiner(mock_client, max_rounds=1)
        await refiner.refine(model, "code")
        # Check the prompt sent includes issue information
        call_args = mock_client._chat.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "DANGLING_REF" in user_msg or "MISSING" in user_msg or "unknown entity" in user_msg

    @pytest.mark.asyncio
    async def test_stops_when_score_improves_above_threshold(self, mock_client):
        """Stops early if score reaches threshold."""
        # Start with model that has dangling refs (warnings → score < 95)
        model = _make_model(
            components=[Component(id="C1", name="API", status=Status.ACTIVE, layer="L1")],
            layers=[Layer(id="L1", name="Web", status=Status.ACTIVE)],
            relationships=[
                Relationship(type=RelationType.CONTAINS, from_id="L1", to_id="C1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="MISSING1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="MISSING2"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="MISSING3"),
            ],
        )
        # Return a fix that adds the missing entities
        mock_client._chat.return_value = {"message": {"content": (
            "components:\n"
            "  - id: MISSING1\n    name: Svc1\n    status: ACTIVE\n    layer: L1\n"
            "  - id: MISSING2\n    name: Svc2\n    status: ACTIVE\n    layer: L1\n"
            "  - id: MISSING3\n    name: Svc3\n    status: ACTIVE\n    layer: L1"
        )}}
        refiner = ModelRefiner(mock_client, max_rounds=5)
        result = await refiner.refine(model, "code")
        # Should stop before max_rounds since score improved
        assert mock_client._chat.call_count <= 3
