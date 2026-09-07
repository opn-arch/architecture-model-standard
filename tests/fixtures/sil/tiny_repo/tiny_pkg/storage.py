"""In-memory store — bottom layer of tiny_pkg."""
from __future__ import annotations


class Store:
    """Trivial key-value store used by ``core``."""

    def __init__(self) -> None:
        self._data: dict[str, int] = {}

    def put(self, key: str, value: int) -> None:
        self._data[key] = value

    def get(self, key: str) -> int | None:
        return self._data.get(key)
