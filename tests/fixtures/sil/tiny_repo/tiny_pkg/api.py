"""API surface layer for tiny_pkg."""
from __future__ import annotations

from tiny_pkg.core import compute


class Service:
    """Thin service facade exposing the ``handle`` operation."""

    def __init__(self, factor: int = 1) -> None:
        self._factor = factor

    def handle(self, value: int) -> int:
        """Public entrypoint — delegates to ``core.compute``."""
        return compute(value, self._factor)
