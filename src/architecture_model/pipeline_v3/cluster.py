"""pipeline_v3.cluster — Component grouping stage (T0.14 Phase 6.3).

Groups :class:`ScannedModule` records into :class:`Cluster` records by
dotted-name prefix. Each cluster is a candidate v3 component; downstream
stages (link, containerize, publish) turn clusters into ``COMP-*`` entities
with realizes/depends-on relationships.

Simplification vs. legacy manifest.grouping
-------------------------------------------
The legacy :mod:`architecture_model.manifest.grouping` uses multi-signal
affinity (subdirectory + name-prefix + import edges) with a full merge-
and-split pipeline. That algorithm is production-tested and remains the
default for legacy pipeline consumers.

For v3 first-pass, we deliberately start with a simpler, more transparent
prefix-based clustering:

    - Group modules by the first ``depth`` dotted-name segments.
    - Cluster id = ``COMP-<sha1(root_prefix)[:8]>`` (deterministic).
    - Cluster name = last segment of the root prefix (human-friendly).
    - Clusters and their modules are sorted for byte-stable output.

Import-affinity refinement can be added later as an optional post-pass
(see Phase 9 / adapter tasks) without changing this module's interface.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field

from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult

__all__ = ["Cluster", "cluster_modules"]


@dataclass(frozen=True)
class Cluster:
    """A candidate v3 component: a group of modules under a common prefix."""

    id: str                       # COMP-<sha1[:8]>
    name: str                     # last segment of root_prefix
    root_prefix: str              # dotted prefix shared by all modules
    modules: list[ScannedModule] = field(default_factory=list)

    @property
    def module_count(self) -> int:
        return len(self.modules)


def _compute_cluster_id(root_prefix: str) -> str:
    """Deterministic COMP-<sha1[:8]> id from a root prefix."""
    digest = hashlib.sha1(root_prefix.encode("utf-8")).hexdigest()
    return f"COMP-{digest[:8]}"


def _root_prefix(name: str, depth: int) -> str:
    """Return the first ``depth`` dotted segments of ``name``.

    If ``name`` has fewer than ``depth`` segments, the whole name is returned.
    """
    parts = name.split(".")
    return ".".join(parts[:depth]) if len(parts) >= depth else name


def cluster_modules(scan: ScanResult, *, depth: int = 3) -> list[Cluster]:
    """Group ``scan.modules`` into Clusters keyed by dotted-name prefix.

    Args:
        scan: Output from :func:`architecture_model.pipeline_v3.scan.scan_repo`.
        depth: Number of dotted segments to use as the cluster key.
            Default 3 (e.g. ``src.pkg.subpkg`` for ``src.pkg.subpkg.mod``).

    Returns:
        List of Clusters sorted by ``root_prefix``. Each cluster's ``modules``
        list is sorted by module dotted name.
    """
    buckets: dict[str, list[ScannedModule]] = defaultdict(list)
    for m in scan.modules:
        buckets[_root_prefix(m.name, depth)].append(m)

    clusters: list[Cluster] = []
    for root in sorted(buckets):
        mods = sorted(buckets[root], key=lambda m: m.name)
        name = root.split(".")[-1] if root else root
        clusters.append(
            Cluster(
                id=_compute_cluster_id(root),
                name=name,
                root_prefix=root,
                modules=mods,
            )
        )
    return clusters
