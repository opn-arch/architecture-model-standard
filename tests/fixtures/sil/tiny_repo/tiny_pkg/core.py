"""Business logic — the middle layer of tiny_pkg."""
from __future__ import annotations

from tiny_pkg.storage import Store

_STORE = Store()


def compute(value: int, factor: int) -> int:
    """Compute value * factor and persist the result."""
    result = value * factor
    _STORE.put("last", result)
    return result
