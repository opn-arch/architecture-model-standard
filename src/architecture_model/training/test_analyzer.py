"""
Test suite analysis: extracts architectural signals from test file structure and coverage.

TestStructureAnalyzer: static analysis (no test execution needed)
- Implied components from test file names
- Test counts per file
- Test import graph

TestCoverageAnalyzer: requires TestRunResult with coverage data
- Module importance scores
- Cross-module relationship evidence
- Component weight signals
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.training.test_runner import TestRunResult


@dataclass
class TestStructure:
    """Static test structure analysis results."""

    implied_components: list[str]  # component names derived from test files
    test_counts: dict[str, int]  # test_file → number of test functions
    test_imports: dict[str, list[str]]  # test_file → imported source modules
    total_tests: int = 0


@dataclass
class TestCoverage:
    """Runtime coverage analysis results."""

    module_importance: dict[str, float]  # module_file → importance (0-1 based on coverage %)
    relationship_evidence: list[tuple[str, str, float]]  # (module_a, module_b, evidence_strength)
    component_weights: dict[str, float]  # implied_component → weight (based on test count + coverage)
    pass_rate: float = 0.0
    total_covered_lines: int = 0
    total_lines: int = 0


class TestStructureAnalyzer:
    """Extracts architectural signals from test file structure (static, no execution)."""

    def analyze(self, repo_path: Path, test_files: list[str] | None = None) -> TestStructure:
        """Analyze test file structure for architectural signals."""
        # 1. Discover test files (if not provided)
        if test_files is not None:
            paths = [repo_path / f for f in test_files]
        else:
            paths = self._discover_test_files(repo_path)

        # 2. Extract implied components from filenames
        implied_components: list[str] = []
        for p in paths:
            component = self._extract_component_name(p.name)
            if component and component not in implied_components:
                implied_components.append(component)

        # 3. Count test functions per file (AST parse)
        test_counts: dict[str, int] = {}
        total_tests = 0
        for p in paths:
            rel = str(p.relative_to(repo_path)) if p.is_absolute() else str(p)
            count = self._count_tests(p)
            test_counts[rel] = count
            total_tests += count

        # 4. Extract imports from test files
        test_imports: dict[str, list[str]] = {}
        for p in paths:
            rel = str(p.relative_to(repo_path)) if p.is_absolute() else str(p)
            imports = self._extract_imports(p)
            test_imports[rel] = imports

        return TestStructure(
            implied_components=implied_components,
            test_counts=test_counts,
            test_imports=test_imports,
            total_tests=total_tests,
        )

    def _discover_test_files(self, repo_path: Path) -> list[Path]:
        """Find all test files in the repo, excluding venvs and caches."""
        test_files: list[Path] = []
        exclude_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules", ".tox"}

        for p in repo_path.rglob("*.py"):
            # Skip excluded directories
            if any(part in exclude_dirs for part in p.parts):
                continue
            # Match test file patterns
            if p.name.startswith("test_") or p.name.endswith("_test.py"):
                test_files.append(p)

        return sorted(test_files)

    def _extract_component_name(self, test_filename: str) -> str | None:
        """test_client.py → 'Client', test_http_pool.py → 'HTTP Pool'.

        Strip test_ prefix and .py suffix, convert snake_case to Title Case.
        Skip conftest.py, __init__.py.
        """
        # Skip non-test files
        if test_filename in ("conftest.py", "__init__.py"):
            return None

        name = test_filename

        # Strip .py suffix
        if name.endswith(".py"):
            name = name[:-3]

        # Strip test_ prefix or _test suffix
        if name.startswith("test_"):
            name = name[5:]
        elif name.endswith("_test"):
            name = name[:-5]

        if not name:
            return None

        # Convert snake_case to Title Case
        # Handle special abbreviations (all-caps segments)
        words = name.split("_")
        titled_words: list[str] = []
        for word in words:
            if not word:
                continue
            # If word is all lowercase and <= 4 chars, could be abbreviation
            # Use uppercase for known abbreviations
            if word.upper() in ("HTTP", "API", "URL", "SQL", "DB", "IO", "UI", "ID", "CLI"):
                titled_words.append(word.upper())
            else:
                titled_words.append(word.capitalize())

        return " ".join(titled_words) if titled_words else None

    def _count_tests(self, test_file: Path) -> int:
        """Count test functions/methods via AST."""
        if not test_file.exists():
            return 0

        try:
            source = test_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            return 0

        count = 0
        for node in ast.walk(tree):
            # Top-level test functions
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                count += 1
            # Test methods in classes
            elif isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
                count += 1

        return count

    def _extract_imports(self, test_file: Path) -> list[str]:
        """Extract imported source modules from a test file."""
        if not test_file.exists():
            return []

        try:
            source = test_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            return []

        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Skip test/pytest imports
                    if not self._is_test_import(alias.name):
                        imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and not self._is_test_import(node.module):
                    imports.append(node.module)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for imp in imports:
            if imp not in seen:
                seen.add(imp)
                unique.append(imp)

        return unique

    def _is_test_import(self, module_name: str) -> bool:
        """Check if an import is a test framework/utility (not source code)."""
        test_prefixes = (
            "pytest", "unittest", "mock", "fixtures",
            "_pytest", "hypothesis", "faker", "factory",
        )
        return any(module_name.startswith(prefix) for prefix in test_prefixes)


class TestCoverageAnalyzer:
    """Derives architectural signals from runtime coverage data."""

    def analyze(self, run_result: TestRunResult, structure: TestStructure) -> TestCoverage:
        """Analyze coverage data for architectural signals."""
        # 1. Compute module importance from line coverage
        module_importance = self._compute_module_importance(run_result.coverage_data)

        # 2. Derive cross-module relationships from test coverage overlap
        relationships = self._derive_relationships(
            run_result.coverage_data, structure.test_imports
        )

        # 3. Compute component weights (test count * coverage)
        component_weights = self._compute_component_weights(structure, module_importance)

        # 4. Compute totals
        total_covered = 0
        total_lines = 0
        for file_info in run_result.coverage_data.values():
            summary = file_info.get("summary", {})
            total_covered += summary.get("covered_lines", 0)
            total_lines += summary.get("num_statements", 0)

        return TestCoverage(
            module_importance=module_importance,
            relationship_evidence=relationships,
            component_weights=component_weights,
            pass_rate=run_result.pass_rate,
            total_covered_lines=total_covered,
            total_lines=total_lines,
        )

    def _compute_module_importance(self, coverage_data: dict) -> dict[str, float]:
        """coverage % → importance score (0-1). Modules with >80% coverage are core."""
        importance: dict[str, float] = {}

        for file_path, file_info in coverage_data.items():
            summary = file_info.get("summary", {})
            num_statements = summary.get("num_statements", 0)
            covered_lines = summary.get("covered_lines", 0)

            if num_statements == 0:
                continue

            coverage_pct = covered_lines / num_statements
            importance[file_path] = coverage_pct

        return importance

    def _derive_relationships(
        self, coverage_data: dict, test_imports: dict[str, list[str]]
    ) -> list[tuple[str, str, float]]:
        """Derive cross-module relationship evidence from test imports and coverage.

        If test_X imports modules A and B, and both A and B have high coverage,
        that's evidence they're tested together (and thus related).
        Strength = min(importance_A, importance_B) — both must be meaningfully covered.
        """
        # First compute importance for matching
        module_importance = self._compute_module_importance(coverage_data)

        # Build a map from module base name to coverage file path
        # coverage_data keys are like "src/client.py", imports are like "mypackage.client"
        module_to_coverage: dict[str, str] = {}
        for cov_path in coverage_data:
            # Extract the module-like name from the file path
            # "src/mypackage/client.py" → "mypackage.client"
            parts = Path(cov_path).with_suffix("").parts
            # Try various truncations to match import names
            for i in range(len(parts)):
                module_name = ".".join(parts[i:])
                module_to_coverage[module_name] = cov_path

        relationships: list[tuple[str, str, float]] = []
        seen_pairs: set[tuple[str, str]] = set()

        for _test_file, imports in test_imports.items():
            # Find which imports have coverage data
            covered_imports: list[tuple[str, str]] = []  # (import_name, coverage_path)
            for imp in imports:
                # Try to find matching coverage entry
                cov_path = module_to_coverage.get(imp)
                if cov_path and cov_path in module_importance:
                    if module_importance[cov_path] > 0.3:  # >30% coverage threshold
                        covered_imports.append((imp, cov_path))

            # Create pairwise relationships
            for i in range(len(covered_imports)):
                for j in range(i + 1, len(covered_imports)):
                    mod_a = covered_imports[i][1]
                    mod_b = covered_imports[j][1]

                    # Normalize pair order for deduplication
                    pair = (min(mod_a, mod_b), max(mod_a, mod_b))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    # Strength = min of both coverages
                    strength = min(
                        module_importance[mod_a],
                        module_importance[mod_b],
                    )
                    relationships.append((mod_a, mod_b, strength))

        # Sort by strength descending
        relationships.sort(key=lambda x: x[2], reverse=True)
        return relationships

    def _compute_component_weights(
        self, structure: TestStructure, module_importance: dict[str, float]
    ) -> dict[str, float]:
        """Weight = normalized(test_count * avg_coverage_of_tested_modules).

        For each implied component, compute its weight based on how many tests
        cover it and the average coverage of the modules it tests.
        """
        component_weights: dict[str, float] = {}

        # Map component names back to their test files
        # component name → test files that imply it
        component_test_files: dict[str, list[str]] = {}
        for test_file in structure.test_counts:
            filename = Path(test_file).name
            component = self._component_from_filename(filename)
            if component and component in structure.implied_components:
                if component not in component_test_files:
                    component_test_files[component] = []
                component_test_files[component].append(test_file)

        for component in structure.implied_components:
            test_files = component_test_files.get(component, [])
            if not test_files:
                component_weights[component] = 0.0
                continue

            # Sum test counts for this component
            total_tests = sum(structure.test_counts.get(tf, 0) for tf in test_files)

            # Average coverage of modules imported by these test files
            coverages: list[float] = []
            for tf in test_files:
                imports = structure.test_imports.get(tf, [])
                for imp in imports:
                    # Find matching coverage data
                    for cov_path, importance in module_importance.items():
                        # Match if the import name appears in the coverage path
                        # e.g., import "mypackage.client" matches "src/mypackage/client.py"
                        cov_module = Path(cov_path).stem
                        imp_parts = imp.split(".")
                        if cov_module in imp_parts or imp_parts[-1] == cov_module:
                            coverages.append(importance)
                            break

            avg_coverage = sum(coverages) / len(coverages) if coverages else 0.0
            component_weights[component] = total_tests * avg_coverage

        # Normalize to 0-1 range
        max_weight = max(component_weights.values()) if component_weights else 1.0
        if max_weight > 0:
            component_weights = {k: v / max_weight for k, v in component_weights.items()}

        return component_weights

    @staticmethod
    def _component_from_filename(filename: str) -> str | None:
        """Extract component name from a test filename (mirrors TestStructureAnalyzer logic)."""
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
