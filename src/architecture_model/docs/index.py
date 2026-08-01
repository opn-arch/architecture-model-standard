"""Generate index/README for documentation."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_index(model: "ArchitectureModel", doc_paths: dict[str, list[Path]]) -> str:
    """Generate README.md index linking to all docs."""
    lines = [f"# {model.meta.project} \u2014 Architecture Documentation", ""]
    components = model.entities.components if hasattr(model.entities, 'components') else []
    lines.append(f"**Schema Version:** {model.meta.schema_version}")
    lines.append(f"**Components:** {len(components)}")
    avg_conf = sum(c.confidence or 0 for c in components) / max(len(components), 1)
    lines.append(f"**Avg Confidence:** {avg_conf:.0%}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if doc_paths.get("diagrams"):
        lines.append("## Diagrams")
        lines.append("")
        for p in doc_paths["diagrams"]:
            lines.append(f"- [{p.stem}](diagrams/{p.name})")
        lines.append("")

    if doc_paths.get("components"):
        lines.append("## Component Specifications")
        lines.append("")
        for p in sorted(doc_paths["components"]):
            comp_name = p.stem
            for c in components:
                if c.id == p.stem:
                    comp_name = f"{c.name} ({c.id})"
                    break
            lines.append(f"- [{comp_name}](components/{p.name})")
        lines.append("")

    other = [("dependency_matrix", "Dependency Matrix", "dependency-matrix.md"),
             ("icd", "Interface Control Document", "icd.md"),
             ("health", "Health Report", "health.md"),
             ("drift", "Drift Report", "drift.md")]
    lines.append("## Reference Documents")
    lines.append("")
    for key, title, filename in other:
        if doc_paths.get(key):
            lines.append(f"- [{title}]({filename})")
    lines.append("")
    lines.append("---")
    lines.append("*Generated deterministically from architecture model.*")
    lines.append("")
    return "\n".join(lines)
