"""architecture_model.walks.spec.loader — WalkSpec YAML loader + validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "WalkSpec",
    "ScopeSpec",
    "TraverseSpec",
    "HopSpec",
    "ClassifySpec",
    "VerdictRule",
    "RollupSpec",
    "EvidenceSpec",
    "EmitSpec",
    "load_walk_spec",
    "load_walk_specs_from_dir",
    "WalkSpecError",
]


class WalkSpecError(ValueError):
    """Raised when a WalkSpec YAML fails to parse or validate."""


@dataclass(frozen=True)
class ScopeSpec:
    kind: str
    predicate: str | None = None
    from_walk: str | None = None  # composition: consume prior walk's emit


@dataclass(frozen=True)
class HopSpec:
    """One hop of a multi-hop traversal.

    Hop N is applied to the set of nodes newly-visited in hop N-1 (hop 0
    starts from the scope root). Edges taken are recorded verbatim; no
    induced-subgraph pass runs in hop mode.

    Two dispatch modes:
      - Uniform (default): every frontier node uses ``edges`` + ``direction``.
      - Kind-dispatched: when ``by_kind`` is non-empty, per-node dispatch
        looks up the source node's singular kind (capability, component,
        behavior, interface, actor, constraint) and applies that sub-spec.
        Nodes whose kind is not in the map silent-skip (no outgoing walk
        from them for this hop). ``edges``/``direction`` on the parent
        HopSpec are IGNORED when ``by_kind`` is set.
    """

    edges: tuple[str, ...] = ()
    direction: str = "outbound"  # inbound | outbound | both
    # Kind-dispatched sub-specs. Stored as an ordered tuple of (kind, spec)
    # pairs so the outer HopSpec remains hashable (frozen dataclass).
    by_kind: tuple[tuple[str, "HopSpec"], ...] = ()


@dataclass(frozen=True)
class TraverseSpec:
    edges: tuple[str, ...] = ()
    direction: str = "outbound"  # inbound | outbound | both
    depth: int | None = 1  # None = unbounded
    # Multi-hop mode: when non-empty, edges/direction/depth are ignored and
    # the traversal walks hops[0] from root, hops[1] from hops[0]'s frontier,
    # etc. Used for kind-dispatched walks like realize whose hops apply
    # different edge types in different directions.
    hops: tuple[HopSpec, ...] = ()


@dataclass(frozen=True)
class VerdictRule:
    name: str  # matches Verdict enum values
    when: str  # predicate expression, evaluated by classify stage


@dataclass(frozen=True)
class ClassifySpec:
    verdicts: tuple[VerdictRule, ...]
    on_missing_attributes: str = "needs-enrichment"  # Q4 default


@dataclass(frozen=True)
class RollupSpec:
    via: str = "contains"  # relationship type
    category: str = "C"  # A | B | C — drives strategy default
    strategy: str = "worst-child"  # worst-child | any-child-ok | union | conjunction | contract-composition


@dataclass(frozen=True)
class EvidenceSpec:
    tier: str = "structural"  # structural | behavioral | semantic
    sources: tuple[str, ...] = ("model",)


@dataclass(frozen=True)
class EmitSpec:
    card_template: str = "default"
    severity_from: str = "verdict"
    # When True, emit includes the traverse subgraph (nodes, edges,
    # overflow_count) on each card. Used by diagram-mode walks whose
    # value is the traversed subgraph itself, not a verdict.
    include_subgraph: bool = False
    # Depth-1 → depth-2 cap on visited nodes for diagram-mode walks.
    # None = no cap (traverse.depth still applies).
    subgraph_cap: int | None = None
    # Silent-skip threshold: when set, emit reduces the card's subgraph to
    # only the root node (empty edges) if the number of NON-ROOT visited
    # nodes is 0 or > threshold. Matches _mermaid_neighbors semantics.
    subgraph_neighbor_threshold: int | None = None
    # Silent-skip when the LAST traversal hop added zero new nodes.
    # Matches _mermaid_constraint_impact's "hop 2 identical to 1-hop view"
    # skip. Only meaningful in hop-mode traversal. Ignored otherwise.
    silent_skip_when_last_hop_empty: bool = False


@dataclass(frozen=True)
class WalkSpec:
    """Complete declarative walk specification."""

    id: str
    audits: tuple[str, ...]
    scope: ScopeSpec
    traverse: TraverseSpec = field(default_factory=TraverseSpec)
    classify: ClassifySpec = field(default_factory=lambda: ClassifySpec(verdicts=()))
    rollup: RollupSpec | None = None
    evidence: EvidenceSpec = field(default_factory=EvidenceSpec)
    emit: EmitSpec = field(default_factory=EmitSpec)


def _get(raw: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in raw:
        raise WalkSpecError(f"{ctx}: missing required key '{key}'")
    return raw[key]


def _parse_scope(raw: dict[str, Any]) -> ScopeSpec:
    if not isinstance(raw, dict):
        raise WalkSpecError(f"scope: expected mapping, got {type(raw).__name__}")
    kind = _get(raw, "kind", "scope")
    return ScopeSpec(
        kind=str(kind),
        predicate=raw.get("predicate"),
        from_walk=raw.get("from_walk"),
    )


def _parse_hop(raw: dict[str, Any]) -> HopSpec:
    """Parse one hop entry (uniform or kind-dispatched)."""
    by_kind_raw = raw.get("by_kind") or {}
    by_kind_items: list[tuple[str, HopSpec]] = []
    if by_kind_raw:
        if not isinstance(by_kind_raw, dict):
            raise WalkSpecError(
                f"traverse.hops[].by_kind: expected mapping, "
                f"got {type(by_kind_raw).__name__}"
            )
        for k in sorted(by_kind_raw.keys()):
            sub = by_kind_raw[k]
            if not isinstance(sub, dict):
                raise WalkSpecError(
                    f"traverse.hops[].by_kind[{k!r}]: expected mapping"
                )
            # Nested by_kind is not supported (would need multi-level
            # dispatch semantics we don't have). Enforce single-level.
            if sub.get("by_kind"):
                raise WalkSpecError(
                    f"traverse.hops[].by_kind[{k!r}]: nested by_kind not supported"
                )
            by_kind_items.append(
                (
                    str(k),
                    HopSpec(
                        edges=tuple(sub.get("edges", ())),
                        direction=sub.get("direction", "outbound"),
                    ),
                )
            )
    return HopSpec(
        edges=tuple(raw.get("edges", ())),
        direction=raw.get("direction", "outbound"),
        by_kind=tuple(by_kind_items),
    )


def _parse_traverse(raw: dict[str, Any] | None) -> TraverseSpec:
    if raw is None:
        return TraverseSpec()
    hops_raw = raw.get("hops")
    if hops_raw:
        hops = tuple(_parse_hop(h) for h in hops_raw)
        # In hop mode, edges/direction/depth are unused but preserved as
        # defaults for consumers that inspect them.
        return TraverseSpec(hops=hops)
    edges = tuple(raw.get("edges", ()))
    direction = raw.get("direction", "outbound")
    depth_raw = raw.get("depth", 1)
    depth = None if depth_raw in ("unbounded", None) else int(depth_raw)
    return TraverseSpec(edges=edges, direction=direction, depth=depth)


def _parse_classify(raw: dict[str, Any] | None) -> ClassifySpec:
    if raw is None:
        return ClassifySpec(verdicts=())
    verdicts_raw = raw.get("verdicts", [])
    verdicts = tuple(
        VerdictRule(name=str(v["name"]), when=str(v.get("when", "true")))
        for v in verdicts_raw
    )
    return ClassifySpec(
        verdicts=verdicts,
        on_missing_attributes=raw.get("on_missing_attributes", "needs-enrichment"),
    )


def _parse_rollup(raw: dict[str, Any] | None) -> RollupSpec | None:
    if raw is None:
        return None
    return RollupSpec(
        via=raw.get("via", "contains"),
        category=raw.get("category", "C"),
        strategy=raw.get("strategy", "worst-child"),
    )


def _parse_evidence(raw: dict[str, Any] | None) -> EvidenceSpec:
    if raw is None:
        return EvidenceSpec()
    return EvidenceSpec(
        tier=raw.get("tier", "structural"),
        sources=tuple(raw.get("sources", ["model"])),
    )


def _parse_emit(raw: dict[str, Any] | None) -> EmitSpec:
    if raw is None:
        return EmitSpec()
    cap_raw = raw.get("subgraph_cap")
    cap = None if cap_raw is None else int(cap_raw)
    thr_raw = raw.get("subgraph_neighbor_threshold")
    thr = None if thr_raw is None else int(thr_raw)
    return EmitSpec(
        card_template=raw.get("card_template", "default"),
        severity_from=raw.get("severity_from", "verdict"),
        include_subgraph=bool(raw.get("include_subgraph", False)),
        subgraph_cap=cap,
        subgraph_neighbor_threshold=thr,
        silent_skip_when_last_hop_empty=bool(
            raw.get("silent_skip_when_last_hop_empty", False)
        ),
    )


def _parse_audits(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    return tuple(str(a) for a in raw)


def parse_walk_spec(raw: dict[str, Any]) -> WalkSpec:
    """Parse a raw dict into a WalkSpec. Raises WalkSpecError on failure."""
    if not isinstance(raw, dict):
        raise WalkSpecError(f"top-level: expected mapping, got {type(raw).__name__}")
    walk_raw = raw.get("walk", raw)
    if not isinstance(walk_raw, dict):
        raise WalkSpecError("walk: expected mapping under 'walk' key or root")

    wid = _get(walk_raw, "id", "walk")
    if not isinstance(wid, str) or not wid.startswith("WALK-"):
        raise WalkSpecError(f"walk.id must be a string starting with 'WALK-'; got {wid!r}")

    return WalkSpec(
        id=wid,
        audits=_parse_audits(walk_raw.get("audits")),
        scope=_parse_scope(_get(walk_raw, "scope", "walk")),
        traverse=_parse_traverse(walk_raw.get("traverse")),
        classify=_parse_classify(walk_raw.get("classify")),
        rollup=_parse_rollup(walk_raw.get("rollup")),
        evidence=_parse_evidence(walk_raw.get("evidence")),
        emit=_parse_emit(walk_raw.get("emit")),
    )


def load_walk_spec(path: Path) -> WalkSpec:
    """Load and parse a single WalkSpec YAML file."""
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    try:
        return parse_walk_spec(raw)
    except WalkSpecError as e:
        raise WalkSpecError(f"{path}: {e}") from e


def load_walk_specs_from_dir(directory: Path) -> list[WalkSpec]:
    """Load all *.v3.yaml WalkSpec files under a directory, sorted by id.

    Performs cycle detection on ``scope.from_walk`` composition edges.
    """
    specs: list[WalkSpec] = []
    for yaml_path in sorted(directory.glob("*.v3.yaml")):
        specs.append(load_walk_spec(yaml_path))
    _check_composition_cycles(specs)
    return specs


def _check_composition_cycles(specs: list[WalkSpec]) -> None:
    """Detect cycles in scope.from_walk composition edges."""
    by_id = {s.id: s for s in specs}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(sid: str, path: tuple[str, ...]) -> None:
        if sid in visiting:
            raise WalkSpecError(
                f"composition cycle detected: {' -> '.join(path + (sid,))}"
            )
        if sid in visited:
            return
        visiting.add(sid)
        spec = by_id.get(sid)
        if spec is not None and spec.scope.from_walk:
            visit(spec.scope.from_walk, path + (sid,))
        visiting.remove(sid)
        visited.add(sid)

    for spec in specs:
        visit(spec.id, ())
