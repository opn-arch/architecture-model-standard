"""Oracle-optimized context builder combining manifest summary + code slices."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from architecture_model.manifest.interfaces import _derive_interfaces
from architecture_model.manifest.scanner import _scan_file
from architecture_model.training.context_builder import ContextBuilder

if TYPE_CHECKING:
    from architecture_model.training.test_analyzer import TestCoverage, TestStructure


class OracleContextBuilder:
    """Builds optimized context for oracle extraction.

    Combines a manifest summary (structure, key modules, interfaces)
    with ContextBuilder code slices for maximum extraction quality.
    """

    def __init__(self, repo_path: Path, max_chars: int = 48000) -> None:
        self._repo_path = Path(repo_path)
        self._max_chars = max_chars

    def build(
        self,
        manifest: Optional[dict] = None,
        *,
        test_structure: Optional[TestStructure] = None,
        test_coverage: Optional[TestCoverage] = None,
    ) -> str:
        """Build oracle context string.

        Args:
            manifest: Pre-generated manifest dict. If None, generates one via AST scan.
            test_structure: Optional test structure analysis for context enrichment.
            test_coverage: Optional test coverage analysis for importance weighting.

        Returns:
            Combined context string for oracle extraction.
        """
        from architecture_model.training.few_shot_examples import MANUAL_EXAMPLE

        if manifest is None:
            manifest = self._generate_manifest()

        parts: list[str] = []

        # Part 0: Few-shot example (prepended for precision guidance)
        if MANUAL_EXAMPLE:
            few_shot_section = f"## Few-Shot Example\n{MANUAL_EXAMPLE}"
            parts.append(few_shot_section)
            parts.append("\n## Your Task\n")

        # Part 0.5: Test-evidenced structure (after few-shot, before project data)
        if test_structure is not None:
            test_section = self.format_test_analysis(test_structure, test_coverage)
            if test_section:
                parts.append(test_section)

        # Part 1: Manifest summary (capped at 20% of budget)
        summary = self._format_manifest_summary(manifest)
        summary_budget = int(self._max_chars * 0.2)
        if len(summary) > summary_budget:
            summary = summary[:summary_budget] + "\n# ... (truncated)"
        parts.append(summary)

        # Part 2: Code context from ContextBuilder (fills remainder)
        remaining = self._max_chars - sum(len(p) for p in parts) - 200  # header overhead
        cb = ContextBuilder(self._repo_path, max_chars=max(remaining, 5000))
        slices = cb.build()
        parts.append("\n## Source Code Context\n")
        parts.append(slices.combined())

        return "\n".join(parts)[:self._max_chars]

    def format_test_analysis(
        self, structure: TestStructure, coverage: Optional[TestCoverage] = None
    ) -> str:
        """Format test analysis as context section for LLM.

        Produces a concise (under 500 chars) summary of test-implied components
        and relationship evidence to guide architecture extraction.

        Args:
            structure: Static test structure analysis.
            coverage: Optional runtime coverage analysis.

        Returns:
            Formatted test analysis section string.
        """
        if not structure.implied_components:
            return ""

        lines: list[str] = []
        lines.append("## Test-Evidenced Structure")
        lines.append("The repo's test suite suggests these architectural components:")

        # Determine importance level per component from test counts
        component_test_counts: dict[str, int] = {}
        for test_file, count in structure.test_counts.items():
            filename = Path(test_file).name
            component = self._component_from_test_filename(filename)
            if component and component in structure.implied_components:
                component_test_counts[component] = (
                    component_test_counts.get(component, 0) + count
                )

        # Sort by test count descending, limit to top 8
        sorted_components = sorted(
            structure.implied_components,
            key=lambda c: component_test_counts.get(c, 0),
            reverse=True,
        )[:8]

        for comp in sorted_components:
            count = component_test_counts.get(comp, 0)
            if count >= 20:
                importance = "high importance"
            elif count >= 5:
                importance = "medium importance"
            else:
                importance = "low importance"
            lines.append(f"- {comp} ({count} tests, {importance})")

        # Add relationship evidence from coverage if available
        if coverage and coverage.relationship_evidence:
            lines.append("")
            lines.append("Test relationship evidence (modules tested together):")
            for mod_a, mod_b, strength in coverage.relationship_evidence[:5]:
                # Use just the filename stems for brevity
                name_a = Path(mod_a).stem
                name_b = Path(mod_b).stem
                if strength >= 0.7:
                    label = "strong"
                elif strength >= 0.4:
                    label = "moderate"
                else:
                    label = "weak"
                lines.append(f"- {name_a} \u2194 {name_b} ({label})")

        result = "\n".join(lines)
        # Enforce 500 char limit for conciseness
        if len(result) > 500:
            result = result[:497] + "..."
        return result

    @staticmethod
    def _component_from_test_filename(filename: str) -> str | None:
        """Extract component name from test filename (mirrors TestStructureAnalyzer)."""
        if filename in ("conftest.py", "__init__.py"):
            return None
        name = filename
        if name.endswith(".py"):
            name = name[:-3]
        if name.startswith("test_"):
            name = name[5:]
        elif name.endswith("_test"):
            name = name[:-5]
        if not name:
            return None
        words = name.split("_")
        titled: list[str] = []
        for word in words:
            if not word:
                continue
            if word.upper() in ("HTTP", "API", "URL", "SQL", "DB", "IO", "UI", "ID", "CLI"):
                titled.append(word.upper())
            else:
                titled.append(word.capitalize())
        return " ".join(titled) if titled else None

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
