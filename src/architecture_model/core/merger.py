"""
Merger: Merge manifest facts into an existing architecture model.

The manifest provides code-grounded facts (file counts, module names, import graphs).
The model provides architectural decisions (what things mean, how they relate).

Merger SUPPLEMENTS the model with manifest data — it never overwrites architectural
decisions. It adds source_file/source_line provenance and fills in component file lists.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import ArchitectureModel, Component, Relationship, RelationType, Status, Symbol, SymbolKind


def merge_manifest(
    model: ArchitectureModel,
    manifest_path: str | Path,
    project_root: str | Path | None = None,
) -> ArchitectureModel:
    """
    Merge manifest data into the architecture model (in-place mutation).

    What gets merged:
    - Component file lists get enriched with manifest-discovered files.
    - Layers get directory lists from manifest module scan.
    - Meta gets manifest_hash updated.

    What does NOT get overwritten:
    - Entity names, descriptions, status markers.
    - Relationships (these are architectural decisions).
    - Capabilities, behaviors, constraints (model-level truth).

    Args:
        model: The architecture model to enrich.
        manifest_path: Path to the reality-manifest.json file.
        project_root: Root of the consumer project (for config lookup).
                      Defaults to manifest_path's grandparent (output/{project}/manifest → root).

    Returns the same model instance (mutated).
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return model

    # Resolve project root for config loading
    if project_root is None:
        # Heuristic: manifest is at output/{project}/reality-manifest.json → root is ../..
        project_root = manifest_path.resolve().parent.parent.parent
    else:
        project_root = Path(project_root).resolve()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Update manifest hash
    import hashlib

    content = manifest_path.read_bytes()
    model.meta.manifest_hash = hashlib.sha256(content).hexdigest()[:16]

    # Enrich layers with directory info
    _merge_layer_directories(model, manifest, project_root)

    # Enrich components with file provenance
    _merge_component_files(model, manifest)

    # Add discovered components not yet in model
    _add_missing_components(model, manifest, project_root)

    return model


def _merge_layer_directories(model: ArchitectureModel, manifest: dict, project_root: Path) -> None:
    """Map manifest directory categories to model layers."""
    modules = manifest.get("modules", [])
    if not modules:
        return

    # Load layer-dir mapping from config
    try:
        from architecture_model.config.loader import get_config

        config = get_config(project_root)
        layer_dir_map = config.layer_dir_map
    except Exception:
        # Fallback: derive from model layer IDs
        layer_dir_map = {}

    for layer in model.entities.layers:
        if layer.id in layer_dir_map:
            layer.directories = layer_dir_map[layer.id]


def _merge_component_files(model: ArchitectureModel, manifest: dict) -> None:
    """Add file provenance to components that match manifest modules."""
    modules = manifest.get("modules", [])
    if not modules:
        return

    # Build filename → path lookup (manifest uses 'file' key)
    file_lookup: dict[str, str] = {}
    for mod in modules:
        path = mod.get("file", mod.get("path", ""))
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        file_lookup[filename] = path

    for comp in model.entities.components:
        if comp.files:
            # Try to resolve full paths
            resolved: list[str] = []
            for f in comp.files:
                if f in file_lookup:
                    resolved.append(file_lookup[f])
                else:
                    resolved.append(f)
            comp.files = resolved
        elif comp.name in file_lookup:
            comp.files = [file_lookup[comp.name]]
            comp.source_file = file_lookup[comp.name]


def _add_missing_components(model: ArchitectureModel, manifest: dict, project_root: Path) -> None:
    """
    Add high-LOC modules from manifest that aren't yet represented as components.

    Only adds modules with >400 LOC that aren't already tracked.
    """
    modules = manifest.get("modules", [])
    if not modules:
        return

    existing_files: set[str] = set()
    for comp in model.entities.components:
        for f in comp.files:
            existing_files.add(f)
            # Also add just filename
            existing_files.add(f.rsplit("/", 1)[-1] if "/" in f else f)

    # F-block directory heuristics — loaded from config
    try:
        from architecture_model.config.loader import get_config

        config = get_config(project_root)
        fblock_dirs = config.fblock_dir_map
    except Exception:
        fblock_dirs = {}
        config = None

    for mod in modules:
        path = mod.get("file", mod.get("path", ""))
        loc = mod.get("line_count", mod.get("loc", 0))
        filename = path.rsplit("/", 1)[-1] if "/" in path else path

        if loc < 400:
            continue
        if filename in existing_files or path in existing_files:
            continue

        # Determine f_block
        f_block = ""
        for prefix, fb in fblock_dirs.items():
            if path.startswith(prefix):
                f_block = fb
                break

        # Determine layer from config
        layer = ""
        try:
            layer_dir_map = config.layer_dir_map
        except Exception:
            layer_dir_map = {}
        for layer_id, dirs in layer_dir_map.items():
            for d in dirs:
                if path.startswith(d):
                    layer = layer_id
                    break
            if layer:
                break

        comp_id = path.replace("/", "-").replace(".py", "").replace("_", "-")

        model.entities.components.append(
            Component(
                id=comp_id,
                name=filename,
                status=Status.ACTIVE,
                layer=layer,
                f_block=f_block,
                files=[path],
                source_file=path,
                description=f"Auto-discovered from manifest ({loc} LOC)",
            )
        )

    # Wire realizes relationships for newly added components
    fblock_to_cap = {cap.f_block: cap.id for cap in model.entities.capabilities}
    existing_rels = {(r.from_id, r.to_id, r.type) for r in model.relationships}
    for comp in model.entities.components:
        if comp.f_block and comp.f_block in fblock_to_cap:
            key = (comp.id, fblock_to_cap[comp.f_block], RelationType.REALIZES)
            if key not in existing_rels:
                model.relationships.append(
                    Relationship(
                        type=RelationType.REALIZES,
                        from_id=comp.id,
                        to_id=fblock_to_cap[comp.f_block],
                        description=f"{comp.name} realizes {comp.f_block}",
                    )
                )
                existing_rels.add(key)


# ---------------------------------------------------------------------------
# Enrichment from manifest (AST ground-truth correction)
# ---------------------------------------------------------------------------


@dataclass
class EnrichmentResult:
    """Result of enrich_from_manifest — model plus accuracy metrics."""

    _model: ArchitectureModel
    naming_accuracy: float = 1.0

    @property
    def model(self) -> ArchitectureModel:
        return self._model

    @property
    def entities(self):
        return self._model.entities

    @property
    def relationships(self):
        return self._model.relationships

    @property
    def meta(self):
        return self._model.meta


def enrich_from_manifest(model: ArchitectureModel, manifest: dict) -> EnrichmentResult:
    """
    Enrich an ArchitectureModel with ground-truth symbols and functions from an AST manifest.

    Replaces component symbols/functions with manifest-derived data, enriches
    relationship imports, and computes naming accuracy vs prior predictions.

    Args:
        model: The architecture model to enrich (mutated in-place).
        manifest: Manifest dict as produced by the manifest generator.

    Returns:
        EnrichmentResult with the enriched model and naming_accuracy score.
    """
    modules = manifest.get("modules", [])
    interfaces = manifest.get("interfaces", [])

    # Build module lookup: filename stem → module dict
    stem_to_module: dict[str, dict] = {}
    for mod in modules:
        path = mod.get("file", "")
        stem = Path(path).stem  # e.g., "dotenv/parser.py" → "parser"
        stem_to_module[stem] = mod

    # Track naming accuracy
    total_predicted = 0
    total_matched = 0

    # Enrich each component
    for comp in model.entities.components:
        matched_module = _find_matching_module(comp, stem_to_module)
        if matched_module is None:
            continue

        # Compute naming accuracy before replacing
        if comp.symbols:
            manifest_names = {cls["name"] for cls in matched_module.get("classes", [])}
            predicted_names = [s.name for s in comp.symbols]
            total_predicted += len(predicted_names)
            total_matched += sum(1 for n in predicted_names if n in manifest_names)

        # Replace symbols with ground truth
        comp.symbols = _build_symbols(matched_module.get("classes", []))

        # Replace functions with ground truth
        comp.functions = _extract_function_names(matched_module.get("functions", []))

    # Enrich relationship imports
    _enrich_relationship_imports(model, modules, interfaces, stem_to_module)

    # Compute overall naming accuracy
    if total_predicted == 0:
        naming_accuracy = 1.0
    else:
        naming_accuracy = total_matched / total_predicted

    return EnrichmentResult(_model=model, naming_accuracy=naming_accuracy)


def _find_matching_module(comp: Component, stem_to_module: dict[str, dict]) -> dict | None:
    """Find the manifest module matching a component by name or id stem."""
    # Try component name directly
    if comp.name in stem_to_module:
        return stem_to_module[comp.name]

    # Try id stem: strip "comp-" prefix
    id_stem = comp.id
    if id_stem.startswith("comp-"):
        id_stem = id_stem[5:]

    if id_stem in stem_to_module:
        return stem_to_module[id_stem]

    return None


def _infer_symbol_kind(cls: dict) -> SymbolKind:
    """Infer SymbolKind from class metadata."""
    bases = cls.get("bases", [])
    decorators = cls.get("decorators", [])
    is_abstract = cls.get("is_abstract", False)

    # Protocol: is_abstract or ABC/Protocol in bases
    if is_abstract or any(b in ("ABC", "Protocol") for b in bases):
        return SymbolKind.PROTOCOL

    # Exception: any base containing "Exception" or "Error"
    if any("Exception" in b or "Error" in b for b in bases):
        return SymbolKind.EXCEPTION

    # Dataclass: "dataclass" in decorators
    if any("dataclass" in d for d in decorators):
        return SymbolKind.DATACLASS

    return SymbolKind.CLASS


def _filter_methods(methods: list[str]) -> list[str]:
    """Keep public methods + __init__, skip other dunders and private methods."""
    result = []
    for m in methods:
        if m == "__init__":
            result.append(m)
        elif m.startswith("__") and m.endswith("__"):
            # Other dunder → skip
            continue
        elif m.startswith("_"):
            # Private → skip
            continue
        else:
            result.append(m)
    return result


def _filter_supers(bases: list[str]) -> list[str]:
    """Filter out 'object' from bases."""
    return [b for b in bases if b != "object"]


def _build_symbols(classes: list[dict]) -> list[Symbol]:
    """Convert manifest class dicts to Symbol instances."""
    symbols = []
    for cls in classes:
        kind = _infer_symbol_kind(cls)
        members = _filter_methods(cls.get("methods", []))
        supers = _filter_supers(cls.get("bases", []))
        symbols.append(Symbol(
            name=cls["name"],
            kind=kind,
            members=members,
            supers=supers,
        ))
    return symbols


def _extract_function_names(signatures: list[str]) -> list[str]:
    """Extract function names from signature strings like 'make_parser(stream) -> Parser'."""
    names = []
    for sig in signatures:
        # Extract name before first '('
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)", sig)
        if match:
            names.append(match.group(1))
    return names


def _enrich_relationship_imports(
    model: ArchitectureModel,
    modules: list[dict],
    interfaces: list[dict],
    stem_to_module: dict[str, dict],
) -> None:
    """Enrich depends-on relationships with imported symbols from manifest."""
    # Build file→stem lookup for interface matching
    file_to_stem: dict[str, str] = {}
    for mod in modules:
        path = mod.get("file", "")
        stem = Path(path).stem
        file_to_stem[path] = stem

    # Build interface lookup: (source_stem, target_stem) → True
    interface_pairs: set[tuple[str, str]] = set()
    for iface in interfaces:
        src_stem = file_to_stem.get(iface.get("source", ""), "")
        tgt_stem = file_to_stem.get(iface.get("target", ""), "")
        if src_stem and tgt_stem:
            interface_pairs.add((src_stem, tgt_stem))

    for rel in model.relationships:
        if rel.type != RelationType.DEPENDS_ON:
            continue

        # Resolve from/to component stems
        from_stem = _component_stem(rel.from_id, model)
        to_stem = _component_stem(rel.to_id, model)

        if not from_stem or not to_stem:
            continue

        # Check if interface exists between these
        if (from_stem, to_stem) not in interface_pairs:
            continue

        # Find source module and collect imports targeting to_stem
        source_mod = stem_to_module.get(from_stem)
        if not source_mod:
            continue

        imports_detailed = source_mod.get("imports_detailed", [])
        imported_symbols: list[str] = []
        for imp in imports_detailed:
            imp_module = imp.get("module", "")
            # Match if import module name matches target stem
            if imp_module == to_stem or imp_module.endswith(f".{to_stem}"):
                imported_symbols.extend(imp.get("symbols", []))

        rel.imports = imported_symbols


def _component_stem(comp_id: str, model: ArchitectureModel) -> str:
    """Get the matching stem for a component id."""
    # Try finding the component to get its name
    for comp in model.entities.components:
        if comp.id == comp_id:
            # Use component name if it looks like a stem
            name = comp.name
            if name and not " " in name:
                return name
            # Fallback to id stem
            break

    # Strip comp- prefix from id
    stem = comp_id
    if stem.startswith("comp-"):
        stem = stem[5:]
    return stem
