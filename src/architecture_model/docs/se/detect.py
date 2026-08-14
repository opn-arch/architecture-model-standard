"""Auto-detect which project-specific documents should be generated."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def detect_project_docs(model: ArchitectureModel) -> list[str]:
    """Return list of project-specific doc types to generate based on model content.

    Returns doc type keys like 'api_reference', 'data_model', etc.
    """
    docs: list[str] = []

    # API Reference — if REST/HTTP interfaces exist
    rest_interfaces = [i for i in model.entities.interfaces
                       if str(getattr(i.type, "value", i.type)).upper() in ("REST", "WEBSOCKET")]
    if rest_interfaces:
        docs.append("api_reference")

    # Data Model — if DB/ORM components or "data" layer exists
    data_comps = [c for c in model.entities.components
                  if getattr(c, "kind", None) and
                  str(getattr(c.kind, "value", c.kind)) in ("data-store", "data-model")]
    data_layers = [la for la in model.entities.layers
                   if "data" in la.name.lower() or "db" in la.name.lower()]
    if data_comps or data_layers:
        docs.append("data_model")

    # Deployment Guide — if OPERATIONAL or TECHNOLOGY constraints exist
    deploy_constraints = [c for c in model.entities.constraints
                          if _constraint_type_str(c.type) in ("operational", "technology")]
    infra_comps = [c for c in model.entities.components
                   if getattr(c, "kind", None) and
                   str(getattr(c.kind, "value", c.kind)) == "infrastructure"]
    if deploy_constraints or infra_comps:
        docs.append("deployment_guide")

    # Security Analysis — if security constraints or auth/security components exist
    sec_constraints = [c for c in model.entities.constraints
                       if _constraint_type_str(c.type) == "security"]
    sec_comps = [c for c in model.entities.components
                 if any(kw in c.name.lower() for kw in ("auth", "security", "csrf", "permission"))]
    if sec_constraints or sec_comps:
        docs.append("security_analysis")

    # CLI Reference — if CLI interfaces exist
    cli_interfaces = [i for i in model.entities.interfaces
                      if str(getattr(i.type, "value", i.type)).upper() == "CLI"]
    cli_comps = [c for c in model.entities.components
                 if getattr(c, "kind", None) and
                 str(getattr(c.kind, "value", c.kind)) == "cli"]
    if cli_interfaces or cli_comps:
        docs.append("cli_reference")

    # Plugin/Extension Guide — if abstract classes or plugin patterns detected
    abstract_comps = [c for c in model.entities.components
                      if any(kw in c.name.lower() for kw in ("plugin", "extension", "backend", "adapter"))]
    if abstract_comps:
        docs.append("plugin_guide")

    return docs
