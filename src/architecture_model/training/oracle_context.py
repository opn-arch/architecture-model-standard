"""Oracle-optimized context builder combining manifest summary + code slices."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from architecture_model.training.context_builder import ContextBuilder


class OracleContextBuilder:
    """Builds optimized context for oracle extraction.

    Combines a manifest summary (structure, key modules, interfaces)
    with ContextBuilder code slices for maximum extraction quality.
    """

    def __init__(self, repo_path: Path, max_chars: int = 48000) -> None:
        self._repo_path = Path(repo_path)
        self._max_chars = max_chars

    def build(self, manifest: Optional[dict] = None) -> str:
        """Build oracle context string.

        Args:
            manifest: Pre-generated manifest dict. If None, generates a lightweight one.

        Returns:
            Combined context string for oracle extraction.
        """
        if manifest is None:
            manifest = self._generate_lightweight_manifest()

        parts: list[str] = []

        # Part 1: Manifest summary
        summary = self._format_manifest_summary(manifest)
        parts.append(summary)

        # Part 2: Code context from ContextBuilder
        remaining = self._max_chars - len(summary) - 200  # header overhead
        cb = ContextBuilder(self._repo_path, max_chars=max(remaining, 5000))
        slices = cb.build()
        parts.append("\n## Source Code Context\n")
        parts.append(slices.combined())

        return "\n".join(parts)[:self._max_chars]

    def _generate_lightweight_manifest(self) -> dict:
        """Generate a minimal manifest via AST scan (no config required)."""
        modules: list[dict] = []
        interfaces: list[dict] = []

        for py_file in sorted(self._repo_path.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                loc = len(content.splitlines())
                rel = str(py_file.relative_to(self._repo_path))
                name = py_file.stem.replace("_", " ").title()
                modules.append({"file": rel, "name": name, "line_count": loc, "status": "active"})
            except OSError:
                continue

        return {"modules": modules, "interfaces": interfaces, "functional_blocks": {}}

    def _format_manifest_summary(self, manifest: dict) -> str:
        """Format manifest into a concise summary for the oracle."""
        modules = manifest.get("modules", [])
        interfaces = manifest.get("interfaces", [])
        blocks = manifest.get("functional_blocks", {})

        # Sort modules by LOC
        sorted_mods = sorted(modules, key=lambda m: m.get("line_count", 0), reverse=True)
        total_loc = sum(m.get("line_count", 0) for m in modules)
        active_mods = [m for m in modules if m.get("status") == "active"]

        lines = [
            "## Reality Manifest Summary",
            f"- **{len(active_mods)} active modules**, {total_loc} total LOC",
            f"- **{len(interfaces)} import interfaces** (dependency edges)",
            f"- **{len(blocks)} functional blocks**",
            "",
            "### Key Modules (by size):",
        ]

        for mod in sorted_mods[:10]:
            lines.append(
                f"- `{mod.get('file', '?')}` — {mod.get('name', '?')} "
                f"({mod.get('line_count', 0)} LOC)"
            )

        if blocks:
            lines.append("\n### Functional Blocks:")
            for bid, bdata in list(blocks.items())[:8]:
                bname = bdata.get("name", bid)
                n_files = len(bdata.get("sub_functions", []))
                lines.append(f"- **{bname}** ({n_files} files)")

        if interfaces:
            lines.append(f"\n### Cross-Module Dependencies ({len(interfaces)} edges):")
            for iface in interfaces[:10]:
                lines.append(f"- `{iface.get('source', '?')}` → `{iface.get('target', '?')}`")

        return "\n".join(lines)
