"""Auto-enrichment of architecture models from AST data.

Populates FunctionSignature, Constant, and TestContract on components
by scanning their source files and discovering matching test files.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, Component, Constant, FunctionSignature, TestContract
)
from architecture_model.manifest.body_hints import extract_file_hints
from architecture_model.manifest.test_analyzer import analyze_test_file

logger = logging.getLogger(__name__)


def enrich_model(
    model: ArchitectureModel,
    project_root: Path,
) -> ArchitectureModel:
    """Auto-populate signatures, constants, test_contracts on components."""
    components = model.entities.get("components", []) if isinstance(model.entities, dict) else model.entities.components
    for comp in components:
        if _enum_str(comp.status) != "ACTIVE":
            continue
        if not comp.files:
            continue

        _enrich_signatures(comp, project_root)
        _enrich_constants(comp, project_root)
        _enrich_test_contracts(comp, project_root)

    return model


def _enum_str(v) -> str:
    """Extract string from enum or return as-is."""
    return v.value if hasattr(v, 'value') else str(v)


def _enrich_signatures(comp: Component, root: Path) -> None:
    """Extract function signatures from component's source files."""
    existing_names = {s.name for s in comp.signatures}

    for file_path in comp.files:
        fpath = root / file_path
        if not fpath.exists():
            logger.debug("File not found: %s", fpath)
            continue
        try:
            sigs = extract_file_hints(fpath, include_private=False)
            for sig in sigs:
                if sig.name not in existing_names:
                    comp.signatures.append(sig)
                    existing_names.add(sig.name)
        except Exception as e:
            logger.warning("Failed to extract signatures from %s: %s", fpath, e)


def _enrich_constants(comp: Component, root: Path) -> None:
    """Extract module-level constants from source files."""
    existing_names = {c.name for c in comp.constants}

    for file_path in comp.files:
        fpath = root / file_path
        if not fpath.exists():
            continue
        try:
            source = fpath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(fpath))
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            name = target.id
                            if name not in existing_names:
                                try:
                                    value = ast.literal_eval(node.value)
                                except (ValueError, TypeError):
                                    value = ast.unparse(node.value)
                                comp.constants.append(
                                    Constant(name=name, value=str(value))
                                )
                                existing_names.add(name)
        except Exception as e:
            logger.warning("Failed to extract constants from %s: %s", fpath, e)


def _enrich_test_contracts(comp: Component, root: Path) -> None:
    """Discover test files and extract test contracts."""
    existing_methods = {t.test_method for t in comp.test_contracts}

    test_files = _discover_test_files(comp, root)
    for tpath in test_files:
        try:
            result = analyze_test_file(tpath)
            for tc in result.contracts:
                if tc.test_method not in existing_methods:
                    comp.test_contracts.append(tc)
                    existing_methods.add(tc.test_method)
        except Exception as e:
            logger.warning("Failed to analyze test file %s: %s", tpath, e)


def _discover_test_files(comp: Component, root: Path) -> list[Path]:
    """Find test files for a component by convention."""
    test_files: list[Path] = []
    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return test_files

    for file_path in comp.files:
        fp = Path(file_path)
        module_name = fp.stem
        package_name = fp.parent.name

        # Convention 1: tests/test_{module}.py
        candidate1 = tests_dir / f"test_{module_name}.py"
        if candidate1.exists() and candidate1 not in test_files:
            test_files.append(candidate1)

        # Convention 2: tests/test_{package}/test_{module}.py
        candidate2 = tests_dir / f"test_{package_name}" / f"test_{module_name}.py"
        if candidate2.exists() and candidate2 not in test_files:
            test_files.append(candidate2)

        # Convention 3: tests/{module}_test.py
        candidate3 = tests_dir / f"{module_name}_test.py"
        if candidate3.exists() and candidate3 not in test_files:
            test_files.append(candidate3)

    return test_files
