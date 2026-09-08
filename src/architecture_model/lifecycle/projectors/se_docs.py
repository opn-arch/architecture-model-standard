"""Adapters wrapping architecture_model.docs.se generators as projectors.

Each adapter takes ``(fragment: ArchitectureModel, config: dict)`` per the
ProjectorFn contract and returns a ``DiagramSpec`` whose Markdown body is
stashed in ``facets["body"]`` with ``facets["content_kind"] = "markdown"``.

Design note (2026-09-08): Phase 1 intentionally overloads DiagramSpec to
carry prose content pending Phase 2's ProseSpec / RenderedContent union.
The ``facets["content_kind"]`` discriminator lets downstream renderers
(and Task 8+ invalidation) distinguish diagram vs prose views.
"""
from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from architecture_model.core.diagram_spec import DiagramSpec

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.lifecycle.view_projection import ProjectorFn, ProjectorRegistry


# Discover generators lazily to avoid circular imports and to keep the
# adapter module cheap to import.
def _load_generator(module_name: str) -> Callable[..., str]:
    import importlib
    mod = importlib.import_module(f"architecture_model.docs.se.{module_name}")
    return getattr(mod, f"generate_{module_name}")


def _wrap(projector_name: str, module_name: str) -> "ProjectorFn":
    """Return a ProjectorFn that renders `generate_<module_name>(model)` as prose."""

    def adapter(fragment: "ArchitectureModel", config: dict[str, Any]) -> DiagramSpec:
        del config  # SE prose generators take no config in Phase 1
        gen_fn = _load_generator(module_name)
        body = gen_fn(fragment)
        return DiagramSpec(
            id=f"prose:{projector_name}",
            title=projector_name,
            facets={"content_kind": "markdown", "body": body},
        )

    adapter.__name__ = f"adapter_{projector_name.replace('.', '_')}"
    return adapter


# (projector_name, se_module_name) — order matches EXPECTED_SE_PROJECTORS in
# the task plan to keep list_names() insertion order stable and reviewable.
SE_PROJECTOR_MAP: dict[str, str] = {
    "family1.conops": "conops",
    "family2.functional_analysis": "functional_analysis",
    "family3.logical_architecture": "logical_architecture",
    "family4.operations_manual": "operations_manual",
    "family4.maintenance_manual": "maintenance_manual",
    "family4.use_cases": "use_cases",
    "family5.deployment_guide": "deployment_guide",
    "family6.interface_spec": "interface_spec",
    "family6.api_reference": "api_reference",
    "family6.cli_reference": "cli_reference",
    "family6.plugin_guide": "plugin_guide",
    "family6.data_model": "data_model",
    "family7.requirements_analysis": "requirements_analysis",
    "family7.verification_validation": "verification_validation",
    "family7.risk_assessment": "risk_assessment",
    "family7.security_analysis": "security_analysis",
    "family7.artifact_traceability": "artifact_traceability",
}


def register_all(registry: "ProjectorRegistry") -> None:
    """Register all 17 SE doc adapters. Skips names already registered.

    The skip-if-registered behavior is important for import-time idempotency:
    Task 5's `_seed_default_registry()` guards against re-invocation, but
    callers that construct their own ProjectorRegistry then call
    ``register_all`` on it should not fail if they invoke twice.
    """
    for name, module_name in SE_PROJECTOR_MAP.items():
        if name in registry:
            continue
        registry.register(name, _wrap(name, module_name), version="1.0.0")
