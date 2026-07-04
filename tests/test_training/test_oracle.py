"""Tests for Oracle (litellm frontier model client)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
    Actor,
    Component,
    Status,
)
from architecture_model.training.oracle import BudgetTracker, Oracle


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


def _make_simple_model() -> ArchitectureModel:
    """Build a simple ArchitectureModel for validation tests."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(
            actors=[Actor(id="actor-1", name="User", status=Status.ACTIVE)],
            components=[Component(id="comp-1", name="API", status=Status.ACTIVE, layer="web")],
        ),
    )


def _mock_litellm_response(content: str, total_tokens: int = 500) -> MagicMock:
    """Create a mock litellm response object."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage.total_tokens = total_tokens
    return response


# ---------------------------------------------------------------------------
# BudgetTracker Tests
# ---------------------------------------------------------------------------


class TestBudgetTracker:
    def test_init_sets_max_tokens(self):
        """BudgetTracker initializes with max_tokens and zero usage."""
        bt = BudgetTracker(max_tokens=10000)
        assert bt.remaining == 10000

    def test_can_afford_within_budget(self):
        """can_afford returns True when estimated tokens fit within remaining."""
        bt = BudgetTracker(max_tokens=10000)
        assert bt.can_afford(5000) is True

    def test_can_afford_exceeds_budget(self):
        """can_afford returns False when estimated tokens exceed remaining."""
        bt = BudgetTracker(max_tokens=10000)
        bt.record_usage(8000)
        assert bt.can_afford(5000) is False

    def test_can_afford_exact_boundary(self):
        """can_afford returns True when estimated equals remaining exactly."""
        bt = BudgetTracker(max_tokens=10000)
        bt.record_usage(5000)
        assert bt.can_afford(5000) is True

    def test_record_usage_decreases_remaining(self):
        """record_usage subtracts from remaining budget."""
        bt = BudgetTracker(max_tokens=10000)
        bt.record_usage(3000)
        assert bt.remaining == 7000
        bt.record_usage(2000)
        assert bt.remaining == 5000

    def test_remaining_never_negative(self):
        """remaining returns 0 if usage exceeds max (defensive)."""
        bt = BudgetTracker(max_tokens=1000)
        bt.record_usage(1500)
        assert bt.remaining == 0


# ---------------------------------------------------------------------------
# Oracle Init Tests
# ---------------------------------------------------------------------------


class TestOracleInit:
    def test_default_model(self):
        """Oracle defaults to gpt-4o model."""
        oracle = Oracle()
        assert oracle._model == "gpt-4o"

    def test_custom_model(self):
        """Oracle accepts custom model name."""
        oracle = Oracle(model="claude-sonnet-4-20250514")
        assert oracle._model == "claude-sonnet-4-20250514"

    def test_init_with_budget(self):
        """Oracle accepts a BudgetTracker."""
        bt = BudgetTracker(max_tokens=50000)
        oracle = Oracle(budget=bt)
        assert oracle._budget is bt

    def test_init_without_budget(self):
        """Oracle works without a budget (unlimited)."""
        oracle = Oracle()
        assert oracle._budget is None


# ---------------------------------------------------------------------------
# Oracle extract_model Tests
# ---------------------------------------------------------------------------


class TestOracleExtractModel:
    @pytest.mark.asyncio
    async def test_extract_model_sends_correct_messages(self):
        """_completion is called with system + user messages containing code context."""
        oracle = Oracle(model="gpt-4o")
        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response(VALID_MODEL_YAML)
        )

        await oracle.extract_model("def foo(): pass")

        oracle._completion.assert_called_once()
        messages = oracle._completion.call_args[0][0]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "UAM" in messages[0]["content"] or "architecture" in messages[0]["content"]
        assert "def foo(): pass" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_extract_model_parses_valid_yaml(self):
        """Valid YAML response is parsed into ArchitectureModel."""
        oracle = Oracle()
        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response(VALID_MODEL_YAML)
        )

        result = await oracle.extract_model("def foo(): pass")

        assert result is not None
        assert isinstance(result, ArchitectureModel)
        assert result.meta.project == "test-project"
        assert len(result.entities.actors) == 1
        assert len(result.entities.components) == 1
        assert len(result.relationships) == 1

    @pytest.mark.asyncio
    async def test_extract_model_returns_none_on_invalid_yaml(self):
        """Invalid YAML response returns None."""
        oracle = Oracle()
        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response("not: [valid: yaml: {{{", 100)
        )

        result = await oracle.extract_model("def foo(): pass")
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_model_returns_none_on_non_dict(self):
        """YAML that parses to a non-dict returns None."""
        oracle = Oracle()
        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response("- item1\n- item2\n", 50)
        )

        result = await oracle.extract_model("def foo(): pass")
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_model_tracks_budget(self):
        """extract_model records token usage in BudgetTracker."""
        bt = BudgetTracker(max_tokens=10000)
        oracle = Oracle(budget=bt)
        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response(VALID_MODEL_YAML, 750)
        )

        await oracle.extract_model("def foo(): pass")

        assert bt.remaining == 9250

    @pytest.mark.asyncio
    async def test_extract_model_refuses_when_budget_exhausted(self):
        """extract_model returns None when budget cannot afford the call."""
        bt = BudgetTracker(max_tokens=100)
        bt.record_usage(100)  # exhaust budget
        oracle = Oracle(budget=bt)
        oracle._completion = AsyncMock()

        result = await oracle.extract_model("def foo(): pass")

        # Should not call litellm at all
        oracle._completion.assert_not_called()
        assert result is None


# ---------------------------------------------------------------------------
# Oracle validate_extraction Tests
# ---------------------------------------------------------------------------


class TestOracleValidateExtraction:
    @pytest.mark.asyncio
    async def test_validate_extraction_returns_dict(self):
        """validate_extraction returns a dict with feedback."""
        oracle = Oracle()
        model = _make_simple_model()

        validation_response = yaml.dump({
            "valid": True,
            "issues": [],
            "suggestions": ["Consider adding behaviors"],
        })

        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response(validation_response, 300)
        )

        result = await oracle.validate_extraction(model, "def foo(): pass")

        assert isinstance(result, dict)
        assert result["valid"] is True
        assert "suggestions" in result
        assert "Consider adding behaviors" in result["suggestions"]

    @pytest.mark.asyncio
    async def test_validate_extraction_sends_model_and_code(self):
        """validate_extraction includes model YAML and source code in prompt."""
        oracle = Oracle()
        model = _make_simple_model()

        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response(yaml.dump({"valid": True}), 200)
        )

        await oracle.validate_extraction(model, "class MyService: pass")

        messages = oracle._completion.call_args[0][0]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        # User message should contain both model info and the code
        assert "class MyService: pass" in messages[1]["content"]
        assert "actor-1" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_validate_extraction_tracks_budget(self):
        """validate_extraction records token usage."""
        bt = BudgetTracker(max_tokens=10000)
        oracle = Oracle(budget=bt)
        model = _make_simple_model()

        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response(
                yaml.dump({"valid": True, "issues": []}), 400
            )
        )

        await oracle.validate_extraction(model, "def foo(): pass")

        assert bt.remaining == 9600

    @pytest.mark.asyncio
    async def test_validate_extraction_returns_empty_on_parse_failure(self):
        """validate_extraction returns empty dict on unparseable response."""
        oracle = Oracle()
        model = _make_simple_model()

        oracle._completion = AsyncMock(
            return_value=_mock_litellm_response("not: [valid: yaml: {{{", 100)
        )

        result = await oracle.validate_extraction(model, "def foo(): pass")
        assert result == {}

    @pytest.mark.asyncio
    async def test_validate_extraction_refuses_when_budget_exhausted(self):
        """validate_extraction returns empty dict when budget exhausted."""
        bt = BudgetTracker(max_tokens=100)
        bt.record_usage(100)
        oracle = Oracle(budget=bt)
        model = _make_simple_model()
        oracle._completion = AsyncMock()

        result = await oracle.validate_extraction(model, "def foo(): pass")

        oracle._completion.assert_not_called()
        assert result == {}
