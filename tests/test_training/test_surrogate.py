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


def _make_model_with_n_entities(n: int) -> ArchitectureModel:
    """Build an ArchitectureModel with exactly n actors (simplest entity)."""
    from architecture_model.core.types import Actor, Status

    actors = [
        Actor(id=f"actor-{i}", name=f"Actor {i}", status=Status.ACTIVE)
        for i in range(n)
    ]
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(actors=actors),
    )


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestSurrogateInit:
    def test_surrogate_init(self):
        """Default model name and host are set correctly."""
        s = Surrogate()
        assert s.model_name == "codellama:13b"
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
        assert s.model_name == "codellama:13b"
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

    def test_confidence_full_model(self):
        """Model with 10+ entities yields confidence 1.0 (capped)."""
        s = Surrogate()
        model = _make_model_with_n_entities(15)
        assert s.confidence(model) == 1.0

    def test_confidence_partial(self):
        """Model with 5 entities yields confidence 0.5."""
        s = Surrogate()
        model = _make_model_with_n_entities(5)
        assert s.confidence(model) == 0.5
