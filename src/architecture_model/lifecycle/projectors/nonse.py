"""Adapters wrapping architecture_model.docs non-SE generators as projectors.

Task 7 of Phase 1 substrate-and-liveness plan. Heterogeneous signatures:
each adapter constructs the required args from the fragment. For
multi-entity generators (component_spec, behavior_spec) outputs are
aggregated across all entities and joined with '\\n\\n---\\n\\n' so each
family<N>.<name> maps to a single deterministic body.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.projectors.drill import drill_to_map

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.lifecycle.view_projection import ProjectorFn, ProjectorRegistry


def _empty_manifest():
    from architecture_model.manifest.types import Manifest, MetricsResult
    return Manifest(
        generated_at="1970-01-01T00:00:00Z",
        project_root=".",
        metrics=MetricsResult(),
        functional_blocks={},
        modules=[],
        interfaces=[],
    )


def _family_of(projector_name: str) -> int:
    prefix = projector_name.split(".", 1)[0]
    assert prefix.startswith("family")
    return int(prefix[len("family"):])


def _prose(projector_name: str, body: str, fragment=None) -> DiagramSpec:
    facets: dict[str, Any] = {"content_kind": "markdown", "body": body}
    if fragment is not None:
        facets["drill_to"] = drill_to_map(fragment, _family_of(projector_name))
    return DiagramSpec(
        id=f"prose:{projector_name}",
        title=projector_name,
        facets=facets,
    )


def _adapter_component_spec(fragment, config):
    del config
    from architecture_model.docs.component_spec import generate_component_spec
    parts = [generate_component_spec(c, fragment) for c in fragment.entities.components]
    return _prose("family3.component_spec", "\n\n---\n\n".join(parts), fragment)


def _adapter_icd(fragment, config):
    del config
    from architecture_model.docs.icd import generate_icd
    return _prose("family6.icd", generate_icd(fragment), fragment)


def _adapter_dependency_matrix(fragment, config):
    del config
    from architecture_model.docs.dependency_matrix import generate_dependency_matrix
    return _prose("family3.dependency_matrix", generate_dependency_matrix(fragment), fragment)


def _adapter_health(fragment, config):
    del config
    from architecture_model.docs.health import generate_health_report
    return _prose("family8.health", generate_health_report(fragment), fragment)


def _adapter_drift(fragment, config):
    del config
    from architecture_model.docs.drift import generate_drift_report
    # Identity drift = "no changes"; deterministic representation of steady state.
    return _prose("family8.drift", generate_drift_report(fragment, fragment), fragment)


def _adapter_system_design(fragment, config):
    del config
    from architecture_model.docs.system_design import generate_system_design
    return _prose("family3.system_design", generate_system_design(fragment), fragment)


def _adapter_integration_flows(fragment, config):
    del config
    from architecture_model.docs.integration_flows import generate_integration_flows
    return _prose("family4.integration_flows", generate_integration_flows(fragment), fragment)


def _adapter_behavior_spec(fragment, config):
    del config
    from architecture_model.docs.behavior_spec import generate_behavior_spec
    from architecture_model.manifest.call_graph import FlowTrace
    manifest = _empty_manifest()
    parts = []
    for beh in fragment.entities.behaviors:
        flow = FlowTrace(entry=beh.id, steps=[], components_crossed=[], depth=0, truncated=False)
        parts.append(generate_behavior_spec(beh, flow, manifest, {}))
    return _prose("family4.behavior_spec", "\n\n---\n\n".join(parts), fragment)


def _adapter_index(fragment, config):
    del config
    from architecture_model.docs.index import generate_index
    return _prose("family8.index", generate_index(fragment, {}), fragment)


NONSE_ADAPTER_MAP: dict[str, "ProjectorFn"] = {
    "family3.component_spec": _adapter_component_spec,
    "family6.icd": _adapter_icd,
    "family3.dependency_matrix": _adapter_dependency_matrix,
    "family8.health": _adapter_health,
    "family8.drift": _adapter_drift,
    "family3.system_design": _adapter_system_design,
    "family4.integration_flows": _adapter_integration_flows,
    "family4.behavior_spec": _adapter_behavior_spec,
    "family8.index": _adapter_index,
}


def register_all(registry: "ProjectorRegistry") -> None:
    for name, adapter in NONSE_ADAPTER_MAP.items():
        if name in registry:
            continue
        registry.register(name, adapter, version="1.0.0")
