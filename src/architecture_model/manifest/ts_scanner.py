"""Regex-based TypeScript/JavaScript scanner (fallback).

Used when Node.js/@arch-model/scanner-js is not available.
Provides degraded output: no type resolution, raw signatures.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def scan_typescript_fallback(root: Path) -> dict[str, Any]:
    """Scan a TS/JS project using regex patterns.
    Returns a SourceGraph-compatible dict.
    """
    units = []
    edges = []

    export_fn_re = re.compile(r"export\s+(?:async\s+)?function\s+(\w+)")
    export_class_re = re.compile(r"export\s+class\s+(\w+)")
    export_const_re = re.compile(r"export\s+(?:const|let|var)\s+(\w+)")
    export_interface_re = re.compile(r"export\s+interface\s+(\w+)")
    export_type_re = re.compile(r"export\s+type\s+(\w+)")
    import_re = re.compile(r"import\s+.*?from\s+['\"](\.[^'\"]+)['\"]")

    for ext in ("*.ts", "*.tsx", "*.js", "*.jsx"):
        for filepath in root.rglob(ext):
            if any(p in filepath.parts for p in ("node_modules", "dist", ".git")):
                continue
            rel = str(filepath.relative_to(root))
            try:
                text = filepath.read_text(errors="replace")
            except Exception:
                continue

            exports = []
            for m in export_fn_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "function", "signature": "", "doc": ""})
            for m in export_class_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "class", "signature": "", "doc": ""})
            for m in export_const_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "constant", "signature": "", "doc": ""})
            for m in export_interface_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "interface", "signature": "", "doc": ""})
            for m in export_type_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "type", "signature": "", "doc": ""})

            units.append({
                "file": rel,
                "has_content": len(exports) > 0,
                "exports": exports,
                "language": "typescript" if ext.startswith("*.ts") else "javascript",
            })

            for m in import_re.finditer(text):
                target = _resolve_import_path(rel, m.group(1))
                edges.append({"source": rel, "target": target, "symbols": []})

    return {"units": units, "edges": edges, "root": str(root), "language": "typescript"}


def _resolve_import_path(source: str, module_path: str) -> str:
    """Simple relative import resolution."""
    from pathlib import PurePosixPath
    source_dir = str(PurePosixPath(source).parent)
    if source_dir == ".":
        resolved = module_path.lstrip("./")
    else:
        resolved = str(PurePosixPath(source_dir) / module_path.lstrip("./"))
    if not any(resolved.endswith(ext) for ext in (".ts", ".tsx", ".js", ".jsx")):
        resolved += ".ts"
    return resolved
