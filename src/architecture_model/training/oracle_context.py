"""Oracle-optimized context builder combining manifest summary + code slices."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from architecture_model.manifest.interfaces import _derive_interfaces
from architecture_model.manifest.scanner import _scan_file
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
            manifest: Pre-generated manifest dict. If None, generates one via AST scan.

        Returns:
            Combined context string for oracle extraction.
        """
        if manifest is None:
            manifest = self._generate_manifest()

        parts: list[str] = []

        # Part 1: Manifest summary (capped at 20% of budget)
        summary = self._format_manifest_summary(manifest)
        summary_budget = int(self._max_chars * 0.2)
        if len(summary) > summary_budget:
            summary = summary[:summary_budget] + "\n# ... (truncated)"
        parts.append(summary)

        # Part 2: Code context from ContextBuilder (fills remainder)
        remaining = self._max_chars - len(summary) - 200  # header overhead
        cb = ContextBuilder(self._repo_path, max_chars=max(remaining, 5000))
        slices = cb.build()
        parts.append("\n## Source Code Context\n")
        parts.append(slices.combined())

        return "\n".join(parts)[:self._max_chars]

    def _generate_manifest(self) -> dict:
        """Generate a proper manifest via AST scan (no config required).

        Uses the real scanner to extract imports, functions, and docstrings
        from each Python file, then derives interfaces from the import graph.
        Infers functional blocks from top-level directory structure.
        """
        root = self._repo_path
        modules: list[dict] = []

        for py_file in sorted(root.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue

            try:
                mod_meta = _scan_file(root, py_file)
                modules.append(mod_meta)
            except (OSError, ValueError):
                continue

        # Derive interfaces from the import graph
        interfaces = _derive_interfaces(modules, root)

        # Infer functional blocks from directory structure
        blocks = self._infer_blocks(modules)

        return {
            "modules": modules,
            "interfaces": interfaces,
            "functional_blocks": blocks,
        }

    def _infer_blocks(self, modules: list[dict]) -> dict:
        """Infer functional blocks from top-level directory groupings."""
        dir_groups: dict[str, list[dict]] = {}

        for mod in modules:
            filepath = mod.get("file", "")
            parts = filepath.split("/")
            if len(parts) >= 2:
                # Group by first directory
                block_dir = parts[0]
            else:
                block_dir = "_root"
            dir_groups.setdefault(block_dir, []).append(mod)

        blocks: dict[str, dict] = {}
        for i, (dir_name, dir_mods) in enumerate(sorted(dir_groups.items()), 1):
            if len(dir_mods) < 2:
                continue  # Skip trivial blocks
            block_id = f"F{i}"
            blocks[block_id] = {
                "name": dir_name.replace("_", " ").strip().title(),
                "status": "active",
                "sub_functions": [{"file": m["file"]} for m in dir_mods],
            }

        return blocks

    def _format_manifest_summary(self, manifest: dict) -> str:
        """Format manifest into a concise summary for the oracle."""
        modules = manifest.get("modules", [])
        interfaces = manifest.get("interfaces", [])
        blocks = manifest.get("functional_blocks", {})

        # Sort modules by LOC
        sorted_mods = sorted(modules, key=lambda m: m.get("line_count", 0), reverse=True)
        total_loc = sum(m.get("line_count", 0) for m in modules)
        significant_mods = [m for m in modules if m.get("line_count", 0) >= 10]

        lines = [
            "## Reality Manifest Summary",
            f"- **{len(significant_mods)} significant modules** ({len(modules)} total), {total_loc} total LOC",
            f"- **{len(interfaces)} import interfaces** (dependency edges)",
            f"- **{len(blocks)} functional blocks**",
            "",
            "### Key Modules (by size):",
        ]

        for mod in sorted_mods[:15]:
            funcs = mod.get("functions", [])
            func_summary = f", {len(funcs)} functions" if funcs else ""
            lines.append(
                f"- `{mod.get('file', '?')}` — {mod.get('name', '?')} "
                f"({mod.get('line_count', 0)} LOC{func_summary})"
            )

        if blocks:
            lines.append("\n### Functional Blocks:")
            for bid, bdata in list(blocks.items())[:8]:
                bname = bdata.get("name", bid)
                n_files = len(bdata.get("sub_functions", []))
                lines.append(f"- **{bname}** ({n_files} files)")

        if interfaces:
            # Block-level dependency matrix (structural hint for LLM)
            from collections import Counter

            # Build file→block mapping
            file_to_block: dict[str, str] = {}
            for bid, bdata in blocks.items():
                bname = bdata.get("name", bid)
                for sf in bdata.get("sub_functions", []):
                    file_to_block[sf.get("file", "")] = bname

            # Aggregate interface edges at block level
            block_edges: Counter[tuple[str, str]] = Counter()
            for iface in interfaces:
                src_block = file_to_block.get(iface.get("source", ""), "")
                tgt_block = file_to_block.get(iface.get("target", ""), "")
                if src_block and tgt_block and src_block != tgt_block:
                    block_edges[(src_block, tgt_block)] += 1

            if block_edges:
                lines.append(f"\n### Block-Level Dependencies ({len(interfaces)} total import edges):")
                lines.append("Components in these blocks MUST have depends-on/consumes relationships:")
                for (src, tgt), count in block_edges.most_common():
                    if count >= 10:
                        strength = "strong"
                    elif count >= 5:
                        strength = "moderate"
                    else:
                        strength = "weak"
                    lines.append(f"- **{src}** -> **{tgt}**: {count} edges ({strength})")

            # Also show most-connected modules (hotspots)
            target_counts = Counter(i["target"] for i in interfaces)
            hotspots = target_counts.most_common(10)
            lines.append(f"\n### Dependency Hotspots:")
            for target, count in hotspots:
                lines.append(f"- `{target}` <- imported by {count} modules")

        return "\n".join(lines)
