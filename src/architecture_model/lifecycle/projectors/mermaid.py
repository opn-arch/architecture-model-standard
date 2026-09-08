"""Adapters wrapping architecture_model.docs.diagrams generators as projectors.

Task 7 of Phase 1 substrate-and-liveness plan. Follows the Task 6 SE-docs
pattern: uniform `(fragment, config) -> DiagramSpec` adapter. Emits
``facets["content_kind"] = "mermaid"`` so downstream renderers can
distinguish diagram bodies from prose.
"""
from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from architecture_model.core.diagram_spec import DiagramSpec

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.lifecycle.view_projection import ProjectorFn, ProjectorRegistry


def _load_generator(fn_name: str) -> Callable[..., str]:
    import importlib
    mod = importlib.import_module("architecture_model.docs.diagrams")
    return getattr(mod, fn_name)


def _wrap(projector_name: str, fn_name: str) -> "ProjectorFn":
    def adapter(fragment: "ArchitectureModel", config: dict[str, Any]) -> DiagramSpec:
        del config
        body = _load_generator(fn_name)(fragment)
        return DiagramSpec(
            id=f"diagram:{projector_name}",
            title=projector_name,
            facets={"content_kind": "mermaid", "body": body},
        )

    adapter.__name__ = f"adapter_{projector_name.replace('.', '_')}"
    return adapter


MERMAID_PROJECTOR_MAP: dict[str, str] = {
    "family3.component_diagram": "generate_component_diagram",
    "family4.use_case_diagram": "generate_use_case_diagram",
    "family1.system_boundary_diagram": "generate_system_boundary_diagram",
}


def register_all(registry: "ProjectorRegistry") -> None:
    for name, fn_name in MERMAID_PROJECTOR_MAP.items():
        if name in registry:
            continue
        registry.register(name, _wrap(name, fn_name), version="1.0.0")
