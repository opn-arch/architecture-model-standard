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
