from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExportResult:
    """Result of building a flat export."""
    files: dict[str, str]  # filename -> content
    repo_name: str
    prefix: str
    total_size_bytes: int = 0


def derive_prefix(repo_name: str) -> str:
    """Derive a short prefix from repo name.
    
    Rules:
    - 'architecture-model-standard' -> 'model-std'
    - 'opencode-arch' -> 'opencode'
    - anything else: use as-is, lowercased, replacing _ with -
    """
    aliases = {
        "architecture-model-standard": "model-std",
        "opencode-arch": "opencode",
        "logs_db": "logs-db",
    }
    return aliases.get(repo_name, repo_name.lower().replace("_", "-"))


def build_flat_export(
    repo_path: Path,
    prefix: str | None = None,
    include_manifests: bool = True,
    include_module_specs: bool = True,
) -> ExportResult:
    """Build all flat files for a repo.
    
    Scans for existing artifacts and only includes files that are present.
    Each output file is named {prefix}--{category}.{ext}
    """
    repo_path = Path(repo_path)
    repo_name = repo_path.name
    if prefix is None:
        prefix = derive_prefix(repo_name)
    
    files: dict[str, str] = {}
    
    # Reference docs (always included)
    from architecture_model.export.reference import (
        generate_readme, generate_schema_reference,
        generate_api_reference, generate_custom_instructions,
    )
    files["README.md"] = generate_readme()
    files["SCHEMA.md"] = generate_schema_reference()
    files["API.md"] = generate_api_reference()
    
    # CONTEXT.md
    ctx = repo_path / "CONTEXT.md"
    if ctx.exists():
        files[f"{prefix}--CONTEXT.md"] = ctx.read_text()
    
    # Top-level model
    model_file = repo_path / ".architecture-model.yaml"
    if model_file.exists():
        files[f"{prefix}--model.yaml"] = model_file.read_text()
    
    # Sub-models (F-blocks + named)
    content = concat_submodels(repo_path)
    if content:
        files[f"{prefix}--submodels.yaml"] = content
    
    # Behavior sub-models
    content = concat_behavior_submodels(repo_path)
    if content:
        files[f"{prefix}--behavior-submodels.yaml"] = content
    
    # Component models (COMP-*)
    content = concat_component_models(repo_path)
    if content:
        files[f"{prefix}--component-models.yaml"] = content
    
    # Behavior specs (markdown)
    content = concat_behavior_specs(repo_path)
    if content:
        files[f"{prefix}--behavior-specs.md"] = content
    
    # Generated docs
    content = concat_docs(repo_path)
    if content:
        files[f"{prefix}--docs.md"] = content
    
    # Manifests
    if include_manifests:
        content = manifests_to_markdown(repo_path / ".architecture" / "manifests")
        if content:
            files[f"{prefix}--manifests.md"] = content
    
    # Module specs
    if include_module_specs:
        content = concat_module_specs(repo_path)
        if content:
            files[f"{prefix}--module-specs.md"] = content
    
    # Mermaid diagrams
    content = concat_diagrams(repo_path)
    if content:
        files[f"{prefix}--diagrams.md"] = content
    
    # Skills
    content = concat_skills(repo_path)
    if content:
        files[f"{prefix}--skills.md"] = content
    
    # Custom instructions (generated last with stats)
    stats = _gather_stats(repo_path, files, prefix)
    files["CUSTOM-INSTRUCTIONS.md"] = generate_custom_instructions(repo_name, stats)
    
    total = sum(len(v.encode()) for v in files.values())
    
    return ExportResult(
        files=files,
        repo_name=repo_name,
        prefix=prefix,
        total_size_bytes=total,
    )


def _gather_stats(repo_path: Path, files: dict, prefix: str) -> dict:
    """Gather stats for custom instructions."""
    stats: dict = {}
    model_file = repo_path / ".architecture-model.yaml"
    if model_file.exists():
        try:
            import yaml
            data = yaml.safe_load(model_file.read_text())
            entities = data.get("entities", {})
            stats["components"] = len(entities.get("components", []))
            stats["behaviors"] = len(entities.get("behaviors", []))
            stats["relationships"] = len(data.get("relationships", []))
        except Exception:
            pass
    stats["file_count"] = len(files)
    return stats


def concat_submodels(repo_path: Path) -> str | None:
    """Concatenate F-block and named sub-model YAMLs."""
    models_dir = repo_path / ".architecture-models"
    if not models_dir.exists():
        return None
    
    paths = []
    for d in sorted(models_dir.iterdir()):
        if d.is_dir() and d.name not in ("behaviors", "images", "functions"):
            model = d / ".architecture-model.yaml"
            if not model.exists():
                model = d / "model.yaml"
            if model.exists():
                paths.append(model)
    
    return _concat_yaml_files(paths) if paths else None


def concat_behavior_submodels(repo_path: Path) -> str | None:
    """Concatenate behavior sub-model YAMLs."""
    beh_dir = repo_path / ".architecture-models" / "behaviors"
    if not beh_dir.exists():
        return None
    paths = sorted(beh_dir.glob("*/model.yaml"))
    return _concat_yaml_files(paths) if paths else None


def concat_component_models(repo_path: Path) -> str | None:
    """Concatenate COMP-* sub-model YAMLs."""
    models_dir = repo_path / ".architecture-models"
    if not models_dir.exists():
        return None
    paths = sorted(models_dir.glob("COMP-*/model.yaml"))
    return _concat_yaml_files(paths) if paths else None


def concat_behavior_specs(repo_path: Path) -> str | None:
    """Concatenate behavior spec markdowns."""
    beh_doc_dir = repo_path / "docs" / "architecture" / "behaviors"
    if not beh_doc_dir.exists():
        return None
    paths = sorted(beh_doc_dir.glob("*.md"))
    return _concat_md_files(paths) if paths else None


def concat_docs(repo_path: Path) -> str | None:
    """Concatenate generated architecture docs (excluding behaviors subdir)."""
    doc_dir = repo_path / "docs" / "architecture"
    if not doc_dir.exists():
        return None
    # Only top-level .md files (behaviors are separate)
    paths = sorted(doc_dir.glob("*.md"))
    return _concat_md_files(paths) if paths else None


def concat_module_specs(repo_path: Path) -> str | None:
    """Concatenate per-component module YAML specs."""
    models_dir = repo_path / ".architecture-models"
    if not models_dir.exists():
        return None
    paths = sorted(models_dir.glob("COMP-*/modules/*.yaml"))
    if not paths:
        return None
    parts = []
    for p in paths:
        rel = _rel_from_models(p)
        content = p.read_text().strip()
        parts.append(f"<!-- FILE: {rel} -->\n\n```yaml\n{content}\n```")
    return "\n\n---\n\n".join(parts)


def concat_diagrams(repo_path: Path) -> str | None:
    """Concatenate Mermaid diagram files."""
    models_dir = repo_path / ".architecture-models"
    if not models_dir.exists():
        return None
    paths = sorted(models_dir.glob("**/*.mmd"))
    if not paths:
        return None
    parts = []
    for p in paths:
        rel = _rel_from_models(p)
        parts.append(f"<!-- FILE: {rel} -->\n\n```mermaid\n{p.read_text().strip()}\n```")
    return "\n\n---\n\n".join(parts)


def concat_skills(repo_path: Path) -> str | None:
    """Concatenate skill markdown files."""
    skills_dir = repo_path / "skills"
    if not skills_dir.exists():
        return None
    paths = sorted(skills_dir.glob("**/*.md"))
    if not paths:
        return None
    parts = []
    for p in paths:
        rel = p.relative_to(skills_dir)
        parts.append(f"<!-- FILE: skills/{rel} -->\n\n{p.read_text().strip()}")
    return "\n\n---\n\n".join(parts)


def manifests_to_markdown(manifest_dir: Path) -> str | None:
    """Convert JSON manifests to readable markdown summaries."""
    if not manifest_dir.exists():
        return None
    
    parts = []
    for jp in sorted(manifest_dir.glob("*.json")):
        try:
            data = json.loads(jp.read_text())
            block_id = jp.stem
            modules = data.get("modules", [])
            files_list = data.get("files", [])
            
            if isinstance(modules, list) and modules and isinstance(modules[0], dict):
                parts.append(f"## {block_id} ({len(modules)} modules)\n")
                for mod in modules[:50]:
                    if not isinstance(mod, dict):
                        continue
                    funcs = mod.get("functions", [])
                    if not isinstance(funcs, list):
                        funcs = []
                    func_names = [f.get("name", "?") for f in funcs if isinstance(f, dict)]
                    imports = mod.get("imports", [])
                    if not isinstance(imports, list):
                        imports = []
                    parts.append(f"### {mod.get('file', '?')} ({len(funcs)} functions)")
                    if func_names:
                        parts.append(f"Functions: {', '.join(func_names[:15])}")
                    internal = [
                        i for i in imports
                        if isinstance(i, str) and not i.startswith(("__", "os", "sys", "json", "re", "typing", "pathlib", "datetime", "logging", "collections", "functools", "dataclasses", "abc", "enum", "io", "time", "copy", "math", "hashlib", "base64", "urllib", "http", "socket", "threading", "subprocess", "shutil", "tempfile", "textwrap", "difflib", "html", "pydantic", "fastapi", "sqlalchemy", "starlette"))
                    ]
                    if internal:
                        parts.append(f"Internal imports: {', '.join(internal[:10])}")
                    parts.append("")
            elif isinstance(files_list, list) and files_list:
                parts.append(f"## {block_id} ({len(files_list)} files)\n")
                for f in files_list[:30]:
                    if isinstance(f, str):
                        parts.append(f"- {f}")
                    elif isinstance(f, dict):
                        parts.append(f"- {f.get('file', f.get('path', '?'))}")
                parts.append("")
            else:
                parts.append(f"## {block_id}\n")
                parts.append("")
        except Exception:
            continue
    
    return "\n".join(parts) if parts else None


def _concat_yaml_files(paths: list[Path]) -> str:
    """Concatenate YAML files with <!-- FILE --> headers."""
    parts = []
    for p in paths:
        rel = _rel_from_models(p)
        header = rel.split("/")[0]
        content = p.read_text().strip()
        parts.append(f"<!-- FILE: .architecture-models/{rel} -->\n# Sub-Model: {header}\n\n{content}")
    return "\n\n---\n\n".join(parts)


def _concat_md_files(paths: list[Path]) -> str:
    """Concatenate markdown files with <!-- FILE --> headers."""
    parts = []
    for p in paths:
        content = p.read_text().strip()
        parts.append(f"<!-- FILE: {p.name} -->\n\n{content}")
    return "\n\n---\n\n".join(parts)


def _rel_from_models(p: Path) -> str:
    """Get relative path from .architecture-models/."""
    s = str(p)
    marker = "/.architecture-models/"
    idx = s.find(marker)
    if idx >= 0:
        return s[idx + len(marker):]
    return p.name
