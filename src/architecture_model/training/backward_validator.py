"""
BackwardValidator: validates an extracted ArchitectureModel against a repo's tests and docs.

Produces scores across 4 dimensions:
1. Test coverage — fraction of components tested (imports traced from test files)
2. Doc coverage — fraction of documented features matched to capabilities
3. Structural coverage — ManifestCoverageComputer overall score
4. Consistency — regeneration consistency (set externally)
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from architecture_model.core.types import ArchitectureModel
from architecture_model.training.oracle_coverage import (
    ManifestCoverageComputer,
    CoverageResult,
    _tokenize,
    _name_matches,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class BackwardResult:
    """Result of backward validation."""

    test_coverage: float = 0.0  # Check 1: fraction of components tested
    doc_coverage: float = 0.0  # Check 2: fraction of documented features matched
    structural_coverage: float = 0.0  # Check 3: ManifestCoverageComputer overall
    consistency: float = 0.0  # Check 4: regeneration consistency (set externally)

    # Detail
    tested_components: list[str] = field(default_factory=list)
    untested_components: list[str] = field(default_factory=list)
    matched_features: list[str] = field(default_factory=list)
    unmatched_features: list[str] = field(default_factory=list)

    @property
    def overall(self) -> float:
        """Weighted average: structural 0.3, test 0.25, doc 0.2, consistency 0.25."""
        return (
            0.30 * self.structural_coverage
            + 0.25 * self.test_coverage
            + 0.20 * self.doc_coverage
            + 0.25 * self.consistency
        )


# ---------------------------------------------------------------------------
# BackwardValidator
# ---------------------------------------------------------------------------


class BackwardValidator:
    """Validates an architecture model against a repo's tests and documentation."""

    def validate(
        self,
        model: ArchitectureModel,
        manifest: dict[str, Any],
        repo_path: Path,
        consistency_score: float = 0.0,
        source_dir: Path | None = None,
    ) -> BackwardResult:
        """Run all backward validation checks.

        Args:
            model: The extracted architecture model.
            manifest: Reality Manifest for the repo.
            repo_path: Path to the repo root.
            consistency_score: Pre-computed regeneration consistency (0-1).
            source_dir: Optional explicit source directory (auto-detected if None).
        """
        test_cov, tested, untested = self._check_test_mapping(
            model, manifest, repo_path, source_dir
        )
        doc_cov, matched, unmatched = self._check_doc_coverage(model, repo_path)
        structural = ManifestCoverageComputer().compute(manifest, model)

        return BackwardResult(
            test_coverage=test_cov,
            doc_coverage=doc_cov,
            structural_coverage=structural.overall,
            consistency=consistency_score,
            tested_components=tested,
            untested_components=untested,
            matched_features=matched,
            unmatched_features=unmatched,
        )

    def _check_test_mapping(
        self,
        model: ArchitectureModel,
        manifest: dict,
        repo_path: Path,
        source_dir: Path | None = None,
    ) -> tuple[float, list[str], list[str]]:
        """Check 1: Test structure mapping.

        Find test files, parse their imports, map imports to components via
        package-aware import resolution.
        Score = fraction of components with at least one test importing their modules.
        """
        if not model.entities.components:
            return 1.0, [], []

        # Build module->component map (manifest file path → component ID)
        module_map = ManifestCoverageComputer()._build_module_component_map(manifest, model)

        # Build import name → manifest file path mapping
        import_to_file = self._build_import_to_file_map(manifest, repo_path, source_dir)

        # Find all test files
        test_files = self._find_test_files(repo_path)

        # Parse imports from test files and map to components
        tested_comp_ids: set[str] = set()
        for test_file in test_files:
            imports = self._parse_imports(test_file)
            for imp in imports:
                # Exact match in import map
                file_path = import_to_file.get(imp)
                if file_path:
                    comp_id = module_map.get(file_path, "")
                    if comp_id:
                        tested_comp_ids.add(comp_id)
                        continue

                    # Facade pattern: import resolves to __init__.py with no component.
                    # Follow re-exports to find actual submodule components.
                    if "__init__.py" in file_path and not comp_id:
                        reexport_files = self._resolve_facade_imports(
                            file_path, manifest, import_to_file
                        )
                        for reexport_file in reexport_files:
                            sub_comp_id = module_map.get(reexport_file, "")
                            if sub_comp_id:
                                tested_comp_ids.add(sub_comp_id)
                    continue

                # Prefix match: test import is more specific than map entry
                # e.g., "click.core.BaseCommand" matches "click.core"
                for mapped_import, mapped_file in import_to_file.items():
                    if imp.startswith(mapped_import + "."):
                        comp_id = module_map.get(mapped_file, "")
                        if comp_id:
                            tested_comp_ids.add(comp_id)
                            break

        # Calculate coverage
        comp_id_to_name = {c.id: c.name for c in model.entities.components}
        tested = [comp_id_to_name[cid] for cid in tested_comp_ids if cid in comp_id_to_name]
        untested = [c.name for c in model.entities.components if c.id not in tested_comp_ids]

        score = len(tested_comp_ids) / len(model.entities.components)
        return score, tested, untested

    def _resolve_facade_imports(
        self,
        init_file: str,
        manifest: dict,
        import_to_file: dict[str, str],
    ) -> list[str]:
        """Resolve facade-pattern re-exports from an __init__.py to submodule file paths.

        When a test does `import httpcore`, it resolves to `__init__.py` which owns
        no component. This method follows the re-exports declared in __init__.py
        (via `imports_detailed` with `is_relative: True`) to find the actual
        submodule files that contain the real implementations.

        Resolution strategies (tried in order):
        1. imports_detailed entries with is_relative=True → resolve module name to file
        2. Fallback: plain imports list → try filename-based resolution (module + ".py")

        Args:
            init_file: The manifest file path for __init__.py (e.g., "__init__.py").
            manifest: The reality manifest dict.
            import_to_file: The import name → file path map (for cross-reference).

        Returns:
            List of manifest file paths for re-exported submodules.
        """
        modules = manifest.get("modules", [])

        # Find the __init__.py module entry in the manifest
        init_module = None
        for mod in modules:
            if mod["file"] == init_file:
                init_module = mod
                break

        if init_module is None:
            return []

        resolved_files: list[str] = []

        # Determine the directory prefix for the __init__.py
        # e.g., "subpkg/__init__.py" → "subpkg/", "__init__.py" → ""
        if "/" in init_file:
            dir_prefix = init_file.rsplit("/", 1)[0] + "/"
        else:
            dir_prefix = ""

        # Strategy 1: Use imports_detailed with is_relative=True
        imports_detailed = init_module.get("imports_detailed", [])
        if imports_detailed:
            for entry in imports_detailed:
                if not entry.get("is_relative", False):
                    continue
                rel_module = entry.get("module", "")
                if not rel_module:
                    continue
                # Resolve relative module name to file path
                # Strip leading underscores/dots for matching, try as-is first
                candidate_file = self._resolve_relative_module(
                    rel_module, dir_prefix, modules, import_to_file
                )
                if candidate_file:
                    resolved_files.append(candidate_file)
            if resolved_files:
                return resolved_files

        # Strategy 2: Fallback to plain imports list
        plain_imports = init_module.get("imports", [])
        for imp_name in plain_imports:
            candidate_file = self._resolve_relative_module(
                imp_name, dir_prefix, modules, import_to_file
            )
            if candidate_file:
                resolved_files.append(candidate_file)

        return resolved_files

    def _resolve_relative_module(
        self,
        module_name: str,
        dir_prefix: str,
        modules: list[dict],
        import_to_file: dict[str, str],
    ) -> str | None:
        """Resolve a relative module name to a manifest file path.

        Tries multiple resolution strategies:
        1. Direct filename match: dir_prefix + module_name + ".py"
        2. Module name without leading underscore
        3. Cross-reference in import_to_file map

        Args:
            module_name: The relative module name (e.g., "_client", "core").
            dir_prefix: Directory prefix from __init__.py location.
            modules: List of manifest module entries.
            import_to_file: The import name → file path map.

        Returns:
            Manifest file path if resolved, None otherwise.
        """
        # Build set of known manifest files for quick lookup
        manifest_files = {mod["file"] for mod in modules}

        # Strategy 1: Direct file path: dir_prefix + module_name + ".py"
        candidate = f"{dir_prefix}{module_name}.py"
        if candidate in manifest_files:
            return candidate

        # Strategy 2: Try without leading underscore
        if module_name.startswith("_"):
            candidate = f"{dir_prefix}{module_name[1:]}.py"
            if candidate in manifest_files:
                return candidate

        # Strategy 3: Check if it's in the import_to_file map
        for mapped_import, mapped_file in import_to_file.items():
            if mapped_import.endswith("." + module_name) or mapped_import == module_name:
                if mapped_file in manifest_files:
                    return mapped_file

        return None

    def _check_doc_coverage(
        self, model: ArchitectureModel, repo_path: Path
    ) -> tuple[float, list[str], list[str]]:
        """Check 2: README/docs feature check.

        Parse markdown files for feature headings/descriptions.
        Match against all entity names (capabilities, components, layers, behaviors)
        via fuzzy matching and containment.
        Score = fraction of documented features that match an entity.
        """
        features = self._extract_documented_features(repo_path)
        if not features:
            return 1.0, [], []  # No docs = vacuously satisfied

        # Match against all entity names, not just capabilities
        all_entity_names = (
            [c.name for c in model.entities.capabilities]
            + [c.name for c in model.entities.components]
            + [l.name for l in model.entities.layers]
            + [b.name for b in model.entities.behaviors]
        )
        if not all_entity_names:
            return 0.0, [], features

        matched: list[str] = []
        unmatched: list[str] = []

        for feature in features:
            if _name_matches(feature, all_entity_names, threshold=0.2):
                matched.append(feature)
            elif self._feature_contained_in_entity(feature, all_entity_names):
                matched.append(feature)
            else:
                unmatched.append(feature)

        score = len(matched) / len(features)
        return score, matched, unmatched

    def _feature_contained_in_entity(self, feature: str, entity_names: list[str]) -> bool:
        """Check if feature words are contained in any entity name, or vice versa."""
        feature_tokens = _tokenize(feature)
        if not feature_tokens:
            return False
        for name in entity_names:
            name_tokens = _tokenize(name)
            if not name_tokens:
                continue
            # Feature tokens are subset of entity tokens
            if feature_tokens <= name_tokens:
                return True
            # Entity tokens are subset of feature tokens
            if name_tokens <= feature_tokens:
                return True
            # Any significant word (3+ chars) overlap
            significant_overlap = {t for t in (feature_tokens & name_tokens) if len(t) >= 3}
            if significant_overlap:
                return True
        return False

    # -----------------------------------------------------------------------
    # Test file discovery
    # -----------------------------------------------------------------------

    def _find_test_files(self, repo_path: Path) -> list[Path]:
        """Find all test files in the repo."""
        test_files: list[Path] = []
        for pattern in ["**/test_*.py", "**/*_test.py"]:
            test_files.extend(repo_path.rglob(pattern))
        # Also look in tests/ directory
        tests_dir = repo_path / "tests"
        if tests_dir.exists():
            for py_file in tests_dir.rglob("*.py"):
                if py_file not in test_files and py_file.name != "__init__.py":
                    test_files.append(py_file)
        return sorted(set(test_files))

    def _parse_imports(self, test_file: Path) -> list[str]:
        """Parse imports from a test file, returning raw module names.

        No path resolution is performed — callers use _build_import_to_file_map
        to resolve import names to manifest file paths.
        """
        try:
            source = test_file.read_text(errors="ignore")
            tree = ast.parse(source)
        except (SyntaxError, ValueError, OSError):
            return []

        imported_modules: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)

        return imported_modules

    # -----------------------------------------------------------------------
    # Package detection and import mapping
    # -----------------------------------------------------------------------

    def _detect_packages(self, repo_path: Path) -> dict[str, str]:
        """Detect Python packages in the repo.

        Returns dict mapping package_name → relative directory path from repo_path.
        Searches common layouts: flat (pkg/), src-layout (src/pkg/), lib-layout (lib/pkg/).
        """
        packages: dict[str, str] = {}

        search_dirs: list[Path] = [repo_path]
        for subdir in ["src", "lib"]:
            candidate = repo_path / subdir
            if candidate.is_dir():
                search_dirs.append(candidate)

        for search_dir in search_dirs:
            try:
                entries = list(search_dir.iterdir())
            except OSError:
                continue
            for item in entries:
                if item.is_dir() and (item / "__init__.py").exists():
                    pkg_name = item.name
                    rel_dir = str(item.relative_to(repo_path))
                    # Don't override — prefer packages found closer to root
                    if pkg_name not in packages:
                        packages[pkg_name] = rel_dir

        return packages

    def _build_import_to_file_map(
        self, manifest: dict, repo_path: Path, source_dir: Path | None = None
    ) -> dict[str, str]:
        """Build mapping from importable module names to manifest file paths.

        Uses two strategies:
        1. Direct path conversion: manifest file "src/client.py" → import "src.client"
        2. Package-prefixed: detect packages, prepend package name to manifest paths
           e.g., manifest "core.py" + package "click" → import "click.core"

        Args:
            manifest: The reality manifest dict.
            repo_path: Path to repo root.
            source_dir: Optional explicit source directory override.

        Returns:
            Dict mapping importable module name → manifest file path.
        """
        modules = manifest.get("modules", [])
        packages = self._detect_packages(repo_path)

        import_map: dict[str, str] = {}

        for mod in modules:
            file_path = mod["file"]  # e.g., "core.py" or "src/client.py"

            # Strategy 1: Direct path-to-module conversion
            # Handles manifests with paths like "src/client.py" → "src.client"
            import_name = self._file_path_to_import_name(file_path)
            if import_name:
                import_map[import_name] = file_path

            # Strategy 2: Package-prefixed
            # Handles manifests where files are relative to source dir
            # e.g., manifest file "core.py" with package "click" → "click.core"
            for pkg_name in packages:
                if import_name:
                    pkg_import = f"{pkg_name}.{import_name}"
                else:
                    # __init__.py → just the package name
                    pkg_import = pkg_name
                import_map[pkg_import] = file_path

        return import_map

    @staticmethod
    def _file_path_to_import_name(file_path: str) -> str:
        """Convert a manifest file path to an importable module name.

        Examples:
            "src/client.py" → "src.client"
            "core.py" → "core"
            "__init__.py" → ""
            "utils/__init__.py" → "utils"
            "testing/helpers.py" → "testing.helpers"
        """
        if not file_path.endswith(".py"):
            return ""

        path = file_path[:-3]  # Strip .py

        # Handle __init__ → parent package name
        if path.endswith("/__init__"):
            path = path[: -len("/__init__")]
        elif path == "__init__":
            return ""

        return path.replace("/", ".")

    # -----------------------------------------------------------------------
    # Documentation feature extraction
    # -----------------------------------------------------------------------

    def _extract_documented_features(self, repo_path: Path) -> list[str]:
        """Extract feature names from README and docs."""
        features: list[str] = []

        # Skip patterns for changelog/history files
        _SKIP_PATTERNS = {"changelog", "changes", "history", "release", "migration"}

        # Check README
        for readme_name in ["README.md", "README.rst", "readme.md"]:
            readme = repo_path / readme_name
            if readme.exists():
                features.extend(self._parse_markdown_features(readme))
                break

        # Check docs/ (but skip changelogs)
        docs_dir = repo_path / "docs"
        if docs_dir.exists():
            for md_file in sorted(docs_dir.rglob("*.md"))[:10]:
                # Skip changelog/history files
                if any(p in md_file.stem.lower() for p in _SKIP_PATTERNS):
                    continue
                features.extend(self._parse_markdown_features(md_file))

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for f in features:
            f_lower = f.lower().strip()
            if f_lower not in seen and len(f_lower) > 2:
                seen.add(f_lower)
                unique.append(f)

        return unique

    def _parse_markdown_features(self, md_file: Path) -> list[str]:
        """Extract feature names from a markdown file.

        Looks for:
        - ## and ### headings (as features)
        - Bold list items: - **Feature name**: description
        """
        try:
            content = md_file.read_text(errors="ignore")
        except OSError:
            return []

        features: list[str] = []

        # Version/date patterns to skip
        _VERSION_RE = re.compile(
            r"^\[?\d+\.\d+|^v?\d+\.\d+|^\d{4}-\d{2}|^unreleased",
            re.IGNORECASE,
        )

        # Headings (## and ###)
        heading_re = re.compile(r"^#{2,3}\s+(.+)", re.MULTILINE)
        for match in heading_re.finditer(content):
            heading = match.group(1).strip()
            # Skip generic headings
            if heading.lower() in (
                "installation",
                "usage",
                "contributing",
                "license",
                "changelog",
                "credits",
                "authors",
                "requirements",
                "getting started",
                "quick start",
                "table of contents",
                "development",
                "testing",
                "documentation",
                "faq",
                "fixed",
                "added",
                "changed",
                "removed",
                "deprecated",
                "security",
            ):
                continue
            # Skip version-pattern headings
            if _VERSION_RE.match(heading):
                continue
            features.append(heading)

        # Bold list items: - **Feature**: desc
        bold_re = re.compile(r"^[-*]\s+\*\*([^*]+)\*\*", re.MULTILINE)
        for match in bold_re.finditer(content):
            item = match.group(1).strip()
            # Skip version patterns in bold items too
            if not _VERSION_RE.match(item):
                features.append(item)

        return features
