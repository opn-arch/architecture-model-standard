"""Documentation generator orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from architecture_model.docs.component_spec import generate_component_spec
from architecture_model.docs.dependency_matrix import generate_dependency_matrix
from architecture_model.docs.icd import generate_icd
from architecture_model.docs.health import generate_health_report
from architecture_model.docs.system_design import generate_system_design
from architecture_model.docs.integration_flows import generate_integration_flows
from architecture_model.docs.drift import generate_drift_report
from architecture_model.docs.index import generate_index

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_docs(
    model: "ArchitectureModel",
    output_dir: Path | str,
    manifest: dict | None = None,
    previous_model: "ArchitectureModel | None" = None,
) -> dict[str, list[Path]]:
    """Generate architecture documentation.

    Returns dict of category -> list of generated file paths.
    """
    output_dir = Path(output_dir)
    result: dict[str, list[Path]] = {}

    # Component specs
    comp_dir = output_dir / "components"
    comp_dir.mkdir(parents=True, exist_ok=True)
    comp_paths: list[Path] = []
    for comp in model.entities.components:
        md = generate_component_spec(comp, model)
        path = comp_dir / f"{comp.id}.md"
        path.write_text(md)
        comp_paths.append(path)
    result["components"] = comp_paths

    # Diagrams
    diagrams_dir = output_dir / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    try:
        from architecture_model.docs.diagrams import generate_all_diagrams
        diagram_paths = generate_all_diagrams(model, diagrams_dir)
        if diagram_paths:
            result["diagrams"] = diagram_paths
    except (ImportError, AttributeError):
        pass

    # Dependency matrix
    dep_md = generate_dependency_matrix(model)
    dep_path = output_dir / "dependency-matrix.md"
    dep_path.write_text(dep_md)
    result["dependency_matrix"] = [dep_path]

    # ICD
    icd_md = generate_icd(model)
    icd_path = output_dir / "icd.md"
    icd_path.write_text(icd_md)
    result["icd"] = [icd_path]

    # Health report
    health_md = generate_health_report(model, manifest)
    health_path = output_dir / "health.md"
    health_path.write_text(health_md)
    result["health"] = [health_path]

    # System design
    sys_md = generate_system_design(model, manifest)
    sys_path = output_dir / "system-design.md"
    sys_path.write_text(sys_md)
    result["system_design"] = [sys_path]

    # Integration flows
    flows_md = generate_integration_flows(model)
    flows_path = output_dir / "integration-flows.md"
    flows_path.write_text(flows_md)
    result["integration_flows"] = [flows_path]

    # Drift report (only if previous model provided)
    if previous_model is not None:
        drift_md = generate_drift_report(previous_model, model)
        drift_path = output_dir / "drift.md"
        drift_path.write_text(drift_md)
        result["drift"] = [drift_path]

    # Index/README
    index_md = generate_index(model, result)
    readme_path = output_dir / "README.md"
    readme_path.write_text(index_md)
    result["index"] = [readme_path]

    return result
