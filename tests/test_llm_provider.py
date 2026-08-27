"""Tests for LLM provider auto-detection."""
import pytest
from unittest.mock import AsyncMock, patch
from architecture_model.pipeline.llm_provider import (
    create_llm_callback,
    copilot_relay_callback,
    LLMProvider,
    detect_provider,
)


class TestCreateLLMCallback:
    def test_returns_none_when_nothing_available(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
                cb = create_llm_callback()
                assert cb is None

    def test_prefers_copilot_relay(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=True):
            cb = create_llm_callback()
            assert cb is not None

    def test_falls_back_to_openai(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
                cb = create_llm_callback()
                assert cb is not None

    def test_falls_back_to_anthropic(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
                cb = create_llm_callback()
                assert cb is not None


class TestDetectProvider:
    def test_detects_copilot_relay(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=True):
            assert detect_provider() == LLMProvider.COPILOT_RELAY

    def test_detects_none(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
            with patch.dict("os.environ", {}, clear=True):
                assert detect_provider() == LLMProvider.NONE


class TestCopilotRelayCallback:
    @pytest.mark.asyncio
    async def test_callback_signature(self):
        with patch("architecture_model.pipeline.llm_provider._call_copilot_relay", new_callable=AsyncMock) as mock:
            mock.return_value = "response text"
            result = await copilot_relay_callback("observe", "review this", {})
            assert result == "response text"
            mock.assert_called_once()
