"""Tests for Surrogate (Ollama client wrapper)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import yaml

from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
)
from architecture_model.training.surrogate import Surrogate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_MODEL_YAML = yaml.dump(
    {
        "meta": {
            "schema_version": "1.0",
            "project": "test-project",
        },
        "entities": {
            "actors": [
                {"id": "actor-1", "name": "User", "status": "ACTIVE", "type": "human"}
            ],
            "components": [
                {"id": "comp-1", "name": "API", "status": "ACTIVE", "layer": "web"}
            ],
        },
        "relationships": [
            {"type": "depends-on", "from": "comp-1", "to": "actor-1"}
        ],
    }
)


def _make_model_with_n_entities(n: int, n_rels: int = 0) -> ArchitectureModel:
    """Build an ArchitectureModel with n actors and n_rels relationships."""
    from architecture_model.core.types import Actor, Relationship, RelationType, Status

    actors = [
        Actor(id=f"actor-{i}", name=f"Actor {i}", status=Status.ACTIVE)
        for i in range(n)
    ]
    relationships = [
        Relationship(
            type=RelationType.DEPENDS_ON,
            from_id=f"actor-{i % n}" if n > 0 else "actor-0",
            to_id=f"actor-{(i + 1) % n}" if n > 1 else "actor-0",
        )
        for i in range(n_rels)
    ]
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(actors=actors),
        relationships=relationships,
    )


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestSurrogateInit:
    def test_surrogate_init(self):
        """Default model name and host are set correctly."""
        s = Surrogate()
        assert s.model_name == "qwen2.5:7b"
        assert s._host == "http://localhost:11434"

    def test_surrogate_init_custom(self):
        """Custom model name and host are used."""
        s = Surrogate(model_name="mistral:7b", host="http://myhost:1234")
        assert s.model_name == "mistral:7b"
        assert s._host == "http://myhost:1234"


# ---------------------------------------------------------------------------
# swap_model Tests
# ---------------------------------------------------------------------------


class TestSwapModel:
    def test_swap_model(self):
        """swap_model updates model_name."""
        s = Surrogate()
        assert s.model_name == "qwen2.5:7b"
        s.swap_model("llama2:7b")
        assert s.model_name == "llama2:7b"


# ---------------------------------------------------------------------------
# extract_model Tests
# ---------------------------------------------------------------------------


class TestExtractModel:
    @pytest.mark.asyncio
    async def test_extract_model_sends_prompt(self):
        """_chat is called with system + user messages containing code context."""
        s = Surrogate()
        # Mock _chat to return valid YAML
        s._chat = AsyncMock(
            return_value={"message": {"content": VALID_MODEL_YAML}}
        )

        await s.extract_model("def foo(): pass")

        s._chat.assert_called_once()
        messages = s._chat.call_args[0][0]
        # Should have system and user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        # System prompt should mention UAM schema or architecture
        assert "UAM" in messages[0]["content"] or "architecture" in messages[0]["content"]
        # User message should contain the code context
        assert "def foo(): pass" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_extract_model_parses_valid_yaml(self):
        """Valid YAML response is parsed into an ArchitectureModel."""
        s = Surrogate()
        s._chat = AsyncMock(
            return_value={"message": {"content": VALID_MODEL_YAML}}
        )

        result = await s.extract_model("def foo(): pass")

        assert result is not None
        assert isinstance(result, ArchitectureModel)
        assert result.meta.project == "test-project"
        assert len(result.entities.actors) == 1
        assert len(result.entities.components) == 1
        assert len(result.relationships) == 1

    @pytest.mark.asyncio
    async def test_extract_model_handles_invalid_yaml(self):
        """Garbage response returns None."""
        s = Surrogate()
        s._chat = AsyncMock(
            return_value={"message": {"content": "not: [valid: yaml: {{{"}}
        )

        result = await s.extract_model("def foo(): pass")
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_model_handles_non_dict_yaml(self):
        """YAML that parses to a non-dict (e.g. a list) returns None."""
        s = Surrogate()
        s._chat = AsyncMock(
            return_value={"message": {"content": "- item1\n- item2\n"}}
        )

        result = await s.extract_model("def foo(): pass")
        assert result is None


# ---------------------------------------------------------------------------
# generate_code Tests
# ---------------------------------------------------------------------------


class TestGenerateCode:
    @pytest.mark.asyncio
    async def test_generate_code_returns_string(self):
        """generate_code returns the LLM's text response."""
        s = Surrogate()
        s._chat = AsyncMock(
            return_value={"message": {"content": "def hello(): print('hi')"}}
        )

        result = await s.generate_code("components:\n  - id: comp-1")

        assert result == "def hello(): print('hi')"
        s._chat.assert_called_once()


# ---------------------------------------------------------------------------
# confidence Tests
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_confidence_empty_model(self):
        """Model with 0 entities yields confidence 0.0."""
        s = Surrogate()
        model = _make_model_with_n_entities(0)
        assert s.confidence(model) == 0.0

    def test_confidence_entities_only_no_relationships(self):
        """10 entities but 0 relationships — penalized by rel_density.

        entity_density = min(1.0, 10/10) = 1.0
        expected_rels = 10 * 1.5 + 1 = 16
        rel_density = min(1.0, 0/16) = 0.0
        confidence = 0.6 * 1.0 + 0.4 * 0.0 = 0.6
        """
        s = Surrogate()
        model = _make_model_with_n_entities(10, n_rels=0)
        assert s.confidence(model) == pytest.approx(0.6)

    def test_confidence_well_connected_model(self):
        """10 entities, 15 relationships — should be ~1.0.

        entity_density = 1.0
        expected_rels = 10 * 1.5 + 1 = 16
        rel_density = min(1.0, 15/16) = 0.9375
        confidence = 0.6 * 1.0 + 0.4 * 0.9375 = 0.975
        """
        s = Surrogate()
        model = _make_model_with_n_entities(10, n_rels=15)
        assert s.confidence(model) == pytest.approx(0.975)

    def test_confidence_saturated_relationships(self):
        """10 entities, 20 relationships — rel_density caps at 1.0.

        entity_density = 1.0
        expected_rels = 16
        rel_density = min(1.0, 20/16) = 1.0
        confidence = 0.6 * 1.0 + 0.4 * 1.0 = 1.0
        """
        s = Surrogate()
        model = _make_model_with_n_entities(10, n_rels=20)
        assert s.confidence(model) == pytest.approx(1.0)

    def test_confidence_partial_model(self):
        """5 entities, 3 relationships — medium confidence.

        entity_density = min(1.0, 5/10) = 0.5
        expected_rels = 5 * 1.5 + 1 = 8.5
        rel_density = min(1.0, 3/8.5) ≈ 0.3529
        confidence = 0.6 * 0.5 + 0.4 * 0.3529 ≈ 0.4412
        """
        s = Surrogate()
        model = _make_model_with_n_entities(5, n_rels=3)
        expected = 0.6 * 0.5 + 0.4 * (3 / 8.5)
        assert s.confidence(model) == pytest.approx(expected)

    def test_confidence_with_coverage_score(self):
        """With coverage_score, uses 3-way weighted average.

        entity_density = 1.0 (10 entities)
        expected_rels = 16, rel_density = 15/16 = 0.9375
        confidence = 0.4 * 1.0 + 0.3 * 0.9375 + 0.3 * 0.8 = 0.92125
        """
        s = Surrogate()
        model = _make_model_with_n_entities(10, n_rels=15)
        result = s.confidence(model, coverage_score=0.8)
        expected = 0.4 * 1.0 + 0.3 * (15 / 16) + 0.3 * 0.8
        assert result == pytest.approx(expected)

    def test_confidence_coverage_score_none_uses_two_signal(self):
        """Passing coverage_score=None explicitly uses 2-signal formula."""
        s = Surrogate()
        model = _make_model_with_n_entities(10, n_rels=15)
        result_none = s.confidence(model, coverage_score=None)
        result_default = s.confidence(model)
        assert result_none == result_default
