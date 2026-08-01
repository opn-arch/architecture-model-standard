"""Documentation generator orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from architecture_model.docs.component_spec import generate_component_spec

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

    # Stub calls for future generators
    _try_generate("architecture_model.docs.diagrams", "generate_diagrams", model, output_dir, result)
    _try_generate("architecture_model.docs.dependency_matrix", "generate_dependency_matrix", model, output_dir, result)
    _try_generate("architecture_model.docs.icd", "generate_icd", model, output_dir, result)
    _try_generate("architecture_model.docs.health", "generate_health", model, output_dir, result)
    _try_generate("architecture_model.docs.drift", "generate_drift", model, output_dir, result)
    _try_generate("architecture_model.docs.index", "generate_index", model, output_dir, result)

    return result


def _try_generate(module_name: str, func_name: str, model, output_dir: Path, result: dict):
    """Try to import and call a generator module, skip if not available."""
    try:
        import importlib
        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)
        func(model, output_dir, result)
    except (ImportError, AttributeError):
        pass
