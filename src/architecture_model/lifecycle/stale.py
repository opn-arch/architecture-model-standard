"""Semantic-intersection stale graph for the architecture lifecycle.

Purpose
-------
Build a directed acyclic graph (DAG) over lifecycle-object kinds
(``package``, ``model``, ``manifest``, ``slice``, ``view``, ``artifact``) and
compute the set of nodes that become stale when a given set of source paths
changes. The graph is planning-only — nothing is executed or rebuilt.

Semantic intersection
---------------------
Each node declares ``owned_paths`` — POSIX-style ``fnmatch`` glob patterns
relative to the package root. A node is *directly* invalidated only when a
changed path matches one of its own globs. Direct invalidation then
propagates to all transitive descendants. A slice with
``owned_paths=("core/**",)`` is *not* invalidated by changes under
``cli/`` — this is what makes the graph "semantic".

Nodes with an empty ``owned_paths`` tuple (and any kind other than
``package``) are never invalidated by paths; they only become stale through
an upstream input. This lets synthetic view/artifact nodes participate in
propagation without pretending to own any code.

Invariants
----------
* Node kind is a lowercase string from ``NODE_KINDS``. It is a soft enum so
  later tasks (T13–T18) can add ``slice``, ``view`` and ``artifact`` nodes
  without modifying this module.
* All returned collections (topological orders, stale-node lists, reason
  dicts) are deterministic — internal iteration is over sorted node ids.
* Cycle detection is performed by :meth:`DependencyGraph.topological_order`
  and raises :class:`CycleError`.
* :func:`stale_report` never raises on a missing cache; a corrupt cache is
  silently discarded and regenerated.

Thread-safety
-------------
Not thread-safe. Callers must serialize concurrent access to a single
graph instance and to ``.architecture/stale.yaml``.

Error taxonomy
--------------
* :class:`CycleError` — raised on cycle detection.
* :class:`KeyError` — raised by :meth:`DependencyGraph.add_edge` on unknown
  node ids.
* Package-loader errors from :mod:`architecture_model.lifecycle.package`
  propagate unchanged.
"""
from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from architecture_model.lifecycle.atomic_store import write_atomic
from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    iter_descendants,
)
from architecture_model.lifecycle.serialization import canonical_json


NODE_KINDS: frozenset[str] = frozenset(
    {"package", "model", "manifest", "slice", "view", "artifact"}
)


class CycleError(Exception):
    """Raised when the dependency graph contains a directed cycle."""


@dataclass(frozen=True)
class StaleNode:
    """One node in the lifecycle dependency graph.

    ``owned_paths`` are POSIX-style ``fnmatch`` globs interpreted relative
    to the package root. An empty tuple means the node owns no code — such
    nodes can only be transitively invalidated via ``inputs``.
    """

    node_id: str
    kind: str
    owned_paths: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    digest: str | None = None


@dataclass(frozen=True)
class StaleSet:
    """The result of :func:`mark_stale`: which nodes are stale, and why."""

    nodes: frozenset[str]
    reasons: dict[str, str] = field(default_factory=dict)


class DependencyGraph:
    """Mutable DAG of :class:`StaleNode` instances.

    Edges are added via :meth:`add_edge` and point from *upstream* to
    *downstream*. ``descendants(x)`` returns the transitive set of nodes
    that depend on ``x``; ``ancestors(x)`` returns the transitive set of
    nodes ``x`` depends on.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, StaleNode] = {}
        # upstream -> set of downstream ids
        self._out: dict[str, set[str]] = {}
        # downstream -> set of upstream ids
        self._in: dict[str, set[str]] = {}

    # ---- construction ---------------------------------------------------

    def add_node(self, node: StaleNode) -> None:
        """Insert or replace a node. Idempotent by ``node_id``."""
        self._nodes[node.node_id] = node
        self._out.setdefault(node.node_id, set())
        self._in.setdefault(node.node_id, set())

    def add_edge(self, upstream_id: str, downstream_id: str) -> None:
        """Add an edge ``upstream_id -> downstream_id``.

        Raises :class:`KeyError` if either endpoint is unknown.
        """
        if upstream_id not in self._nodes:
            raise KeyError(f"unknown upstream node {upstream_id!r}")
        if downstream_id not in self._nodes:
            raise KeyError(f"unknown downstream node {downstream_id!r}")
        self._out[upstream_id].add(downstream_id)
        self._in[downstream_id].add(upstream_id)

    # ---- inspection -----------------------------------------------------

    def nodes(self) -> list[StaleNode]:
        """All nodes, sorted by ``node_id``."""
        return [self._nodes[k] for k in sorted(self._nodes)]

    def get(self, node_id: str) -> StaleNode:
        return self._nodes[node_id]

    def descendants(self, node_id: str) -> set[str]:
        """Transitive downstream nodes, excluding ``node_id`` itself."""
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for nxt in self._out.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    def ancestors(self, node_id: str) -> set[str]:
        """Transitive upstream nodes, excluding ``node_id`` itself."""
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for prev in self._in.get(cur, ()):
                if prev not in seen:
                    seen.add(prev)
                    stack.append(prev)
        return seen

    def topological_order(self) -> list[str]:
        """Return a deterministic topological order of node ids.

        Ties are broken by ``node_id`` lexical order. Raises
        :class:`CycleError` if the graph is cyclic.
        """
        indeg: dict[str, int] = {n: len(self._in[n]) for n in self._nodes}
        ready = sorted(n for n, d in indeg.items() if d == 0)
        result: list[str] = []
        while ready:
            cur = ready.pop(0)
            result.append(cur)
            new_ready: list[str] = []
            for nxt in sorted(self._out[cur]):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    new_ready.append(nxt)
            # Merge and keep sorted
            ready = sorted(ready + new_ready)
        if len(result) != len(self._nodes):
            missing = sorted(set(self._nodes) - set(result))
            raise CycleError(
                f"cycle detected among nodes: {missing!r}"
            )
        return result


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------

def _rel_pkg_path(root_pkg: ArchitecturePackage, pkg: ArchitecturePackage) -> PurePosixPath:
    assert root_pkg.root is not None and pkg.root is not None
    if pkg.root == root_pkg.root:
        return PurePosixPath(".")
    return PurePosixPath(pkg.root.relative_to(root_pkg.root).as_posix())


def _join_rel(base: PurePosixPath, leaf: str) -> str:
    if str(base) in (".", ""):
        return leaf
    return f"{base}/{leaf}"


def build_graph(
    root_pkg: ArchitecturePackage,
    *,
    extra_nodes: Iterable[StaleNode] = (),
) -> DependencyGraph:
    """Build a DAG for a package tree.

    For every package in the tree (root + descendants) three nodes are
    added: ``package:<id>``, ``model:<id>`` and ``manifest:<id>``, with
    edges ``package -> model -> manifest``. For each non-root package,
    an edge ``model:<child> -> model:<root>`` is added, expressing that
    the parent's aggregated model depends on the child's model.

    ``extra_nodes`` lets callers inject slice, view or artifact nodes to
    participate in :func:`mark_stale` propagation. Edges implied by each
    ``StaleNode.inputs`` field are added automatically (each input id is
    treated as upstream). Extra nodes may reference the auto-generated
    nodes by id.
    """
    g = DependencyGraph()
    all_pkgs = list(iter_descendants(root_pkg, include_self=True))
    # Auto-generated nodes per package
    for pkg in all_pkgs:
        rel = _rel_pkg_path(root_pkg, pkg)
        pkg_id = pkg.architecture_id
        pkg_node = StaleNode(
            node_id=f"package:{pkg_id}",
            kind="package",
            owned_paths=(_join_rel(rel, "package.yaml"),),
        )
        model_node = StaleNode(
            node_id=f"model:{pkg_id}",
            kind="model",
            owned_paths=(_join_rel(rel, pkg.model_ref),),
            inputs=(f"package:{pkg_id}",),
        )
        manifest_node = StaleNode(
            node_id=f"manifest:{pkg_id}",
            kind="manifest",
            owned_paths=(_join_rel(rel, "**/*.py"),),
            inputs=(f"model:{pkg_id}",),
        )
        g.add_node(pkg_node)
        g.add_node(model_node)
        g.add_node(manifest_node)
        g.add_edge(pkg_node.node_id, model_node.node_id)
        g.add_edge(model_node.node_id, manifest_node.node_id)

    # child.model -> root.model edges
    root_model_id = f"model:{root_pkg.architecture_id}"
    for pkg in all_pkgs:
        if pkg.architecture_id == root_pkg.architecture_id:
            continue
        g.add_edge(f"model:{pkg.architecture_id}", root_model_id)

    # Extra nodes (slice/view/artifact/etc.). Add nodes first, then edges.
    extras = list(extra_nodes)
    for node in extras:
        g.add_node(node)
    for node in extras:
        for up in node.inputs:
            g.add_edge(up, node.node_id)

    return g


# ---------------------------------------------------------------------------
# mark_stale
# ---------------------------------------------------------------------------

def _norm_rel(path: Path, package_root: Path) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = Path(p).resolve().relative_to(Path(package_root).resolve())
        except ValueError:
            # Path outside package root — keep POSIX form so it can still
            # be compared against absolute globs if callers use them.
            return PurePosixPath(p.as_posix()).as_posix()
    return PurePosixPath(p.as_posix()).as_posix()


def _matches_any(rel: str, patterns: Iterable[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatchcase(rel, pat):
            return True
        # Support recursive '**' semantics beyond fnmatch by expanding
        # a common case: pattern 'X/**' should also match 'X/a/b.py'.
        # fnmatch treats '*' as any-non-slash, but the '**' segment here
        # is really shorthand for "any depth". We normalize by testing
        # against a version where '**' -> '*' and comparing path prefix.
        if "**" in pat:
            prefix = pat.split("**", 1)[0].rstrip("/")
            if prefix and (rel == prefix or rel.startswith(prefix + "/")):
                return True
    return False


def mark_stale(
    graph: DependencyGraph,
    changed_paths: Iterable[Path],
    *,
    package_root: Path,
) -> StaleSet:
    """Return the set of nodes made stale by ``changed_paths``.

    Direct invalidation: any node whose ``owned_paths`` globs match any
    changed path (semantic intersection). Nodes with empty ``owned_paths``
    are only invalidated transitively.

    Propagation: every descendant of a directly-invalidated node is also
    stale, with reason recording the upstream trigger.
    """
    rels = sorted({_norm_rel(p, package_root) for p in changed_paths})

    direct: dict[str, str] = {}
    for node in graph.nodes():  # already sorted
        if not node.owned_paths:
            continue
        matched = [r for r in rels if _matches_any(r, node.owned_paths)]
        if matched:
            direct[node.node_id] = (
                f"owned path matched: {matched[0]}"
            )

    reasons: dict[str, str] = {}
    stale: set[str] = set()
    # Add direct in sorted order for deterministic reason messages.
    for nid in sorted(direct):
        reasons[nid] = direct[nid]
        stale.add(nid)
        for d in sorted(graph.descendants(nid)):
            if d not in reasons:
                reasons[d] = f"upstream stale: {nid}"
                stale.add(d)

    return StaleSet(nodes=frozenset(stale), reasons=reasons)


# ---------------------------------------------------------------------------
# stale_report — with .architecture/stale.yaml cache
# ---------------------------------------------------------------------------

def _cache_path(root_pkg: ArchitecturePackage) -> Path:
    assert root_pkg.root is not None
    return root_pkg.root / ".architecture" / "stale.yaml"


def _cache_key(graph: DependencyGraph, changed_rels: list[str]) -> str:
    """Deterministic digest of graph shape + inputs."""
    payload = {
        "nodes": [
            {
                "id": n.node_id,
                "kind": n.kind,
                "owned": list(n.owned_paths),
                "inputs": list(n.inputs),
                "digest": n.digest,
            }
            for n in graph.nodes()
        ],
        "changed": changed_rels,
    }
    return canonical_json(payload).decode("utf-8")


def _render_cache_yaml(key: str, report: list[StaleNode], reasons: dict[str, str]) -> bytes:
    lines = [
        "# Auto-generated by architecture_model.lifecycle.stale — do not edit.",
        f"key_digest: {key.__hash__() & 0xffffffff:08x}",
        "nodes:",
    ]
    for n in report:
        lines.append(f"  - id: {n.node_id}")
        lines.append(f"    kind: {n.kind}")
        reason = reasons.get(n.node_id, "").replace("'", "''")
        lines.append(f"    reason: '{reason}'")
    # Store the key itself so we can compare on next run.
    lines.append("cache_key: |")
    for line in key.splitlines() or [key]:
        lines.append(f"  {line}")
    if not key.splitlines():
        lines[-1] = f"  {key}"
    return ("\n".join(lines) + "\n").encode("utf-8")


def _read_cached_key(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    marker = "cache_key: |"
    if marker not in text:
        return None
    tail = text.split(marker, 1)[1]
    body_lines = []
    for line in tail.splitlines():
        if line.startswith("  "):
            body_lines.append(line[2:])
        elif not line.strip():
            continue
        else:
            break
    return "\n".join(body_lines) if body_lines else None


def stale_report(
    root_pkg: ArchitecturePackage,
    changed_paths: Iterable[Path],
) -> list[StaleNode]:
    """Compute the stale-node report for ``root_pkg``.

    Convenience wrapper over :func:`build_graph` + :func:`mark_stale`.
    Results are sorted by ``(kind, node_id)``. The result is cached at
    ``<package_root>/.architecture/stale.yaml``; if the cache's key digest
    matches the current graph+inputs digest the cached report is returned
    without rebuilding. Missing or corrupt caches are silently regenerated.
    """
    assert root_pkg.root is not None
    graph = build_graph(root_pkg)
    changed_list = list(changed_paths)
    rels = sorted({_norm_rel(p, root_pkg.root) for p in changed_list})
    key = _cache_key(graph, rels)
    cache = _cache_path(root_pkg)

    stale = mark_stale(graph, changed_list, package_root=root_pkg.root)
    id_to_node = {n.node_id: n for n in graph.nodes()}
    report = sorted(
        (id_to_node[nid] for nid in stale.nodes if nid in id_to_node),
        key=lambda n: (n.kind, n.node_id),
    )

    # Only write when key differs (avoid unnecessary churn).
    prev_key = _read_cached_key(cache)
    if prev_key != key:
        try:
            write_atomic(cache, _render_cache_yaml(key, report, stale.reasons))
        except OSError:
            # Cache is best-effort; never fail the report.
            pass

    return report
