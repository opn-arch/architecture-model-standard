"""SI&L (Self-Improvement & Logging) record schema.

Per-component record used by both architecture components (COMP-* in the
model) and runtime components (pipeline stages, MCP tools, renderers,
validators), distinguished by `kind`.

See docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §4.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
from typing import Any, Optional

import yaml


MAX_EVENTS = 50
VALID_KINDS = frozenset({"architecture-component", "runtime-component"})


@dataclass
class Metrics:
    """Rollup metrics for a component.

    All fields are optional with sensible defaults; runtime-only fields are
    zero for architecture components, and validation/regen fields are ``None``
    when not yet computed.
    """

    validation_score: Optional[int] = None
    drift_flag_count: int = 0
    regen_readiness: Optional[int] = None
    lesson_count: int = 0
    invocations_7d: int = 0
    failure_rate_7d: float = 0.0
    avg_duration_ms: float = 0.0


@dataclass
class Event:
    """Ring-buffer entry for `recent_events`.

    Emitted by the ``@instrumented`` decorator (B2.1.2) on entry/exit.
    """

    ts: str = ""
    kind: str = "invocation"  # invocation | outcome | lesson | drift | validation
    outcome: Optional[str] = None  # ok | error | timeout | skipped | null
    duration_ms: Optional[float] = None
    ref: Optional[str] = None
    event_id: Optional[str] = None


@dataclass
class Rollup:
    """Architecture-component-only rollup pointing at runtime children."""

    runtime_components: list[str] = field(default_factory=list)
    aggregated_at: Optional[str] = None


@dataclass
class SILRecord:
    """One SI&L record per component (architecture or runtime)."""

    component_id: str
    kind: str
    name: str
    metrics: Metrics
    last_touched_revision: Optional[str] = None
    last_touched_at: Optional[str] = None
    events: list[Event] = field(default_factory=list)
    rollup: Optional[Rollup] = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(
                f"invalid kind {self.kind!r}; expected one of {sorted(VALID_KINDS)}"
            )
        # Enforce ring buffer cap on construction.
        if len(self.events) > MAX_EVENTS:
            self.events = self.events[-MAX_EVENTS:]

    def add_event(self, event: Event) -> None:
        """Append an event, trimming to the ring buffer cap (newest last)."""
        self.events.append(event)
        if len(self.events) > MAX_EVENTS:
            del self.events[: len(self.events) - MAX_EVENTS]


# --------------------------------------------------------------------------- #
# YAML helpers                                                                #
# --------------------------------------------------------------------------- #


def _record_to_dict(record: SILRecord) -> dict[str, Any]:
    return asdict(record)


def dump_yaml(record: SILRecord) -> str:
    """Serialize a SILRecord to YAML (lossless round-trip with ``load_yaml``)."""
    return yaml.safe_dump(
        _record_to_dict(record),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )


def _filter_kwargs(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in known}


def load_yaml(text: str) -> SILRecord:
    """Parse a SILRecord YAML document produced by ``dump_yaml``."""
    raw = yaml.safe_load(text) or {}
    if not isinstance(raw, dict):
        raise ValueError("SILRecord YAML must be a mapping")

    metrics_raw = raw.get("metrics") or {}
    metrics = Metrics(**_filter_kwargs(Metrics, metrics_raw))

    events_raw = raw.get("events") or []
    events = [Event(**_filter_kwargs(Event, e or {})) for e in events_raw]

    rollup_raw = raw.get("rollup")
    rollup = Rollup(**_filter_kwargs(Rollup, rollup_raw)) if rollup_raw else None

    return SILRecord(
        component_id=raw["component_id"],
        kind=raw["kind"],
        name=raw["name"],
        metrics=metrics,
        last_touched_revision=raw.get("last_touched_revision"),
        last_touched_at=raw.get("last_touched_at"),
        events=events,
        rollup=rollup,
    )
