"""
Merger: Merge manifest facts into an existing architecture model.

The manifest provides code-grounded facts (file counts, module names, import graphs).
The model provides architectural decisions (what things mean, how they relate).

Merger SUPPLEMENTS the model with manifest data — it never overwrites architectural
decisions. It adds source_file/source_line provenance and fills in component file lists.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from architecture_model.utils.discovery import (
    EXCLUDED_DIRS,
    discover_source_files,
    discover_test_files,
)

from .types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Constant,
    Entities,
    FunctionSignature,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
    TestContract,
)


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
        source_block_dirs = config.source_block_dir_map
    except Exception:
        source_block_dirs = {}
        config = None

    for mod in modules:
        path = mod.get("file", mod.get("path", ""))
        loc = mod.get("line_count", mod.get("loc", 0))
        filename = path.rsplit("/", 1)[-1] if "/" in path else path

        if loc < 400:
            continue
        if filename in existing_files or path in existing_files:
            continue

        # Determine source_block
        source_block = ""
        for prefix, fb in source_block_dirs.items():
            if path.startswith(prefix):
                source_block = fb
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
                source_block=source_block,
                files=[path],
                source_file=path,
                description=f"Auto-discovered from manifest ({loc} LOC)",
            )
        )

    # Wire realizes relationships for newly added components
    source_block_to_cap = {cap.source_block: cap.id for cap in model.entities.capabilities}
    existing_rels = {(r.from_id, r.to_id, r.type) for r in model.relationships}
    for comp in model.entities.components:
        if comp.source_block and comp.source_block in source_block_to_cap:
            key = (comp.id, source_block_to_cap[comp.source_block], RelationType.REALIZES)
            if key not in existing_rels:
                model.relationships.append(
                    Relationship(
                        type=RelationType.REALIZES,
                        from_id=comp.id,
                        to_id=source_block_to_cap[comp.source_block],
                        description=f"{comp.name} realizes {comp.source_block}",
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
    """Enrich depends-on relationships with imported symbols from manifest.

    For each depends-on relationship, finds the source module's imports_detailed
    that reference the target module, and populates Relationship.imports.
    """
    for rel in model.relationships:
        if rel.type != RelationType.DEPENDS_ON:
            continue

        # Resolve from/to component stems
        from_stem = _component_stem(rel.from_id, model)
        to_stem = _component_stem(rel.to_id, model)

        if not from_stem or not to_stem:
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

        if imported_symbols:
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


# ---------------------------------------------------------------------------
# Compaction: reduce enriched model size for LLM context limits
# ---------------------------------------------------------------------------

# Maximum members (methods) per symbol before truncation
_MAX_MEMBERS_PER_SYMBOL = 8
# Maximum functions per component before truncation
_MAX_FUNCTIONS_PER_COMPONENT = 12
# Maximum symbols per component before truncation
_MAX_SYMBOLS_PER_COMPONENT = 6
# Target YAML char budget (rough estimate — 7B models struggle above ~12K)
_YAML_CHAR_BUDGET = 12000


def compact_for_generation(model: ArchitectureModel) -> ArchitectureModel:
    """Compact an enriched model for LLM code generation.

    Truncates symbol members and component functions when the model is too
    large for a 7B model's effective context. Preserves structure (all
    components, all symbol names by kind) but limits detail per entity.

    The model is mutated in-place and returned.

    Strategy:
    - Cap symbols per component to _MAX_SYMBOLS_PER_COMPONENT (keep by importance)
    - Cap members per symbol to _MAX_MEMBERS_PER_SYMBOL (keep __init__ + public)
    - Cap functions per component to _MAX_FUNCTIONS_PER_COMPONENT
    - Prioritize: __init__ first, then alphabetical for determinism
    - Excess symbols are listed as names-only in a comment field
    - For very large models (>16 components), apply stricter per-component limits
    """
    import copy
    import yaml

    model = copy.deepcopy(model)

    # Adaptive limits based on model size
    n_components = len(model.entities.components)
    if n_components > 15:
        max_symbols = 3
        max_members = 4
        max_functions = 5
    elif n_components > 10:
        max_symbols = 4
        max_members = 6
        max_functions = 8
    else:
        max_symbols = _MAX_SYMBOLS_PER_COMPONENT
        max_members = _MAX_MEMBERS_PER_SYMBOL
        max_functions = _MAX_FUNCTIONS_PER_COMPONENT

    for comp in model.entities.components:
        # Compact symbols — keep top N by member count (most important classes)
        if len(comp.symbols) > max_symbols:
            # Sort by member count descending (most substantial classes first)
            ranked = sorted(comp.symbols, key=lambda s: len(s.members), reverse=True)
            comp.symbols = ranked[:max_symbols]

        # Compact symbol members
        for sym in comp.symbols:
            if len(sym.members) > max_members:
                # Prioritize __init__, then sort remaining alphabetically
                has_init = "__init__" in sym.members
                others = sorted(m for m in sym.members if m != "__init__")
                cap = max_members - (1 if has_init else 0)
                kept = others[:cap]
                if has_init:
                    kept = ["__init__"] + kept
                sym.members = kept

        # Compact functions
        if len(comp.functions) > max_functions:
            comp.functions = sorted(comp.functions)[:max_functions]

    return model


# ---------------------------------------------------------------------------
# Compose Enriched Model (from raw source code)
# ---------------------------------------------------------------------------

# Filenames to exclude
_EXCLUDED_FILES = frozenset({"setup.py", "conftest.py"})


def _trace_init_reexports(init_path: Path) -> set[str]:
    """Parse an __init__.py and return stems of modules it re-exports from.

    Handles:
      - from .core import MyClass      → {"core"}
      - from .utils import helper      → {"utils"}
      - from .sub.impl import thing    → {"impl"}
      - from . import something        → {"something"}
    """
    try:
        source = init_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(init_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()

    stems: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0 and node.module:
                # Relative import: from .core import X → "core"
                # from .sub.impl import X → "impl" (last part)
                parts = node.module.split(".")
                stems.add(parts[-1])
            elif node.level > 0 and not node.module:
                # from . import something → each alias name is a module
                for alias in (node.names or []):
                    stems.add(alias.name)
    return stems


def _build_package_dirs(project_root: Path) -> dict[str, Path]:
    """Build mapping of package directory names → their __init__.py paths.

    Skips test directories and virtual environments. Handles nested packages.
    """
    package_dirs: dict[str, Path] = {}
    for init_file in sorted(project_root.rglob("__init__.py")):
        pkg_dir = init_file.parent
        # Skip excluded directories
        rel_parts = pkg_dir.relative_to(project_root).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        package_dirs[pkg_dir.name] = init_file
    return package_dirs


def _map_tests_to_sources(
    test_files: list[Path],
    source_stems: set[str],
    project_root: Path,
) -> dict[str, list[Path]]:
    """Map source file stems to the test files that cover them.

    Parses each test file's imports to find which source modules it tests.
    When an import references a package directory (not a source file stem),
    traces through that package's __init__.py to find re-exported module stems.

    Returns: {source_stem: [test_file_paths]}
    """
    mapping: dict[str, list[Path]] = {}

    # Build package directory lookup for __init__.py tracing
    package_dirs = _build_package_dirs(project_root)

    for test_file in test_files:
        try:
            source = test_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(test_file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        # Extract imported module names
        imported_stems: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                # e.g., "from colorama.ansi import code_to_chars" → "ansi"
                parts = node.module.split(".")
                for part in parts:
                    if part in source_stems:
                        imported_stems.add(part)
                    elif part in package_dirs:
                        # Part is a package dir — trace __init__.py re-exports
                        reexported = _trace_init_reexports(package_dirs[part])
                        for reexport_stem in reexported:
                            if reexport_stem in source_stems:
                                imported_stems.add(reexport_stem)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    for part in parts:
                        if part in source_stems:
                            imported_stems.add(part)

        for stem in imported_stems:
            mapping.setdefault(stem, []).append(test_file)

    return mapping


def _build_constants_for_file(tree: ast.Module) -> list[Constant]:
    """Build Constant list from module constants, class attributes, and module assignments."""
    from architecture_model.manifest.scanner import (
        _extract_class_attributes,
        _extract_module_assignments,
        _extract_module_constants,
    )

    constants: list[Constant] = []

    # Module-level constants (UPPER_CASE = literal)
    for name, value in _extract_module_constants(tree).items():
        constants.append(Constant(name=name, value=value, context="module-level constant"))

    # Class attributes
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for attr_name, attr_value in _extract_class_attributes(node).items():
                constants.append(
                    Constant(
                        name=attr_name,
                        value=attr_value,
                        context=f"class attribute of {node.name}",
                    )
                )

    # Module-level assignments (non-constant, non-literal)
    for name, expr in _extract_module_assignments(tree).items():
        constants.append(Constant(name=name, value=expr, context="module-level instance"))

    return constants


def compose_enriched_model(project_root: Path) -> ArchitectureModel:
    """Compose a fully-enriched ArchitectureModel from source code.

    Scans all source files in the project, extracting:
    - Module constants, class attributes, module assignments → Constant objects
    - Function signatures with body hints → FunctionSignature objects
    - Test contracts from matching test files → TestContract objects

    Each source module becomes a Component in the resulting model.

    Args:
        project_root: Root directory of the project to scan.

    Returns:
        An ArchitectureModel with one Component per source file, enriched
        with constants, signatures, and test contracts.
    """
    from architecture_model.manifest.body_hints import extract_file_hints
    from architecture_model.manifest.scanner import _parse_file_ast
    from architecture_model.manifest.test_analyzer import analyze_test_file

    # Discover files
    source_files = discover_source_files(project_root)
    test_files = discover_test_files(project_root)

    # Build stem set for test mapping
    source_stems = {f.stem for f in source_files}

    # Map tests to sources
    test_mapping = _map_tests_to_sources(test_files, source_stems, project_root)

    # Build components
    components: list[Component] = []

    for src_file in source_files:
        stem = src_file.stem
        rel_path = str(src_file.relative_to(project_root))

        # Parse AST
        tree = _parse_file_ast(src_file)
        if tree is None:
            continue

        # Constants
        constants = _build_constants_for_file(tree)

        # Signatures with body hints
        try:
            signatures = extract_file_hints(src_file)
        except Exception:
            signatures = []

        # Test contracts from matched test files
        test_contracts: list[TestContract] = []
        matched_test_files = test_mapping.get(stem, [])
        for tf in matched_test_files:
            try:
                result = analyze_test_file(tf)
                test_contracts.extend(result.contracts)
            except Exception:
                continue

        comp = Component(
            id=f"comp-{stem}",
            name=stem,
            status=Status.ACTIVE,
            files=[rel_path],
            kind=ComponentKind.MODULE,
            constants=constants,
            signatures=signatures,
            test_contracts=test_contracts,
        )
        components.append(comp)

    # Determine project name from root dir
    project_name = project_root.name

    meta = ModelMeta(
        schema_version="1.4",
        project=project_name,
    )

    entities = Entities(components=components)

    return ArchitectureModel(
        meta=meta,
        entities=entities,
        relationships=[],
    )
