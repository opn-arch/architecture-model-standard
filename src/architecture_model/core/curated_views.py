"""Shared assembly for curated native architecture views."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .diagram_renderer import DiagramRenderOptions, render_diagram_panel
from .diagram_spec import Diagnostic, DiagramSpec
from .se_view_projectors import (
    project_conops,
    project_functional_architecture,
    project_logical_architecture,
    project_use_cases,
)
from .view_context import ArchitectureViewContext
from .view_curation import ViewCuration, load_viewer_curation

if TYPE_CHECKING:
    from .types import ArchitectureModel


NATIVE_VIEW_DEFINITIONS = {
    "conops": ("ConOps", "Concept of Operations", project_conops, "conops", "conops.svg"),
    "functional": ("Functional Architecture", "Functional Analysis (SA-4.2)", project_functional_architecture, "functional", "functional-architecture.svg"),
    "logical": ("Logical Architecture", "Logical Decomposition (SA-4.3)", project_logical_architecture, "logical", "logical-architecture.svg"),
    "use-cases": ("Use Cases", "Use Case Analysis", project_use_cases, "use_cases", "use-cases.svg"),
}


def build_curated_views(
    model: "ArchitectureModel",
    repo_path: str | Path,
    *,
    curation_path: str | Path | None = None,
    use_curation: bool = True,
    theme: str = "light",
) -> dict[str, dict[str, Any]]:
    """Project and render all native views from one hierarchy and curation load."""

    root = Path(repo_path).resolve()
    context = ArchitectureViewContext.load(model, root)
    curation = load_viewer_curation(root, context, curation_path) if use_curation else None
    candidate = Path(curation_path) if curation_path is not None else root / ".architecture/viewer-curation.yaml"
    candidate = candidate if candidate.is_absolute() else root / candidate
    exists = use_curation and candidate.is_file()
    options = DiagramRenderOptions(theme=theme)
    views: dict[str, dict[str, Any]] = {}
    for key, (label, subtitle, projector, curation_name, filename) in NATIVE_VIEW_DEFINITIONS.items():
        diagnostics = [item for item in (curation.diagnostics if curation else []) if not item.view or item.view == curation_name]
        selected = getattr(curation.views, curation_name) if curation is not None else ViewCuration()
        try:
            spec = projector(context, selected)
        except ValueError:
            diagnostic = Diagnostic(
                "warning", "VIEW_PROJECTION_INVALID",
                f"Unsafe or invalid presentation data omitted; automatic {label} view unavailable",
                view=curation_name, source="model",
            )
            spec = DiagramSpec(key, label, subtitle, warnings=[diagnostic])
            diagnostics.append(diagnostic)
        spec.warnings.extend(item for item in context.diagnostics if item not in spec.warnings)
        spec.warnings.extend(item for item in diagnostics if item not in spec.warnings)
        views[key] = {
            "label": label,
            "subtitle": subtitle,
            "filename": filename,
            "spec": spec,
            "panel": render_diagram_panel(spec, options),
            "context": context,
            "view_curation": selected,
            "curation": {
                "status": "partial" if diagnostics else "curated" if exists else "auto",
                "path": str(candidate) if use_curation else "disabled",
            },
        }
    return views
