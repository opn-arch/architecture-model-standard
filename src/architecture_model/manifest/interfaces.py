"""Interface derivation from import analysis between scanned modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _derive_interfaces(modules: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    """Derive interfaces from import analysis between scanned modules."""
    # Build a map of module paths to their file info
    module_map: dict[str, dict[str, Any]] = {}
    for mod in modules:
        module_map[mod["file"]] = mod

    # Convert file paths to importable module names
    file_to_module: dict[str, str] = {}
    for mod in modules:
        # e.g. "app/routers/logs.py" -> "app.routers.logs"
        mod_name = mod["file"].replace("/", ".").removesuffix(".py")
        file_to_module[mod["file"]] = mod_name

    module_to_file: dict[str, str] = {v: k for k, v in file_to_module.items()}

    interfaces: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for mod in modules:
        source_file = mod["file"]
        for imp in mod.get("imports", []):
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
                        {
                            "source": source_file,
                            "target": target_file,
                            "import_path": imp,
                        }
                    )

    return interfaces
