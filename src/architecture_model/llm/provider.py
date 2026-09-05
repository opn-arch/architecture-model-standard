"""LLMProvider Protocol and Completion TypedDict."""
from typing import Protocol, TypedDict


class Completion(TypedDict):
    text: str


class LLMProvider(Protocol):
    name: str
