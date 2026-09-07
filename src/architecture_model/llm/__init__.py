"""LLM Provider protocol — see docs/plans/2026-09-05-...-shared-interfaces-design.md §5."""

from architecture_model.llm.provider import Completion, LLMProvider

__all__ = ["Completion", "LLMProvider"]
