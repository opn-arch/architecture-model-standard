"""pipeline_v3.orchestrator — Stage coordinator (T0.14 Phase 6.8).

Wires the seven pipeline_v3 stages into a single end-to-end run:

    scan → derive_promises → cluster → link → containerize → verify → publish

Exposes :func:`run_pipeline` and :class:`PipelineRunResult`. Every
intermediate artifact (scan, promises, clusters, links, model, verify
report, per-component reports, publish result) is available on the
returned :class:`PipelineRunResult` so downstream tooling can inspect
any stage without re-running.

Design intent
-------------

The orchestrator is deliberately thin — a straight-line composition of
the seven stage modules. Each stage remains independently testable and
callable; the orchestrator adds convenience, not new semantics. That
choice keeps failure isolation trivial: any bug lives in the stage it
belongs to, not in a coordination layer.

Optional flags
--------------

- ``cluster_depth``: dotted-segment depth for clustering (default 3).
- ``project_name``: stamped into ``meta.project`` at publish time.
- ``skip_publish``: run every stage except publish; leave no artifact
  on disk. Useful for CI checks, tests, and in-memory workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from architecture_model.core.promise import Promise
from architecture_model.pipeline_v3.cluster import Cluster, cluster_modules
from architecture_model.pipeline_v3.containerize import (
    ContainerizedModel,
    containerize,
)
from architecture_model.pipeline_v3.derive_promises import derive_promises
from architecture_model.pipeline_v3.link import Link, link_clusters
from architecture_model.pipeline_v3.publish import PublishResult, publish_model
from architecture_model.pipeline_v3.scan import ScanResult, scan_repo
from architecture_model.pipeline_v3.verify import (
    verify_model,
    verify_per_component,
)
from architecture_model.quality.chain_closure import ChainClosureReport

__all__ = ["PipelineRunResult", "run_pipeline"]


@dataclass(frozen=True)
class PipelineRunResult:
    """All intermediate artifacts + final outputs from a pipeline_v3 run."""

    scan: ScanResult
    module_promises: list[Promise]
    clusters: list[Cluster]
    links: list[Link]
    model: ContainerizedModel
    verify_report: ChainClosureReport
    per_component_reports: dict[str, ChainClosureReport]
    published: PublishResult | None


def run_pipeline(
    repo_path: Path | str,
    *,
    out_path: Path | str,
    project_name: str = "",
    cluster_depth: int = 3,
    skip_publish: bool = False,
) -> PipelineRunResult:
    """Run the full pipeline_v3 end-to-end.

    Args:
        repo_path: Absolute or relative path to the source tree to scan.
        out_path: Destination for the v3 YAML (ignored when
            ``skip_publish=True``).
        project_name: Stamped into ``meta.project``.
        cluster_depth: Dotted-segment depth for cluster grouping.
        skip_publish: If True, skip the publish stage entirely — no
            file is written and ``PipelineRunResult.published`` is None.

    Returns:
        :class:`PipelineRunResult` with every intermediate and final artifact.
    """
    repo = Path(repo_path)
    out = Path(out_path)

    scan = scan_repo(repo)
    module_promises = derive_promises(scan)
    clusters = cluster_modules(scan, depth=cluster_depth)
    links = link_clusters(clusters)
    model = containerize(clusters, module_promises, links)
    report = verify_model(model)
    per_comp = verify_per_component(model)

    published: PublishResult | None = None
    if not skip_publish:
        published = publish_model(
            model,
            out,
            project_name=project_name,
            source_root=repo,
        )

    return PipelineRunResult(
        scan=scan,
        module_promises=module_promises,
        clusters=clusters,
        links=links,
        model=model,
        verify_report=report,
        per_component_reports=per_comp,
        published=published,
    )
