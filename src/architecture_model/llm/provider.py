"""LLMProvider Protocol and Completion TypedDict.

See docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §5.
"""
from __future__ import annotations

from typing import Iterator, Literal, Protocol, TypedDict, runtime_checkable


class Completion(TypedDict):
    text: str
    tokens_prompt: int
    tokens_completion: int
    model: str
    finish_reason: Literal["stop", "length", "content_filter", "tool_use"]


@runtime_checkable
class LLMProvider(Protocol):
    """Uniform LLM interface. Adapters live in opencode-arch."""

    name: str

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Completion: ...

    def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Iterator[str]: ...

    def structured(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str | None = None,
    ) -> dict: ...

    def tokenize(self, text: str) -> int: ...
