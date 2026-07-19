"""Interface derivation from import analysis between scanned modules."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

from architecture_model.manifest.types import InterfaceEdge, ModuleInfo, ModuleStatus

logger = logging.getLogger(__name__)


def derive_interfaces(modules: list[ModuleInfo], root: Path) -> list[InterfaceEdge]:
    """Derive interfaces from import analysis between scanned modules.

    Uses both simple imports and imports_detailed (with relative import
    resolution) to find inter-module dependencies within the project.

    Args:
        modules: Typed module info objects from AST scanning.
        root: Project root path.

    Returns:
        List of InterfaceEdge objects representing inter-module dependencies.
    """
    # Build maps: file path <-> dotted module name
    file_to_module: dict[str, str] = {}
    for mod in modules:
        mod_name = mod.file.replace("/", ".").removesuffix(".py")
        file_to_module[mod.file] = mod_name

    module_to_file: dict[str, str] = {v: k for k, v in file_to_module.items()}

    # Also build a set of file stems (without .py) for path-based matching
    file_set: set[str] = {f.removesuffix(".py") for f in file_to_module}

    interfaces: list[InterfaceEdge] = []
    seen: set[tuple[str, str]] = set()

    def _add_edge(source: str, target: str, import_path: str) -> None:
        if target != source:
            key = (source, target)
            if key not in seen:
                seen.add(key)
                interfaces.append(InterfaceEdge(
                    source=source, target=target, import_path=import_path,
                ))

    def _resolve_dotted(dotted: str) -> str | None:
        """Resolve a dotted module path to a file path in our module set."""
        slash = dotted.replace(".", "/")
        # Direct match: src.architecture_model.core.parser -> src/architecture_model/core/parser.py
        if slash in file_set:
            return slash + ".py"
        # Package __init__: src.architecture_model.core -> src/architecture_model/core/__init__.py
        init = slash + "/__init__"
        if init in file_set:
            return init + ".py"
        # Try stripping src/ prefix (absolute imports don't include src/)
        # e.g., architecture_model.core.parser -> try src/architecture_model/core/parser
        for prefix in ("src/",):
            with_prefix = prefix + slash
            if with_prefix in file_set:
                return with_prefix + ".py"
            init_with = prefix + slash + "/__init__"
            if init_with in file_set:
                return init_with + ".py"
        return None

    for mod in modules:
        source_file = mod.file

        # --- Pass 1: simple imports (backward compat) ---
        for imp in mod.imports:
            target_file = module_to_file.get(imp)
            if not target_file:
                for mod_path, fpath in module_to_file.items():
                    if mod_path.startswith(imp + ".") or imp.startswith(mod_path + "."):
                        target_file = fpath
                        break
            if target_file:
                _add_edge(source_file, target_file, imp)

        # --- Pass 2: imports_detailed (relative + absolute with full paths) ---
        for imp_detail in mod.imports_detailed:
            module_name = imp_detail.module
            is_relative = imp_detail.is_relative

            if is_relative:
                # Resolve relative to the source module's directory.
                # from .types import X  -> same dir
                # from ..core.parser import X  -> parent dir (level info lost,
                #   so try both same-dir and parent-dir)
                mod_dir = str(Path(source_file).parent)
                slash_name = module_name.replace(".", "/")

                # Try same-level: mod_dir/module_name
                candidate = mod_dir + "/" + slash_name
                if candidate in file_set:
                    _add_edge(source_file, candidate + ".py", module_name)
                    continue
                # Try package init
                if candidate + "/__init__" in file_set:
                    _add_edge(source_file, candidate + "/__init__.py", module_name)
                    continue
                # Try parent-level: parent(mod_dir)/module_name
                parent_dir = str(Path(mod_dir).parent)
                candidate = parent_dir + "/" + slash_name
                if candidate in file_set:
                    _add_edge(source_file, candidate + ".py", module_name)
                    continue
                if candidate + "/__init__" in file_set:
                    _add_edge(source_file, candidate + "/__init__.py", module_name)
                    continue
                # Try grandparent (for from ...X imports)
                gp_dir = str(Path(parent_dir).parent)
                candidate = gp_dir + "/" + slash_name
                if candidate in file_set:
                    _add_edge(source_file, candidate + ".py", module_name)
                elif candidate + "/__init__" in file_set:
                    _add_edge(source_file, candidate + "/__init__.py", module_name)
            else:
                # Absolute import: architecture_model.core.parser
                target_file = _resolve_dotted(module_name)
                if target_file:
                    _add_edge(source_file, target_file, module_name)

    logger.debug("Derived %d interface edges from %d modules", len(interfaces), len(modules))
    return interfaces


def _derive_interfaces(modules: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    """Derive interfaces from import analysis between scanned modules.

    .. deprecated::
        Use :func:`derive_interfaces` which accepts typed objects.
        This wrapper converts dicts for backward compatibility.
    """
    warnings.warn(
        "_derive_interfaces is deprecated, use derive_interfaces instead",
        DeprecationWarning,
        stacklevel=2,
    )
    typed_modules = [
        ModuleInfo(
            file=m["file"],
            name=m.get("name", ""),
            docstring=m.get("docstring"),
            functions=[],
            imports=m.get("imports", []),
            line_count=m.get("line_count", 0),
            status=ModuleStatus(m.get("status", "active")),
            classes=[],
        )
        for m in modules
    ]
    edges = derive_interfaces(typed_modules, root)
    return [e.to_dict() for e in edges]
