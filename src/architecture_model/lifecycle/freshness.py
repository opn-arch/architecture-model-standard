"""Freshness constants for artifact provenance.

A projected view / rendered artifact is:
- ``"fresh"`` — was produced from the current model revision.
- ``"stale"`` — was produced from an earlier revision and needs rebuild.
- ``"pending"`` — scheduled for rebuild but not yet produced.

The `project()` function stamps `"fresh"` on outputs unconditionally at
production time. Downstream invalidation (SemanticDiff → stale_families)
flips the stored marker to `"stale"`; scheduling flips it to `"pending"`.
"""
from __future__ import annotations

from typing import Literal

Freshness = Literal["fresh", "stale", "pending"]
FRESHNESS_VALUES: tuple[Freshness, ...] = ("fresh", "stale", "pending")
