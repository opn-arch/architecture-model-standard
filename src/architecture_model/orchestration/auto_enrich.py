"""Auto-enrichment of architecture model components from manifest data.

Populates Component fields (signatures, symbols, constants, contract, pattern,
responsibilities) by matching component files to manifest modules.
"""

from __future__ import annotations

import re
from typing import Any

from architecture_model.core.types import (
    Behavior,
    Component,
    Constant,
    FunctionSignature,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
)
from architecture_model.manifest.types import ClassInfo, FunctionInfo, Manifest, ModuleInfo
from architecture_model.monitoring import monitored
from architecture_model.patterns import load_patterns

# Decorators that indicate a trigger
_TRIGGER_DECORATORS = re.compile(
    r"(route|get|post|put|delete|patch|"
    r"event|signal|handler|listen|subscribe|"
    r"on_event|on_message|webhook|cron|scheduled)",
    re.IGNORECASE,
)


def _parse_signature(name: str, func: FunctionInfo) -> FunctionSignature:
    """Parse a FunctionInfo into a FunctionSignature."""
    sig = func.signature
    params: list[str] = []
    returns = ""

    # Extract params and return type from "(a: int, b: int) -> int" or "name(a: int) -> int"
    m = re.match(r"(?:\w+)?\((.*?)\)\s*(?:->\s*(.+))?", sig)
    if m:
        param_str = m.group(1).strip()
        if param_str:
            params = [p.strip() for p in param_str.split(",")]
        returns = (m.group(2) or "").strip()

    return FunctionSignature(
        name=name,
        params=params,
        returns=returns,
        decorators=[],
        body_hint=func.docstring or "",
    )


def _detect_symbol_kind(cls: ClassInfo) -> SymbolKind:
    """Detect SymbolKind from class decorators and bases."""
    all_text = " ".join(cls.decorators + cls.bases).lower()
    if "dataclass" in all_text:
        return SymbolKind.DATACLASS
    if "exception" in all_text or "error" in all_text:
        return SymbolKind.EXCEPTION
    if "protocol" in all_text:
        return SymbolKind.PROTOCOL
    if "enum" in all_text:
        return SymbolKind.ENUM
    if "abc" in all_text or cls.is_abstract:
        return SymbolKind.INTERFACE
    return SymbolKind.CLASS


def _class_to_symbol(cls: ClassInfo) -> Symbol:
    """Convert a ClassInfo to a Symbol."""
    return Symbol(
        name=cls.name,
        kind=_detect_symbol_kind(cls),
        members=list(cls.methods),
        supers=list(cls.bases),
    )


def _extract_contract(module: ModuleInfo, classes: list[ClassInfo]) -> str:
    """Infer contract from first sentence of module or class docstring."""
    for source in [module.docstring] + [None]:  # try module first
        pass
    # Try module docstring
    if module.docstring:
        first = module.docstring.strip().split("\n")[0]
        # Get first sentence
        sentence = re.split(r"[.!?]", first)[0].strip()
        if sentence:
            return sentence
    # Try first class docstring (not available in ClassInfo, skip)
    return ""


def _classify_pattern(modules: list[ModuleInfo], threshold: int = 2) -> str:
    """Classify component pattern using pattern catalog indicators."""
    catalog = load_patterns()

    # Collect all names (functions, classes, methods) from modules
    names: list[str] = []
    for mod in modules:
        for f in mod.functions:
            names.append(f.name.lower())
        for c in mod.classes:
            names.append(c.name.lower())
            for m in c.methods:
                names.append(m.lower())
            for d in c.decorators:
                names.append(d.lower())

    name_text = " ".join(names)

    best_pattern = ""
    best_count = 0

    for pattern_name, pattern_info in catalog.items():
        if not isinstance(pattern_info, dict):
            continue
        indicators = pattern_info.get("indicators", [])
        match_count = 0
        for indicator in indicators:
            # Strip wildcards and lowercase
            clean = indicator.lower().replace("*", "").replace("class ", "").replace("@", "").strip()
            if not clean:
                continue
            if clean in name_text:
                match_count += 1
        if match_count >= threshold and match_count > best_count:
            best_count = match_count
            best_pattern = pattern_name

    return best_pattern


def _extract_responsibilities(classes: list[ClassInfo]) -> list[str]:
    """Extract responsibilities from class method names."""
    responsibilities: list[str] = []
    for cls in classes:
        for method in cls.methods:
            if method.startswith("_"):
                continue
            # Convert method name to readable responsibility
            readable = method.replace("_", " ")
            responsibilities.append(readable)
    return responsibilities


@monitored("orchestration.auto_enrich")
def enrich_from_manifest(model: Any, manifest: Manifest) -> None:
    """Enrich model components in-place from manifest data.

    Populates signatures, symbols, constants, contract, pattern, and
    responsibilities for each component by matching files to manifest modules.
    """
    # Build file -> ModuleInfo lookup
    file_lookup: dict[str, ModuleInfo] = {}
    for mod in manifest.modules:
        file_lookup[mod.file] = mod

    components = (
        model.entities.components
        if hasattr(model.entities, "components")
        else model.entities.get("components", [])
        if hasattr(model.entities, "get")
        else []
    )

    for comp in components:
        if not isinstance(comp, Component):
            continue

        # Gather matching modules for this component's files
        matched_modules: list[ModuleInfo] = []
        for f in comp.files:
            if f in file_lookup:
                matched_modules.append(file_lookup[f])

        if not matched_modules:
            continue

        # Extract signatures (from top-level functions AND class methods)
        if not comp.signatures:
            sigs: list[FunctionSignature] = []
            for mod in matched_modules:
                for func in mod.functions:
                    sigs.append(_parse_signature(func.name, func))
                # Also create signatures from class methods
                for cls in mod.classes:
                    if cls.method_details:
                        # Use full typed signatures from method_details
                        for mfunc in cls.method_details:
                            if not mfunc.name.startswith("_"):
                                sigs.append(_parse_signature(mfunc.name, mfunc))
                    else:
                        # Fallback: name-only signatures
                        for method_name in cls.methods:
                            if not method_name.startswith("_"):
                                sigs.append(FunctionSignature(
                                    name=method_name, params=["self"], returns="",
                                    decorators=[], body_hint="",
                                ))
            comp.signatures = sigs

        # Extract symbols
        if not comp.symbols:
            symbols: list[Symbol] = []
            for mod in matched_modules:
                for cls in mod.classes:
                    symbols.append(_class_to_symbol(cls))
            comp.symbols = symbols

        # Extract constants
        if not comp.constants:
            consts: list[Constant] = []
            for mod in matched_modules:
                for name, value in mod.module_constants.items():
                    consts.append(Constant(name=name, value=value, context=mod.name))
            comp.constants = consts

        # Infer contract
        if not comp.contract:
            for mod in matched_modules:
                contract = _extract_contract(mod, mod.classes)
                if contract:
                    comp.contract = contract
                    break

        # Classify pattern
        if not comp.pattern:
            pattern = _classify_pattern(matched_modules)
            if pattern:
                comp.pattern = pattern

        # Extract responsibilities
        if not comp.responsibilities:
            all_classes: list[ClassInfo] = []
            for mod in matched_modules:
                all_classes.extend(mod.classes)
            resps = _extract_responsibilities(all_classes)
            if resps:
                comp.responsibilities = resps

    # Recompute confidence scores after enrichment
    try:
        from ..core.confidence import compute_component_confidence
        for comp in components:
            if isinstance(comp, Component):
                # Guarantee minimum contract: every component must have one
                if not comp.contract:
                    comp.contract = _synthesize_contract(comp)
                comp.confidence = compute_component_confidence(comp)
    except ImportError:
        pass


def _synthesize_contract(comp: Component) -> str:
    """Generate a minimum contract from available component metadata.

    Telemetry shows 0 contracts → 32% pass rate vs 70% with contracts.
    Every component must have at least a basic contract describing its role.
    """
    parts: list[str] = []

    # Use pattern if available
    if comp.pattern:
        parts.append(f"Implements {comp.pattern} pattern.")

    # Describe public API from signatures
    if comp.signatures:
        pub_sigs = [s.name for s in comp.signatures if not s.name.startswith("_")][:5]
        if pub_sigs:
            parts.append(f"Exposes: {', '.join(pub_sigs)}.")

    # Describe responsibilities
    if comp.responsibilities:
        parts.append(f"Responsible for: {'; '.join(comp.responsibilities[:3])}.")

    # Fallback: describe by files and name
    if not parts:
        file_hint = f" across {len(comp.files)} files" if comp.files else ""
        parts.append(f"Provides {comp.name} functionality{file_hint}.")

    return " ".join(parts)


def _extract_trigger(decorated_functions: list, func_name: str) -> str:
    """Find trigger decorator for a function."""
    for dec_func in decorated_functions:
        if dec_func.name == func_name:
            for dec in dec_func.decorators:
                if _TRIGGER_DECORATORS.search(dec):
                    return dec
    return ""


def _extract_steps(functions: list[FunctionInfo], entry_name: str) -> list[str]:
    """Extract ordered call steps from the entry point function's call graph."""
    for func in functions:
        if func.name == entry_name:
            return list(func.calls) if func.calls else []
    return []


def _extract_error_conditions(functions: list[FunctionInfo], entry_name: str) -> list[str]:
    """Extract error/post conditions from raises in the entry function."""
    for func in functions:
        if func.name == entry_name:
            return list(func.raises) if func.raises else []
    return []


@monitored("orchestration.auto_enrich_behaviors")
def enrich_behaviors_from_manifest(model: Any, manifest: Manifest) -> None:
    """Enrich model behaviors in-place from manifest data.

    Populates trigger, steps, and postconditions for each behavior by matching
    source_file to manifest modules and using the behavior name as entry point.
    """
    # Build file -> ModuleInfo lookup
    file_lookup: dict[str, ModuleInfo] = {}
    for mod in manifest.modules:
        file_lookup[mod.file] = mod

    behaviors = (
        model.entities.behaviors
        if hasattr(model.entities, "behaviors")
        else model.entities.get("behaviors", [])
        if hasattr(model.entities, "get")
        else []
    )

    for behavior in behaviors:
        if not isinstance(behavior, Behavior):
            continue

        # Match source_file to module
        module = file_lookup.get(behavior.source_file or "")
        if not module:
            continue

        # Use behavior name (snake_case) as entry point function name
        entry_name = behavior.name.lower().replace(" ", "_").replace("-", "_")

        # Extract trigger from decorated functions (don't overwrite)
        if not behavior.trigger:
            trigger = _extract_trigger(module.decorated_functions, entry_name)
            if trigger:
                behavior.trigger = trigger

        # Extract steps from call graph (don't overwrite)
        if not behavior.steps:
            steps = _extract_steps(module.functions, entry_name)
            if steps:
                behavior.steps = steps

        # Extract postconditions from raises (don't overwrite)
        if not behavior.postconditions:
            conditions = _extract_error_conditions(module.functions, entry_name)
            if conditions:
                behavior.postconditions = [f"raises {exc}" for exc in conditions]


@monitored("orchestration.enrich_with_block_context")
def enrich_with_block_context(
    model: Any,
    recursive_manifests: dict,  # dict[str, RecursiveManifest]
) -> None:
    """Second-pass enrichment using block-level context.

    Uses recursive manifests to:
    1. Classify patterns at block level (more indicators available)
    2. Propagate block pattern to unclassified components
    3. Infer contracts from block name when module docstring is absent
    """
    components = (
        model.entities.components
        if hasattr(model.entities, "components")
        else model.entities.get("components", [])
        if hasattr(model.entities, "get")
        else []
    )

    # Group components by block
    block_components: dict[str, list] = {}
    for comp in components:
        if isinstance(comp, Component):
            bid = comp.source_block
            if bid:
                block_components.setdefault(bid, []).append(comp)

    for block_id, rm in recursive_manifests.items():
        comps = block_components.get(block_id, [])
        if not comps:
            continue

        # Classify pattern at block level (all modules combined)
        all_modules = rm.manifest.modules
        block_pattern = _classify_pattern(all_modules, threshold=2)

        # Propagate to unclassified components
        for comp in comps:
            if not comp.pattern:
                if block_pattern:
                    comp.pattern = block_pattern
                else:
                    # Try individual with threshold=1 (lowered because we have block context)
                    matched = [
                        m for m in all_modules
                        if m.file in comp.files
                        or any(
                            m.file.endswith(f) or f.endswith(m.file)
                            for f in comp.files
                        )
                    ]
                    if matched:
                        individual = _classify_pattern(matched, threshold=1)
                        if individual:
                            comp.pattern = individual

            # Infer contract from block name if still missing
            if not comp.contract:
                comp.contract = f"{comp.name} in {rm.block_name} block."

        # Recompute confidence for affected components
        try:
            from ..core.confidence import compute_component_confidence
            for comp in comps:
                comp.confidence = compute_component_confidence(comp)
        except ImportError:
            pass


# ---------------------------------------------------------------------------
# Interface contract extraction from SourceGraph
# ---------------------------------------------------------------------------


def manifest_to_source_graph(manifest: Any, model: Any) -> "SourceGraph":
    """Convert a Manifest's import data into a SourceGraph for interface extraction.

    Resolves module-name imports (e.g. 'src.b.core') to file paths by matching
    against manifest modules, then creates DependencyEdge objects.
    """
    from architecture_model.manifest.protocol import SourceGraph, SourceUnit, DependencyEdge

    # Build a lookup: module name (dot-separated) -> file path
    # e.g. "src.a.main" -> "src/a/main.py"
    name_to_file: dict[str, str] = {}
    for mod in manifest.modules:
        # mod.name is typically dot-separated; mod.file is the path
        name_to_file[mod.name] = mod.file
        # Also index by converting file path to dot notation
        dot_name = mod.file.replace("/", ".").replace(".py", "")
        name_to_file[dot_name] = mod.file

    # Build SourceUnits (one per module)
    units = [
        SourceUnit(file=mod.file, exports=[], language="python")
        for mod in manifest.modules
    ]

    # Build edges from imports
    edges: list[DependencyEdge] = []
    known_files = {mod.file for mod in manifest.modules}

    for mod in manifest.modules:
        for imp in mod.imports:
            # Try to resolve import to a manifest module file
            target_file = name_to_file.get(imp)
            if not target_file:
                # Try prefix matching (e.g. "src.b" might match "src.b.__init__")
                # or the import might be a package — skip stdlib/external
                continue
            if target_file == mod.file:
                continue  # skip self-imports
            if target_file not in known_files:
                continue
            edges.append(DependencyEdge(
                source=mod.file,
                target=target_file,
                symbols=[],
            ))

    return SourceGraph(
        units=units,
        edges=edges,
        root=getattr(manifest, 'project_root', ''),
        language="python",
    )


def extract_component_interfaces(
    model: Any,
    graph: "SourceGraph",
) -> int:
    """Extract interface contracts between components from cross-boundary edges.

    For each dependency edge that crosses a component boundary:
    - The source component gets a 'requires' interface
    - The target component gets a 'provides' interface

    Args:
        model: ArchitectureModel with entities.components
        graph: SourceGraph with edges (dependency info)

    Returns:
        Number of interfaces added.
    """
    from architecture_model.core.types import ComponentInterface
    from architecture_model.manifest.protocol import SourceGraph

    # Build file -> component mapping
    components = _get_components(model)
    file_to_comp: dict[str, Component] = {}
    for comp in components:
        for f in comp.files:
            file_to_comp[f] = comp

    # Build file -> exports mapping from graph
    file_exports: dict[str, list[str]] = {}
    for unit in graph.units:
        file_exports[unit.file] = unit.export_names

    added = 0
    # Track existing interfaces to avoid duplicates
    seen: set[tuple[str, str, str]] = set()  # (comp_id, kind, target_comp_id)

    for edge in graph.edges:
        src_comp = file_to_comp.get(edge.source)
        tgt_comp = file_to_comp.get(edge.target)

        # Only care about cross-boundary edges
        if not src_comp or not tgt_comp or src_comp is tgt_comp:
            continue

        # Determine what symbols are being imported
        symbols = edge.symbols if edge.symbols else file_exports.get(edge.target, [])

        # Source component REQUIRES from target component
        req_key = (src_comp.id, "requires", tgt_comp.id)
        if req_key not in seen:
            seen.add(req_key)
            src_comp.interfaces.append(ComponentInterface(
                name=f"uses_{tgt_comp.name}",
                kind="requires",
                target_component=tgt_comp.id,
                symbols=symbols[:10],  # cap at 10 most relevant
            ))
            added += 1

        # Target component PROVIDES to source component
        prov_key = (tgt_comp.id, "provides", src_comp.id)
        if prov_key not in seen:
            seen.add(prov_key)
            tgt_comp.interfaces.append(ComponentInterface(
                name=f"exposes_to_{src_comp.name}",
                kind="provides",
                target_component=src_comp.id,
                symbols=symbols[:10],
            ))
            added += 1

    return added


def enrich_from_source_graph(model: Any, graph: "SourceGraph") -> None:
    """Enrich model components from SourceGraph export data (language-agnostic).

    Populates signatures, symbols, contracts, patterns, and responsibilities
    from ExportedSymbol data. Enables non-Python repos to reach higher confidence.
    """
    from architecture_model.manifest.protocol import SourceGraph as SG
    from architecture_model.core.confidence import compute_component_confidence

    # Build file -> unit lookup
    unit_map = {u.file: u for u in graph.units}

    components = _get_components(model)
    for comp in components:
        if not comp.files:
            continue

        # Collect exports for this component
        all_exports = []
        for f in comp.files:
            unit = unit_map.get(f)
            if unit:
                all_exports.extend(unit.exports)

        if not all_exports:
            continue

        # Signatures from function exports
        if not comp.signatures:
            comp.signatures = [
                FunctionSignature(name=e.name, params=[], returns="", decorators=[], body_hint=e.doc or "")
                for e in all_exports if e.kind == "function" and e.signature
            ]

        # Symbols from class/type/interface exports
        if not comp.symbols:
            comp.symbols = [
                Symbol(name=e.name, kind=SymbolKind.INTERFACE if e.kind == "interface" else SymbolKind.CLASS,
                       members=[], supers=[])
                for e in all_exports if e.kind in ("class", "type", "interface")
            ]

        # Contract from docstrings
        if not comp.contract:
            docs = [e.doc for e in all_exports if e.doc]
            if docs:
                comp.contract = "; ".join(docs[:3])
            else:
                names = [e.name for e in all_exports[:5]]
                comp.contract = f"Provides: {', '.join(names)}"

        # Responsibilities from function exports
        if not comp.responsibilities:
            funcs = [e.name for e in all_exports if e.kind == "function"]
            if funcs:
                comp.responsibilities = funcs[:10]

        # Pattern detection from export names
        if not comp.pattern:
            names_lower = " ".join(e.name.lower() for e in all_exports)
            if any(kw in names_lower for kw in ("handle", "route", "endpoint", "controller")):
                comp.pattern = "handler"
            elif any(kw in names_lower for kw in ("connect", "query", "repository", "store")):
                comp.pattern = "repository"
            elif any(kw in names_lower for kw in ("create", "build", "factory", "new")):
                comp.pattern = "factory"
            elif any(kw in names_lower for kw in ("middleware", "interceptor", "filter")):
                comp.pattern = "middleware"
            elif any(kw in names_lower for kw in ("service", "manager", "provider")):
                comp.pattern = "service"

        # Recompute confidence
        comp.confidence = compute_component_confidence(comp)


def _get_components(model: Any) -> list[Component]:
    """Get components from model handling both dict and Entities."""
    entities = model.entities if hasattr(model, "entities") else model.get("entities", {})
    if hasattr(entities, "components"):
        return entities.components
    elif isinstance(entities, dict):
        return entities.get("components", [])
    return []


@monitored("orchestration.create_behaviors")
def create_behaviors_from_manifest(
    model: Any,
    manifest: Manifest,
) -> tuple[list[Behavior], list[Relationship]]:
    """Auto-create granular behaviors from manifest, one per significant function.

    Scans all modules in the manifest, creates a Behavior for each function
    in router and service modules. Links behaviors to components via relationships.

    Args:
        model: ArchitectureModel with entities.components populated.
        manifest: Manifest with modules and interfaces.

    Returns:
        Tuple of (behaviors created, relationships linking components to behaviors).
    """
    # Build file→component mapping
    components = _get_components(model)
    file_to_comp: dict[str, str] = {}
    for comp in components:
        for f in (comp.files or []):
            file_to_comp[f] = comp.id

    # Build import graph: which files import which
    imports_from: dict[str, set[str]] = {}
    for iface in (manifest.interfaces or []):
        src = iface.source if hasattr(iface, 'source') else iface.get('source', '')
        tgt = iface.target if hasattr(iface, 'target') else iface.get('target', '')
        if src and tgt:
            imports_from.setdefault(src, set()).add(tgt)

    behaviors: list[Behavior] = []
    new_rels: list[Relationship] = []
    beh_id = 1

    for mod in manifest.modules:
        # Skip __init__.py files
        if mod.file.endswith("__init__.py"):
            continue

        comp_id = file_to_comp.get(mod.file)
        if not comp_id:
            continue

        # Only create behaviors for router and service modules
        is_router = "routers/" in mod.file or "routes/" in mod.file or "views/" in mod.file
        is_service = "services/" in mod.file or "pipeline" in mod.file
        if not is_router and not is_service:
            continue

        functions = mod.functions or []
        for func in functions:
            fname = func.name if hasattr(func, 'name') else str(func)

            # Skip private/dunder functions
            if fname.startswith("_"):
                continue

            # Skip trivial service functions
            call_count = len(func.calls) if hasattr(func, 'calls') and func.calls else 0
            if is_service and call_count < 2:
                # Simple accessor patterns are always trivial with <2 calls
                trivial_prefixes = ("get_", "set_", "is_", "has_", "fetch_")
                if any(fname.startswith(p) for p in trivial_prefixes):
                    continue

            # Determine trigger
            if is_router:
                trigger = _infer_http_trigger(fname, mod.file)
            else:
                trigger = "internal service call"

            # Determine steps from function's calls
            steps = []
            if hasattr(func, 'calls') and func.calls:
                steps = [call for call in func.calls if not call.startswith("_")][:10]

            # Determine involved components
            involved = {comp_id}
            imported_files = imports_from.get(mod.file, set())
            for imp_file in imported_files:
                imp_comp = file_to_comp.get(imp_file)
                if imp_comp and imp_comp != comp_id:
                    involved.add(imp_comp)

            beh = Behavior(
                id=f"BEH-{beh_id}",
                name=fname,
                status=Status.ACTIVE,
                source_file=mod.file,
                trigger=trigger,
                steps=steps,
            )
            behaviors.append(beh)

            # Create realizes relationships (component → behavior)
            for cid in involved:
                new_rels.append(Relationship(
                    type=RelationType.REALIZES,
                    from_id=cid,
                    to_id=beh.id,
                    description=f"{cid} participates in {fname}",
                ))

            beh_id += 1

    # CRUD collapse: merge create_X, get_X, update_X, delete_X into "X CRUD"
    crud_prefixes = ("get_all_", "create_", "get_", "update_", "delete_", "add_", "remove_", "list_")
    resource_map: dict[str, list[int]] = {}
    for idx, beh in enumerate(behaviors):
        for prefix in crud_prefixes:
            if beh.name.startswith(prefix):
                resource = beh.name[len(prefix):]
                if resource.endswith("s") and len(resource) > 1:
                    resource = resource[:-1]
                resource_map.setdefault(resource, []).append(idx)
                break

    indices_to_remove: set[int] = set()
    for resource, indices in resource_map.items():
        if len(indices) >= 3:
            indices_to_remove.update(indices)
            all_steps = [behaviors[i].name for i in indices]
            old_ids = {behaviors[i].id for i in indices}
            resource_title = resource.replace("_", " ").title()
            collapsed_beh = Behavior(
                id=f"BEH-{beh_id}",
                name=f"{resource_title} CRUD",
                status=Status.ACTIVE,
                source_file=behaviors[indices[0]].source_file,
                trigger=behaviors[indices[0]].trigger,
                steps=all_steps,
            )
            # Collect unique source components from old relationships
            sources = {r.from_id for r in new_rels if r.to_id in old_ids}
            # Remove old relationships, add new ones
            new_rels = [r for r in new_rels if r.to_id not in old_ids]
            for cid in sources:
                new_rels.append(Relationship(
                    type=RelationType.REALIZES,
                    from_id=cid,
                    to_id=collapsed_beh.id,
                    description=f"{cid} participates in {collapsed_beh.name}",
                ))
            behaviors.append(collapsed_beh)
            beh_id += 1

    if indices_to_remove:
        behaviors = [b for i, b in enumerate(behaviors) if i not in indices_to_remove]

    return behaviors, new_rels


def _infer_http_trigger(func_name: str, file_path: str) -> str:
    """Infer HTTP trigger from function name and file path."""
    import os
    resource = os.path.splitext(os.path.basename(file_path))[0]

    name_lower = func_name.lower()
    if name_lower.startswith(("create", "add", "new", "post")):
        return f"POST /{resource}"
    elif name_lower.startswith(("list", "get_all", "search", "index")):
        return f"GET /{resource}"
    elif name_lower.startswith(("get", "read", "fetch", "retrieve", "show")):
        return f"GET /{resource}/{{id}}"
    elif name_lower.startswith(("update", "edit", "modify", "put", "patch")):
        return f"PATCH /{resource}/{{id}}"
    elif name_lower.startswith(("delete", "remove", "destroy")):
        return f"DELETE /{resource}/{{id}}"
    elif name_lower.startswith(("approve", "reject", "toggle", "archive")):
        return f"POST /{resource}/{{id}}/{name_lower}"
    else:
        return f"POST /{resource}/{func_name}"
