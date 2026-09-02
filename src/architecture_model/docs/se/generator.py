"""SE document generation orchestrator."""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .changelog import Changelog
from .frontmatter import generate_frontmatter, parse_frontmatter, extract_section_hashes
from .detect import detect_project_docs

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel

# Registry: doc_key -> (module_name, function_name, display_name, filename)
STANDARD_DOCS: list[tuple[str, str, str, str]] = [
    ("conops", "conops", "ConOps", "conops.md"),
    ("functional_analysis", "functional_analysis", "Functional Analysis", "functional-analysis.md"),
    (
        "logical_architecture",
        "logical_architecture",
        "Logical Architecture",
        "logical-architecture.md",
    ),
    (
        "requirements_analysis",
        "requirements_analysis",
        "Requirements Analysis",
        "requirements-analysis.md",
    ),
    (
        "verification_validation",
        "verification_validation",
        "Verification & Validation",
        "verification-validation.md",
    ),
    ("operations_manual", "operations_manual", "Operations Manual", "operations-manual.md"),
    ("maintenance_manual", "maintenance_manual", "Maintenance Manual", "maintenance-manual.md"),
    ("use_cases", "use_cases", "Use Cases", "use-cases.md"),
    ("risk_assessment", "risk_assessment", "Risk Assessment", "risk-assessment.md"),
    ("interface_spec", "interface_spec", "Interface Specification", "interface-specification.md"),
    (
        "artifact_traceability",
        "artifact_traceability",
        "Artifact Traceability Map",
        "artifact-traceability.md",
    ),
]

PROJECT_DOCS: dict[str, tuple[str, str, str]] = {
    "api_reference": ("api_reference", "API Reference", "api-reference.md"),
    "data_model": ("data_model", "Data Model", "data-model.md"),
    "deployment_guide": ("deployment_guide", "Deployment Guide", "deployment-guide.md"),
    "security_analysis": ("security_analysis", "Security Analysis", "security-analysis.md"),
    "cli_reference": ("cli_reference", "CLI Reference", "cli-reference.md"),
    "plugin_guide": ("plugin_guide", "Plugin / Extension Guide", "plugin-guide.md"),
}

# Maps ModelDiff.affected_artifacts() names → STANDARD_DOCS keys
ARTIFACT_TO_DOC_KEY: dict[str, str | None] = {
    "use-cases": "use_cases",
    "functional-architecture": "functional_analysis",
    "logical-architecture": "logical_architecture",
    "icd": "interface_spec",
    "requirements-analysis": "requirements_analysis",
    "readme": None,  # Not an SE doc
}


def _model_hash(model: ArchitectureModel) -> str:
    """Compute a hash representing the model's current state."""
    content = f"{model.entity_count}-{model.relationship_count}"
    for c in model.entities.components:
        content += c.id
    return hashlib.md5(content.encode()).hexdigest()[:12]


def _import_generator(module_name: str):
    """Dynamically import a generator function."""
    import importlib

    mod = importlib.import_module(f"architecture_model.docs.se.{module_name}")
    # Convention: generate_<module_name>
    func_name = f"generate_{module_name}"
    return getattr(mod, func_name)


def generate_se_docs(
    model: ArchitectureModel,
    output_dir: Path,
    manifest: Any | None = None,
    *,
    doc_filter: list[str] | None = None,
    author: str = "architect_pipeline",
    reviews: list | None = None,
    enrichments: list | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Generate SE documents for a model.

    Args:
        model: The architecture model to generate docs from.
        output_dir: Directory to write docs to.
        manifest: Optional manifest for enrichment.
        doc_filter: If set, only generate these doc keys. None = all.
        author: Author name for changelog entries.

    Returns:
        Dict with 'generated' (list of paths), 'skipped', 'preserved_edits', 'errors'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    changelog = Changelog(output_dir / "changelog.yaml")
    mhash = _model_hash(model)

    system_name = (
        getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    )
    system_id = getattr(model.meta, "system_id", "") or "SYS-unknown"

    result: dict[str, Any] = {"generated": [], "skipped": [], "preserved_edits": [], "errors": []}
    native_views: dict[str, tuple[Any, str]] = {}
    if repo_root is not None:
        from architecture_model.core.diagram_renderer import render_diagram_panel
        from architecture_model.core.se_view_projectors import (
            project_conops,
            project_functional_architecture,
            project_logical_architecture,
            project_use_cases,
        )
        from architecture_model.core.view_context import ArchitectureViewContext
        from architecture_model.core.view_curation import load_viewer_curation

        context = ArchitectureViewContext.load(model, repo_root)
        curation = load_viewer_curation(repo_root, context)
        definitions = {
            "conops": (project_conops, curation.views.conops, "conops.svg"),
            "functional_analysis": (project_functional_architecture, curation.views.functional, "functional-architecture.svg"),
            "logical_architecture": (project_logical_architecture, curation.views.logical, "logical-architecture.svg"),
            "use_cases": (project_use_cases, curation.views.use_cases, "use-cases.svg"),
        }
        for key, (projector, view_curation, filename) in definitions.items():
            if doc_filter and key not in doc_filter:
                continue
            spec = projector(context, view_curation)
            svg_path = output_dir / filename
            svg_path.write_text(render_diagram_panel(spec).svg + "\n", encoding="utf-8")
            result["generated"].append(str(svg_path))
            native_views[key] = (spec, filename)

    # Determine which docs to generate
    to_generate: list[tuple[str, str, str, str]] = []  # (key, module, display, filename)

    for key, mod, display, fname in STANDARD_DOCS:
        if doc_filter and key not in doc_filter:
            continue
        to_generate.append((key, mod, display, fname))

    # Auto-detect project-specific docs
    detected = detect_project_docs(model)
    for pkey in detected:
        if doc_filter and pkey not in doc_filter:
            continue
        if pkey in PROJECT_DOCS:
            mod, display, fname = PROJECT_DOCS[pkey]
            to_generate.append((pkey, mod, display, fname))

    # Generate each document
    # Compute completeness for diagnostic banners
    _completeness_banner = ""
    try:
        from architecture_model.core.completeness import compute_completeness

        _comp_result = compute_completeness(model)
        if _comp_result.grade in ("D", "F"):
            gap_lines = "\n".join(f"> - {g}" for g in _comp_result.gaps[:4])
            _completeness_banner = (
                f"> **Model Completeness: {_comp_result.grade} ({_comp_result.score:.0f}%)**\n"
                f"> Some sections may be empty due to missing model entities.\n"
                f"{gap_lines}\n"
                f"> Run the extraction pipeline or manually add behaviors/interfaces/constraints.\n\n"
            )
    except Exception:
        pass

    for key, mod_name, display_name, filename in to_generate:
        try:
            gen_func = _import_generator(mod_name)
        except (ImportError, AttributeError):
            result["skipped"].append(f"{key}: generator not implemented")
            continue

        try:
            if mod_name == "artifact_traceability":
                md_content = gen_func(
                    model,
                    manifest,
                    reviews=reviews,
                    enrichments=enrichments,
                    repo_root=repo_root,
                )
            elif key in native_views:
                spec, svg_filename = native_views[key]
                md_content = gen_func(
                    model, manifest,
                    diagram_reference=f"![{spec.title}]({svg_filename})",
                )
            else:
                md_content = gen_func(model, manifest)
        except Exception as e:
            result["errors"].append(f"{key}: {e}")
            continue

        # Prepend completeness banner if model is semantically thin
        if _completeness_banner and md_content:
            md_content = _completeness_banner + md_content

        out_path = output_dir / filename

        # Check for existing file with user edits
        preserved: list[str] = []
        if out_path.exists():
            existing = out_path.read_text()
            _, existing_body = parse_frontmatter(existing)
            current_hashes = extract_section_hashes(existing_body)
            edited_sections = changelog.detect_edits(filename, current_hashes=current_hashes)

            if edited_sections:
                # Merge: keep user-edited sections, replace rest
                new_hashes = extract_section_hashes(md_content)
                merged = _merge_sections(existing_body, md_content, edited_sections)
                md_content = merged
                preserved = edited_sections
                result["preserved_edits"].extend([f"{filename}:{s}" for s in edited_sections])

        # Determine edition number
        cl_data = changelog.load()
        doc_entry = cl_data.get("documents", {}).get(filename)
        edition = len(doc_entry["editions"]) + 1 if doc_entry else 1

        # Add frontmatter
        fm = generate_frontmatter(
            document=display_name,
            system=system_name,
            system_id=system_id,
            model_hash=mhash,
            edition=edition,
        )
        full_doc = fm + "\n\n" + md_content

        out_path.write_text(full_doc)
        result["generated"].append(str(out_path))

        # Update changelog
        section_hashes = extract_section_hashes(md_content)
        if doc_entry:
            changelog.record_regeneration(
                filename,
                author=author,
                model_hash=mhash,
                preserved_sections=preserved,
                section_hashes=section_hashes,
            )
        else:
            changelog.record_generation(
                filename, author=author, model_hash=mhash, section_hashes=section_hashes
            )

    # Generate index
    _write_index(output_dir, to_generate, detected, result)

    return result


def _merge_sections(existing_body: str, new_body: str, preserve: list[str]) -> str:
    """Merge new content with existing, preserving user-edited sections."""
    existing_sections = _split_sections(existing_body)
    new_sections = _split_sections(new_body)

    merged_lines: list[str] = []
    # Start with content before first ##
    if new_sections.get("__preamble__"):
        merged_lines.append(new_sections["__preamble__"])

    for section_name in new_sections:
        if section_name == "__preamble__":
            continue
        if section_name in preserve and section_name in existing_sections:
            merged_lines.append(f"## {section_name}")
            merged_lines.append(existing_sections[section_name])
        else:
            merged_lines.append(f"## {section_name}")
            merged_lines.append(new_sections[section_name])

    return "\n".join(merged_lines)


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown into {section_name: content} dict."""
    sections: dict[str, str] = {}
    current: str | None = "__preamble__"
    lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        else:
            lines.append(line)

    if current is not None:
        sections[current] = "\n".join(lines).strip()

    return sections


def _write_index(
    output_dir: Path, generated: list[tuple], detected: list[str], result: dict
) -> None:
    """Write SE docs index file."""
    lines = ["# Systems Engineering Documents", ""]
    lines.append("## Standard SE Documents")
    lines.append("")
    for key, _, display, fname in generated:
        if key not in [
            d
            for d, *_ in [
                ("api_reference",),
                ("data_model",),
                ("deployment_guide",),
                ("security_analysis",),
                ("cli_reference",),
                ("plugin_guide",),
            ]
        ]:
            status = "generated" if str(output_dir / fname) in result["generated"] else "skipped"
            icon = "+" if status == "generated" else "-"
            lines.append(f"- [{icon}] [{display}]({fname})")
    lines.append("")

    if detected:
        lines.append("## Project-Specific Documents")
        lines.append("")
        for pkey in detected:
            if pkey in PROJECT_DOCS:
                _, display, fname = PROJECT_DOCS[pkey]
                lines.append(f"- [{display}]({fname})")
        lines.append("")

    (output_dir / "index.md").write_text("\n".join(lines))
    result["generated"].append(str(output_dir / "index.md"))


def regenerate_affected(
    old_model: "ArchitectureModel",
    new_model: "ArchitectureModel",
    output_dir: Path,
    *,
    manifest: Any | None = None,
    author: str = "diff_regen",
) -> dict[str, Any]:
    """Regenerate only the SE docs affected by model changes.

    Uses ModelDiff.affected_artifacts() to determine which docs are stale,
    then calls generate_se_docs() with a doc_filter.

    Returns:
        Dict with 'generated', 'affected_artifacts', 'reason', plus standard generate_se_docs keys.
    """
    from architecture_model.core.differ import diff_models

    diff = diff_models(old_model, new_model)

    if not diff.has_changes:
        return {
            "generated": [],
            "skipped": [],
            "preserved_edits": [],
            "errors": [],
            "affected_artifacts": [],
            "reason": "no_changes",
        }

    affected = diff.affected_artifacts()

    # Map artifact names to doc keys
    doc_keys = set()
    for artifact_name in affected:
        mapped = ARTIFACT_TO_DOC_KEY.get(artifact_name)
        if mapped is not None:
            doc_keys.add(mapped)

    if not doc_keys:
        return {
            "generated": [],
            "skipped": [],
            "preserved_edits": [],
            "errors": [],
            "affected_artifacts": sorted(affected),
            "reason": "no_mappable_docs",
        }

    result = generate_se_docs(
        new_model,
        output_dir,
        manifest=manifest,
        doc_filter=list(doc_keys),
        author=author,
    )
    result["affected_artifacts"] = sorted(affected)
    result["reason"] = "diff_triggered"
    return result
