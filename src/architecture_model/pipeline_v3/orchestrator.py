"""pipeline_v3.orchestrator — Stage coordinator (T0.14 Phase 6.8).

Wires the seven pipeline_v3 stages into a single end-to-end run:

    scan → derive_promises → cluster → link → containerize → verify → publish

Exposes :func:`run_pipeline` and :class:`PipelineRunResult`. Every
intermediate artifact (scan, promises, clusters, links, model, verify
report, per-component reports, publish result) is available on the
returned :class:`PipelineRunResult` so downstream tooling can inspect
any stage without re-running.

Substrate integration
---------------------

As of the walk-substrate work (Part 1), the orchestrator runs on the
generic :class:`~architecture_model.pipeline_v3.substrate.Pipeline`
runner. Each pipeline_v3 stage becomes a :class:`Stage` operating on a
shared ``_PipelineState`` dict. Output is byte-identical to the pre-
substrate straight-line implementation (guarded by existing tests).

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
from typing import Any

from architecture_model.core.promise import Promise
from architecture_model.pipeline_v3.cluster import Cluster, cluster_modules
from architecture_model.pipeline_v3.containerize import (
    ContainerizedModel,
    containerize,
)
from architecture_model.pipeline_v3.derive_behaviors import (
    BehaviorCandidate,
    derive_behaviors,
)
from architecture_model.pipeline_v3.derive_promises import derive_promises
from architecture_model.pipeline_v3.derive_triggers import (
    TriggerEdge,
    derive_triggers,
)
from architecture_model.pipeline_v3.link import Link, link_clusters
from architecture_model.pipeline_v3.publish import PublishResult, publish_model
from architecture_model.pipeline_v3.scan import ScanResult, scan_repo
from architecture_model.pipeline_v3.substrate import (
    Pipeline,
    StageContext,
    wrap_function,
)
from architecture_model.pipeline_v3.verify import (
    verify_model,
    verify_per_component,
)
from architecture_model.quality.chain_closure import ChainClosureReport

__all__ = ["PipelineRunResult", "run_pipeline"]


def _load_default_provider():
    """Lazy-load OCA's MCPProvider. Raise actionable error if unavailable.

    Called only when ``infer_attributes=True`` and no
    ``attribute_provider`` was passed. Keeps AMS free of hard dependencies
    on opencode-arch.
    """
    try:
        from opencode_arch.llm.providers.mcp import MCPProvider  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "run_pipeline(infer_attributes=True) requires either an "
            "explicit `attribute_provider=...` argument or the "
            "`opencode-arch` package. Install with "
            "`pip install opencode-arch` or pass a custom LLMProvider."
        ) from exc
    return MCPProvider()


@dataclass(frozen=True)
class PipelineRunResult:
    """All intermediate artifacts + final outputs from a pipeline_v3 run."""

    scan: ScanResult
    module_promises: list[Promise]
    behavior_candidates: list[BehaviorCandidate]
    trigger_edges: list[TriggerEdge]
    clusters: list[Cluster]
    links: list[Link]
    model: ContainerizedModel
    verify_report: ChainClosureReport
    per_component_reports: dict[str, ChainClosureReport]
    published: PublishResult | None


def _build_pipeline(
    repo: Path,
    out: Path,
    project_name: str,
    cluster_depth: int,
    skip_publish: bool,
    infer_attributes: bool = False,
    attribute_provider=None,
    ingest_requirements: bool = False,
    doc_roots=None,
    requirements_provider=None,
) -> Pipeline:
    """Build the pipeline_v3 stage pipeline over a shared state dict.

    State keys: ``repo``, ``scan``, ``module_promises``, ``clusters``,
    ``links``, ``model``, ``verify_report``, ``per_component_reports``,
    ``published``.
    """

    def _scan(state: dict[str, Any]) -> dict[str, Any]:
        state["scan"] = scan_repo(state["repo"])
        return state

    def _derive(state: dict[str, Any]) -> dict[str, Any]:
        state["module_promises"] = derive_promises(state["scan"])
        return state

    def _derive_behaviors(state: dict[str, Any]) -> dict[str, Any]:
        state["behavior_candidates"] = derive_behaviors(state["scan"])
        return state

    def _derive_triggers(state: dict[str, Any]) -> dict[str, Any]:
        state["trigger_edges"] = derive_triggers(
            state["scan"], state["behavior_candidates"]
        )
        return state

    def _cluster(state: dict[str, Any]) -> dict[str, Any]:
        state["clusters"] = cluster_modules(state["scan"], depth=cluster_depth)
        return state

    def _link(state: dict[str, Any]) -> dict[str, Any]:
        state["links"] = link_clusters(state["clusters"])
        return state

    def _containerize(state: dict[str, Any]) -> dict[str, Any]:
        state["model"] = containerize(
            state["clusters"],
            state["module_promises"],
            state["links"],
            state["behavior_candidates"],
            state["trigger_edges"],
        )
        return state

    def _verify(state: dict[str, Any]) -> dict[str, Any]:
        state["verify_report"] = verify_model(state["model"])
        state["per_component_reports"] = verify_per_component(state["model"])
        return state

    def _publish(state: dict[str, Any]) -> dict[str, Any]:
        if skip_publish:
            state["published"] = None
        else:
            transform_doc = None
            if infer_attributes or ingest_requirements:
                _attr_provider = attribute_provider
                if infer_attributes and _attr_provider is None:
                    _attr_provider = _load_default_provider()

                def transform_doc(doc: dict) -> dict:
                    if infer_attributes:
                        from architecture_model.pipeline_v3.derive_attributes_llm import (
                            derive_attributes,
                        )

                        doc = derive_attributes(doc, provider=_attr_provider)
                    if ingest_requirements:
                        from architecture_model.pipeline_v3.ingest_requirements import (
                            DEFAULT_DOC_ROOTS,
                            ingest_requirements as _ingest,
                        )

                        doc = _ingest(
                            doc,
                            repo_path=repo,
                            doc_roots=doc_roots or DEFAULT_DOC_ROOTS,
                            provider=requirements_provider,
                        )
                    return doc

            state["published"] = publish_model(
                state["model"],
                out,
                project_name=project_name,
                source_root=repo,
                transform_doc=transform_doc,
            )
        return state

    return Pipeline(
        [
            wrap_function("scan", _scan),
            wrap_function("derive_promises", _derive),
            wrap_function("derive_behaviors", _derive_behaviors),
            wrap_function("derive_triggers", _derive_triggers),
            wrap_function("cluster", _cluster),
            wrap_function("link", _link),
            wrap_function("containerize", _containerize),
            wrap_function("verify", _verify),
            wrap_function("publish", _publish),
        ]
    )


def run_pipeline(
    repo_path: Path | str,
    *,
    out_path: Path | str,
    project_name: str = "",
    cluster_depth: int = 3,
    skip_publish: bool = False,
    infer_attributes: bool = False,
    attribute_provider=None,
    ingest_requirements: bool = False,
    doc_roots=None,
    requirements_provider=None,
) -> PipelineRunResult:
    """Run the full pipeline_v3 end-to-end via the substrate runner.

    Args:
        repo_path: Absolute or relative path to the source tree to scan.
        out_path: Destination for the v3 YAML (ignored when
            ``skip_publish=True``).
        project_name: Stamped into ``meta.project``.
        cluster_depth: Dotted-segment depth for cluster grouping.
        skip_publish: If True, skip the publish stage entirely — no
            file is written and ``PipelineRunResult.published`` is None.
        infer_attributes: If True, run R7's LLM-based Category B attribute
            inference before serialization. Off by default so runs stay
            deterministic and cost-free.
        attribute_provider: LLMProvider used when ``infer_attributes=True``.
            When ``None`` and the flag is on, the pipeline lazy-loads the
            MCPProvider from ``opencode_arch`` and raises RuntimeError with
            install instructions when it is not available.

    Returns:
        :class:`PipelineRunResult` with every intermediate and final artifact.
    """
    repo = Path(repo_path)
    out = Path(out_path)

    pipeline = _build_pipeline(
        repo,
        out,
        project_name,
        cluster_depth,
        skip_publish,
        infer_attributes=infer_attributes,
        attribute_provider=attribute_provider,
        ingest_requirements=ingest_requirements,
        doc_roots=doc_roots,
        requirements_provider=requirements_provider,
    )
    initial_state: dict[str, Any] = {"repo": repo}
    result = pipeline.run(initial_state, StageContext(run_id="pipeline_v3"))

    final = result.final
    assert final is not None and final.value is not None, "pipeline produced no state"
    state = final.value

    return PipelineRunResult(
        scan=state["scan"],
        module_promises=state["module_promises"],
        behavior_candidates=state["behavior_candidates"],
        trigger_edges=state["trigger_edges"],
        clusters=state["clusters"],
        links=state["links"],
        model=state["model"],
        verify_report=state["verify_report"],
        per_component_reports=state["per_component_reports"],
        published=state["published"],
    )
