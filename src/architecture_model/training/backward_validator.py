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
    ) -> BackwardResult:
        """Run all backward validation checks.

        Args:
            model: The extracted architecture model.
            manifest: Reality Manifest for the repo.
            repo_path: Path to the repo root.
            consistency_score: Pre-computed regeneration consistency (0-1).
        """
        test_cov, tested, untested = self._check_test_mapping(model, manifest, repo_path)
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
        self, model: ArchitectureModel, manifest: dict, repo_path: Path
    ) -> tuple[float, list[str], list[str]]:
        """Check 1: Test structure mapping.

        Find test files, parse their imports, map imports to components.
        Score = fraction of components with at least one test importing their modules.
        """
        if not model.entities.components:
            return 1.0, [], []

        # Build module->component map
        module_map = ManifestCoverageComputer()._build_module_component_map(manifest, model)

        # Find all test files
        test_files = self._find_test_files(repo_path)

        # Parse imports from test files and map to components
        tested_comp_ids: set[str] = set()
        for test_file in test_files:
            imports = self._parse_imports(test_file, repo_path)
            for imp in imports:
                comp_id = module_map.get(imp, "")
                if comp_id:
                    tested_comp_ids.add(comp_id)

        # Calculate coverage
        comp_id_to_name = {c.id: c.name for c in model.entities.components}
        tested = [comp_id_to_name[cid] for cid in tested_comp_ids if cid in comp_id_to_name]
        untested = [c.name for c in model.entities.components if c.id not in tested_comp_ids]

        score = len(tested_comp_ids) / len(model.entities.components)
        return score, tested, untested

    def _check_doc_coverage(
        self, model: ArchitectureModel, repo_path: Path
    ) -> tuple[float, list[str], list[str]]:
        """Check 2: README/docs feature check.

        Parse markdown files for feature headings/descriptions.
        Match against capability names via fuzzy matching.
        Score = fraction of documented features that match a capability.
        """
        features = self._extract_documented_features(repo_path)
        if not features:
            return 1.0, [], []  # No docs = vacuously satisfied

        capability_names = [c.name for c in model.entities.capabilities]
        if not capability_names:
            return 0.0, [], features

        matched: list[str] = []
        unmatched: list[str] = []

        for feature in features:
            if _name_matches(feature, capability_names, threshold=0.3):
                matched.append(feature)
            else:
                unmatched.append(feature)

        score = len(matched) / len(features)
        return score, matched, unmatched

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

    def _parse_imports(self, test_file: Path, repo_path: Path) -> list[str]:
        """Parse imports from a test file and resolve to relative file paths."""
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

        # Resolve module names to file paths relative to repo_path
        resolved: list[str] = []
        for mod in imported_modules:
            # Convert dot notation to path
            parts = mod.split(".")
            # Try multiple resolutions
            candidates = [
                "/".join(parts) + ".py",
                "/".join(parts) + "/__init__.py",
                "/".join(parts[1:]) + ".py" if len(parts) > 1 else "",
            ]
            for candidate in candidates:
                if candidate and (repo_path / candidate).exists():
                    resolved.append(candidate)
                    break

        return resolved

    # -----------------------------------------------------------------------
    # Documentation feature extraction
    # -----------------------------------------------------------------------

    def _extract_documented_features(self, repo_path: Path) -> list[str]:
        """Extract feature names from README and docs."""
        features: list[str] = []

        # Check README
        for readme_name in ["README.md", "README.rst", "readme.md"]:
            readme = repo_path / readme_name
            if readme.exists():
                features.extend(self._parse_markdown_features(readme))
                break

        # Check docs/
        docs_dir = repo_path / "docs"
        if docs_dir.exists():
            for md_file in sorted(docs_dir.rglob("*.md"))[:10]:  # Cap to avoid huge doc trees
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

        # Headings (## and ###)
        heading_re = re.compile(r"^#{2,3}\s+(.+)", re.MULTILINE)
        for match in heading_re.finditer(content):
            heading = match.group(1).strip()
            # Skip generic headings
            if heading.lower() not in (
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
            ):
                features.append(heading)

        # Bold list items: - **Feature**: desc
        bold_re = re.compile(r"^[-*]\s+\*\*([^*]+)\*\*", re.MULTILINE)
        for match in bold_re.finditer(content):
            features.append(match.group(1).strip())

        return features
