"""ArtifactSpec dependency DAG + rebuild plan generator.

Purpose
-------
Given a collection of :class:`ArtifactSpec` objects, build a directed
acyclic graph over their bundle references and emit a topologically
ordered :class:`RebuildPlan` naming which artifacts must be rebuilt.

Design
------
The DAG is *artifact-centric*: nodes are ArtifactSpecs and edges point
from each entry in a zip artifact's ``bundle_refs`` to the zip itself
(upstream leaf artifacts must be built before the zip that aggregates
them). Non-zip artifacts contribute nodes with no outgoing edges (their
view/slice/model upstream chain is already modeled by
:mod:`architecture_model.lifecycle.stale` and is exposed here only as
``BuildStep.view_ref`` metadata).

We deliberately do **not** reuse
:class:`architecture_model.lifecycle.stale.DependencyGraph`. That graph
carries ``owned_paths`` / ``inputs`` semantics tuned for path-based
invalidation across the full lifecycle graph (packages, models,
manifests, slices, views, artifacts). Here we need only artifact-to-
artifact edges with cycle + missing-ref checks, so a small local DAG is
clearer and avoids overloading upstream node ids.

Execution
---------
This module is planning-only. No artifact bytes are produced; execution
is Phase 2.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef

if TYPE_CHECKING:  # pragma: no cover
    from architecture_model.lifecycle.stale import StaleSet


class ArtifactDAGError(Exception):
    """Base class for artifact DAG construction errors."""


class ArtifactDAGCycle(ArtifactDAGError):
    """Raised when the artifact DAG contains a directed cycle."""


class MissingArtifactRef(ArtifactDAGError):
    """Raised when a ``bundle_refs`` entry points at an unknown artifact id."""


@dataclass(frozen=True)
class BuildStep:
    """One planned build in a :class:`RebuildPlan`."""

    artifact_id: str
    kind: str
    inputs: tuple[str, ...]
    view_ref: ViewRef | None
    bundle_refs: tuple[str, ...]
    output_path: str


@dataclass(frozen=True)
class RebuildPlan:
    """Ordered plan of :class:`BuildStep` instances to execute (later)."""

    steps: tuple[BuildStep, ...]
    skipped_up_to_date: tuple[str, ...]
    warnings: tuple[str, ...] = ()


_EXT: dict[str, str] = {
    "svg": "svg",
    "markdown": "md",
    "html": "html",
    "ai-context": "txt",
    "zip": "zip",
}


class ArtifactDAG:
    """Small artifact-centric DAG. Nodes are artifact ids."""

    def __init__(self) -> None:
        self._artifacts: dict[str, ArtifactSpec] = {}
        self._out: dict[str, set[str]] = {}
        self._in: dict[str, set[str]] = {}

    def add(self, artifact: ArtifactSpec) -> None:
        self._artifacts[artifact.id] = artifact
        self._out.setdefault(artifact.id, set())
        self._in.setdefault(artifact.id, set())

    def add_edge(self, upstream: str, downstream: str) -> None:
        self._out[upstream].add(downstream)
        self._in[downstream].add(upstream)

    def artifacts(self) -> list[ArtifactSpec]:
        return [self._artifacts[k] for k in sorted(self._artifacts)]

    def get(self, artifact_id: str) -> ArtifactSpec:
        return self._artifacts[artifact_id]

    def topological_order(self) -> list[str]:
        """Deterministic Kahn's algorithm; sorted ties by id."""
        indeg = {n: len(self._in[n]) for n in self._artifacts}
        ready = sorted(n for n, d in indeg.items() if d == 0)
        result: list[str] = []
        while ready:
            cur = ready.pop(0)
            result.append(cur)
            for nxt in sorted(self._out[cur]):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    ready.append(nxt)
            ready.sort()
        if len(result) != len(self._artifacts):
            missing = sorted(set(self._artifacts) - set(result))
            raise ArtifactDAGCycle(
                f"cycle detected among artifacts: {missing!r}"
            )
        return result


def build_artifact_dag(artifacts: Iterable[ArtifactSpec]) -> ArtifactDAG:
    """Build an :class:`ArtifactDAG` from ``artifacts``.

    Adds an edge from each ``bundle_refs`` entry (upstream) to the zip
    artifact that names it (downstream). Raises
    :class:`MissingArtifactRef` if a bundle_ref points at an unknown
    artifact id, and :class:`ArtifactDAGCycle` if the resulting graph
    contains a directed cycle.
    """
    dag = ArtifactDAG()
    specs = list(artifacts)
    for a in specs:
        dag.add(a)
    known = {a.id for a in specs}
    for a in specs:
        if a.renderer != "zip":
            continue
        for ref in a.bundle_refs or ():
            if ref not in known:
                raise MissingArtifactRef(
                    f"artifact {a.id!r} bundle_refs entry {ref!r} is unknown"
                )
            dag.add_edge(ref, a.id)
    # Force cycle check now so callers get errors up-front.
    dag.topological_order()
    return dag


def _output_path(output_dir: str, artifact_id: str, renderer: str) -> str:
    return f"{output_dir}/{artifact_id}.{_EXT[renderer]}"


def _make_step(a: ArtifactSpec, output_dir: str) -> BuildStep:
    if a.renderer == "zip":
        bundle = tuple(a.bundle_refs or ())
        inputs = tuple(sorted(bundle))
        return BuildStep(
            artifact_id=a.id,
            kind="zip",
            inputs=inputs,
            view_ref=None,
            bundle_refs=bundle,
            output_path=_output_path(output_dir, a.id, "zip"),
        )
    return BuildStep(
        artifact_id=a.id,
        kind=a.renderer,
        inputs=(),
        view_ref=a.view_ref,
        bundle_refs=(),
        output_path=_output_path(output_dir, a.id, a.renderer),
    )


def rebuild_plan(
    artifacts: Iterable[ArtifactSpec],
    *,
    stale: "StaleSet | None" = None,
    output_dir: str = "artifacts",
) -> RebuildPlan:
    """Compute a topologically ordered :class:`RebuildPlan`.

    * ``stale=None`` → every artifact receives a :class:`BuildStep`
      (full rebuild).
    * ``stale`` provided → only artifacts whose id ``a.id`` satisfies
      ``f"artifact:{a.id}" in stale.nodes`` receive a BuildStep. Others
      go into :attr:`RebuildPlan.skipped_up_to_date`. The T11 stale
      propagator already includes descendants, so no re-propagation
      happens here.

    Execution is out of scope: this task only plans. Callers execute
    steps in Phase 2.
    """
    specs = list(artifacts)
    dag = build_artifact_dag(specs)
    order = dag.topological_order()
    by_id = {a.id: a for a in specs}

    steps: list[BuildStep] = []
    skipped: list[str] = []
    for aid in order:
        spec = by_id[aid]
        if stale is not None and f"artifact:{aid}" not in stale.nodes:
            skipped.append(aid)
            continue
        steps.append(_make_step(spec, output_dir))

    return RebuildPlan(
        steps=tuple(steps),
        skipped_up_to_date=tuple(skipped),
    )


__all__ = [
    "ArtifactDAG",
    "ArtifactDAGCycle",
    "ArtifactDAGError",
    "BuildStep",
    "MissingArtifactRef",
    "RebuildPlan",
    "build_artifact_dag",
    "rebuild_plan",
]
