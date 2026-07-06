"""Code Writer: materializes generated multi-module code into a testable Python package.

Takes the LLM's multi-module output (separated by '# module.py' comments) and writes
it as a proper Python package that can be pip-installed and tested.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MaterializedPackage:
    """A generated package written to disk, ready for testing."""

    package_dir: Path  # Root dir (contains package_name/ subdir)
    package_name: str  # Package name (e.g., "click")
    source_dir: Path  # Path to the actual source package (package_dir/package_name)
    modules: list[str] = field(default_factory=list)  # Module files written
    init_written: bool = False  # Whether __init__.py was generated/created


class CodeWriter:
    """Materializes generated code into a testable Python package."""

    def materialize(
        self,
        generated_code: str,
        package_name: str,
        output_dir: Path,
    ) -> MaterializedPackage:
        """Write generated multi-module code to a package directory.

        Args:
            generated_code: Multi-module Python code with '# module.py' separators
            package_name: Name for the package (e.g., "click")
            output_dir: Parent directory to create the package in

        Returns:
            MaterializedPackage with metadata about what was written
        """
        # 1. Parse code into modules
        modules = self._split_modules(generated_code, package_name)

        # 2. Create package directory structure
        source_dir = output_dir / package_name
        source_dir.mkdir(parents=True, exist_ok=True)

        # 3. Write each module
        written_modules = []
        module_stems = {
            Path(name).stem for name in modules if name != "__init__.py"
        }
        for module_name, module_code in modules.items():
            # Ensure module_name ends with .py
            if not module_name.endswith(".py"):
                module_name = f"{module_name}.py"

            # Fix absolute imports that should be relative
            module_code = self._fix_relative_imports(
                module_code, package_name, module_stems
            )

            # Handle subdirectories (e.g., "subpkg/module.py")
            module_path = source_dir / module_name
            module_path.parent.mkdir(parents=True, exist_ok=True)
            module_path.write_text(module_code, encoding="utf-8")
            written_modules.append(module_name)

        # 4. Generate __init__.py if not already written
        init_written = False
        if "__init__.py" not in written_modules:
            init_content = self._generate_init(modules, package_name)
            init_path = source_dir / "__init__.py"
            init_path.write_text(init_content, encoding="utf-8")
            init_written = True
            written_modules.append("__init__.py")
        else:
            init_written = True  # Was in the generated code

        return MaterializedPackage(
            package_dir=output_dir,
            package_name=package_name,
            source_dir=source_dir,
            modules=written_modules,
            init_written=init_written,
        )

    def _split_modules(self, code: str, package_name: str) -> dict[str, str]:
        """Split multi-module code into individual modules.

        Returns: dict mapping module_name -> code_content
        """
        modules: dict[str, str] = {}

        # Split by '# module_name.py' pattern
        header_pattern = re.compile(
            r"^#\s*([\w._/\-]+\.py)\s*$",
            re.MULTILINE,
        )

        matches = list(header_pattern.finditer(code))

        if matches:
            for i, match in enumerate(matches):
                module_name = match.group(1)
                # Clean up module name: remove package prefix if present
                module_name = self._normalize_module_name(module_name, package_name)

                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
                module_code = code[start:end].strip()

                if module_code:  # Skip empty modules
                    modules[module_name] = module_code
        else:
            # No module headers found - treat as single module
            modules[f"{package_name}.py"] = code.strip()

        return modules

    def _normalize_module_name(self, name: str, package_name: str) -> str:
        """Normalize module name by stripping package/src prefixes.

        "click/core.py" -> "core.py"
        "src/click/core.py" -> "core.py"
        "core.py" -> "core.py"
        """
        parts = name.replace("\\", "/").split("/")

        # Strip "src" prefix
        if parts and parts[0] == "src":
            parts = parts[1:]

        # Strip package_name prefix
        if parts and parts[0] == package_name:
            parts = parts[1:]

        return "/".join(parts) if parts else name

    def _generate_init(self, modules: dict[str, str], package_name: str) -> str:
        """Generate an __init__.py that exports public symbols.

        Scans each module for class definitions and public functions,
        creates import-all statements.
        """
        imports = []
        for module_name, code in modules.items():
            if module_name == "__init__.py":
                continue
            # Get the module stem (without .py)
            stem = module_name.replace(".py", "").replace("/", ".")
            if stem.startswith("_"):
                continue  # Skip private modules

            # Find public classes and functions via simple regex
            classes = re.findall(r"^class\s+([A-Z]\w*)", code, re.MULTILINE)
            functions = re.findall(r"^def\s+([a-z]\w*)", code, re.MULTILINE)

            # Import public names
            public_names = [c for c in classes if not c.startswith("_")]
            public_names += [f for f in functions if not f.startswith("_")]

            if public_names:
                names_str = ", ".join(public_names)
                imports.append(f"from .{stem} import {names_str}")

        if imports:
            return "\n".join(imports) + "\n"
        return ""

    def _fix_relative_imports(
        self, code: str, package_name: str, known_modules: set[str]
    ) -> str:
        """Fix absolute imports that should be relative within the package.

        LLMs commonly generate `from parser import X` when they should write
        `from .parser import X` for intra-package references. This detects
        known sibling modules and converts to relative imports.

        Also fixes `from package_name.module import X` → `from .module import X`.
        """
        lines = code.split("\n")
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # Fix: from module import ... → from .module import ...
            # Only when 'module' is a known sibling module in this package
            match = re.match(r"^from\s+(\w+)\s+(import\s+.+)$", stripped)
            if match and match.group(1) in known_modules:
                module = match.group(1)
                rest = match.group(2)
                indent = line[: len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}from .{module} {rest}")
                continue

            # Fix: from package_name.module import ... → from .module import ...
            prefix = f"from {package_name}."
            if stripped.startswith(prefix):
                rest = stripped[len(prefix):]
                indent = line[: len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}from .{rest}")
                continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def patch_for_testing(
        self,
        package: MaterializedPackage,
        original_repo: Path,
        test_dir_name: str = "tests",
    ) -> None:
        """Copy test infrastructure from original repo to enable running tests.

        Copies:
        - tests/ directory
        - conftest.py (if at repo root)
        - pyproject.toml or setup.py/setup.cfg (for pip install -e .)

        Args:
            package: The materialized package
            original_repo: Path to the original repo with tests
            test_dir_name: Name of the test directory (default "tests")
        """
        output_dir = package.package_dir

        # Copy tests
        src_tests = original_repo / test_dir_name
        if src_tests.exists():
            dst_tests = output_dir / test_dir_name
            if dst_tests.exists():
                shutil.rmtree(dst_tests)
            shutil.copytree(src_tests, dst_tests, dirs_exist_ok=True)

        # Copy conftest.py if at repo root
        conftest = original_repo / "conftest.py"
        if conftest.exists():
            shutil.copy2(conftest, output_dir / "conftest.py")

        # Copy/generate pyproject.toml for pip install
        pyproject = original_repo / "pyproject.toml"
        if pyproject.exists():
            shutil.copy2(pyproject, output_dir / "pyproject.toml")
        else:
            # Generate minimal pyproject.toml
            content = f"""[project]
name = "{package.package_name}"
version = "0.0.1"

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends._legacy:_Backend"
"""
            (output_dir / "pyproject.toml").write_text(content)

        # Copy setup.py/setup.cfg if they exist
        for cfg in ("setup.py", "setup.cfg"):
            src = original_repo / cfg
            if src.exists():
                shutil.copy2(src, output_dir / cfg)

    def cleanup(self, package: MaterializedPackage) -> None:
        """Remove a materialized package directory."""
        if package.package_dir.exists():
            shutil.rmtree(package.package_dir)
