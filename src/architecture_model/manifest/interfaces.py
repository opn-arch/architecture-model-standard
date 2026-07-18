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

    Args:
        modules: Typed module info objects from AST scanning.
        root: Project root path.

    Returns:
        List of InterfaceEdge objects representing inter-module dependencies.
    """
    # Build a map of file paths to importable module names
    file_to_module: dict[str, str] = {}
    for mod in modules:
        mod_name = mod.file.replace("/", ".").removesuffix(".py")
        file_to_module[mod.file] = mod_name

    module_to_file: dict[str, str] = {v: k for k, v in file_to_module.items()}

    interfaces: list[InterfaceEdge] = []
    seen: set[tuple[str, str]] = set()

    for mod in modules:
        source_file = mod.file
        for imp in mod.imports:
            # Check if this import refers to another module in our project
            target_file = module_to_file.get(imp)
            if not target_file:
                # Try partial match (e.g. "app.models" matches "app.models.log")
                for mod_path, fpath in module_to_file.items():
                    if mod_path.startswith(imp + ".") or imp.startswith(mod_path + "."):
                        target_file = fpath
                        break
            if target_file and target_file != source_file:
                key = (source_file, target_file)
                if key not in seen:
                    seen.add(key)
                    interfaces.append(
                        InterfaceEdge(
                            source=source_file,
                            target=target_file,
                            import_path=imp,
                        )
                    )

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
