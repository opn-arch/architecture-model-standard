"""
Test Contract Miner: extracts behavioral specifications (contracts) from test suites.

AST-scans test files to determine what each method/function should do, providing
structured context for LLM-driven code generation.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MethodContract:
    """Behavioral contract for a single method/function, derived from tests."""

    component: str  # Source module name (e.g., "core", "parser")
    target: str  # Class.method or function name being tested
    test_source: str  # Test file:function that defines this contract
    assertions: list[str] = field(default_factory=list)  # Simplified assertion descriptions
    inputs: list[str] = field(default_factory=list)  # Example inputs from parametrize
    expected: list[str] = field(default_factory=list)  # Expected outputs/behaviors
    raises: list[str] = field(default_factory=list)  # Expected exceptions
    fixtures: list[str] = field(default_factory=list)  # Required setup (fixture names)


@dataclass
class TestContracts:
    """All behavioral contracts extracted from a test suite."""

    __test__ = False  # Prevent pytest collection

    contracts: list[MethodContract] = field(default_factory=list)
    public_api: list[str] = field(default_factory=list)  # Symbols imported by tests
    fixture_definitions: dict[str, str] = field(default_factory=dict)  # fixture → desc
    total_tests: int = 0
    total_assertions: int = 0

    def for_component(self, component_name: str) -> list[MethodContract]:
        """Filter contracts relevant to a specific component."""
        return [c for c in self.contracts if c.component == component_name]

    def summary_for_prompt(self, component_name: str, max_tokens: int = 500) -> str:
        """Format contracts as text for inclusion in generation prompt.

        Format each contract as:
        - {target}: {assertions joined}. Raises: {raises}. Inputs: {inputs[:3]}

        Truncate at max_tokens (estimated 4 chars/token).
        """
        relevant = self.for_component(component_name)
        if not relevant:
            return ""
        lines: list[str] = []
        char_limit = max_tokens * 4
        total_chars = 0
        for c in relevant:
            desc_parts: list[str] = []
            if c.assertions:
                desc_parts.append("; ".join(c.assertions[:3]))
            if c.raises:
                desc_parts.append(f"Raises: {', '.join(c.raises)}")
            if c.inputs:
                desc_parts.append(f"Inputs: {', '.join(c.inputs[:2])}")
            line = f"- {c.target}: {'. '.join(desc_parts)}"
            if total_chars + len(line) > char_limit:
                break
            lines.append(line)
            total_chars += len(line)
        return "\n".join(lines)


class TestContractMiner:
    """Mines behavioral contracts from test suites via AST analysis."""

    def mine(self, repo_path: Path, package_name: str) -> TestContracts:
        """Mine behavioral contracts from a repo's test suite.

        Args:
            repo_path: Root of the repo (e.g., /tmp/test-repos/click)
            package_name: The package being tested (e.g., "click")
        """
        test_files = self._discover_test_files(repo_path)

        contracts: list[MethodContract] = []
        public_api: set[str] = set()
        fixture_defs: dict[str, str] = {}
        total_tests = 0
        total_assertions = 0

        for test_file in test_files:
            tree = self._parse_file(test_file)
            if tree is None:
                continue

            # Extract imports to identify which components are being tested
            file_imports = self._extract_package_imports(tree, package_name)

            # Extract public API symbols
            for symbol in file_imports.keys():
                public_api.add(symbol)

            # Extract fixture definitions from this file
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and self._is_fixture(node):
                    doc = ast.get_docstring(node) or ""
                    fixture_defs[node.name] = doc[:100] if doc else node.name

            # Process each test function
            rel_path = str(test_file.relative_to(repo_path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        total_tests += 1
                        contract = self._extract_contract(
                            node, file_imports, package_name, rel_path
                        )
                        if contract:
                            total_assertions += len(contract.assertions)
                            contracts.append(contract)

        return TestContracts(
            contracts=contracts,
            public_api=sorted(public_api),
            fixture_definitions=fixture_defs,
            total_tests=total_tests,
            total_assertions=total_assertions,
        )

    def _discover_test_files(self, repo_path: Path) -> list[Path]:
        """Find test files, excluding venvs and caches."""
        exclude = {".venv", "venv", "__pycache__", ".git", "node_modules", ".tox", ".eggs"}
        files: list[Path] = []
        for p in repo_path.rglob("*.py"):
            if any(part in exclude for part in p.parts):
                continue
            if p.name.startswith("test_") or p.name.endswith("_test.py"):
                files.append(p)
        return sorted(files)

    def _parse_file(self, path: Path) -> ast.Module | None:
        """Parse a Python file, returning None on failure."""
        try:
            return ast.parse(path.read_text(errors="ignore"))
        except (SyntaxError, OSError):
            return None

    def _extract_package_imports(self, tree: ast.Module, package_name: str) -> dict[str, str]:
        """Extract imports from the package under test.

        Returns: dict mapping imported symbol → component/module name.
        E.g., for 'from click.core import Command': {"Command": "core"}
        E.g., for 'from click import Command': {"Command": "click"}
        E.g., for 'import click': {"click": "click"}
        """
        imports: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                # Check if it's from our package
                if node.module == package_name or node.module.startswith(f"{package_name}."):
                    # Determine component: "click.core" → "core", "click" → "click"
                    parts = node.module.split(".")
                    component = parts[-1] if len(parts) > 1 else package_name
                    for alias in node.names:
                        imports[alias.name] = component
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == package_name or alias.name.startswith(f"{package_name}."):
                        parts = alias.name.split(".")
                        component = parts[-1] if len(parts) > 1 else package_name
                        imports[alias.asname or alias.name] = component
        return imports

    def _is_fixture(self, node: ast.FunctionDef) -> bool:
        """Check if a function is decorated with @pytest.fixture."""
        for dec in node.decorator_list:
            if isinstance(dec, ast.Attribute) and dec.attr == "fixture":
                return True
            if isinstance(dec, ast.Name) and dec.id == "fixture":
                return True
            if isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute) and dec.func.attr == "fixture":
                    return True
                if isinstance(dec.func, ast.Name) and dec.func.id == "fixture":
                    return True
        return False

    def _extract_contract(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_imports: dict[str, str],
        package_name: str,
        test_file: str,
    ) -> MethodContract | None:
        """Extract a behavioral contract from a single test function."""
        # Determine target: what is this test testing?
        target = self._identify_target(func_node, file_imports)
        if not target:
            # Fallback: derive from test name
            name = func_node.name
            if name.startswith("test_"):
                target = name[5:]  # test_basic_functionality → basic_functionality
            else:
                return None

        # Determine component
        component = self._identify_component(func_node, file_imports, target)

        # Extract assertions
        assertions = self._extract_assertions(func_node)

        # Extract raises
        raises = self._extract_raises(func_node)

        # Extract parametrize inputs
        inputs = self._extract_parametrize_inputs(func_node)

        # Extract fixtures (from function arguments)
        fixtures = [arg.arg for arg in func_node.args.args if arg.arg not in ("self", "cls")]

        # Expected values (from assertions)
        expected = self._extract_expected_values(func_node)

        return MethodContract(
            component=component,
            target=target,
            test_source=f"{test_file}::{func_node.name}",
            assertions=assertions,
            inputs=inputs,
            expected=expected,
            raises=raises,
            fixtures=fixtures,
        )

    def _identify_target(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, file_imports: dict[str, str]
    ) -> str | None:
        """Identify what method/function the test is exercising.

        Strategy:
        1. Look for method calls on imported objects (e.g., runner.invoke → "invoke")
        2. Look for direct calls to imported names (e.g., Command() → "Command")
        """
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # obj.method() pattern
                if isinstance(node.func, ast.Attribute):
                    method = node.func.attr
                    # Check if the object is an imported name
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in file_imports:
                            return f"{node.func.value.id}.{method}"
                    return method  # Just the method name
                # direct_call() pattern
                elif isinstance(node.func, ast.Name):
                    if node.func.id in file_imports:
                        return node.func.id
        return None

    def _identify_component(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_imports: dict[str, str],
        target: str,
    ) -> str:
        """Determine which component this test belongs to."""
        # Check if target references a known import
        if "." in target:
            obj = target.split(".")[0]
            if obj in file_imports:
                return file_imports[obj]
        if target in file_imports:
            return file_imports[target]
        # Default: first imported component
        if file_imports:
            return next(iter(file_imports.values()))
        return "unknown"

    def _extract_assertions(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Extract simplified assertion descriptions."""
        assertions: list[str] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assert):
                desc = self._describe_assertion(node)
                if desc:
                    assertions.append(desc)
        return assertions[:10]  # Cap at 10 per test

    def _describe_assertion(self, assert_node: ast.Assert) -> str | None:
        """Convert an assert AST node to a human-readable description."""
        test = assert_node.test

        # assert x == y
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            op = test.ops[0]
            left = ast.unparse(test.left)[:60]
            right = ast.unparse(test.comparators[0])[:60]

            if isinstance(op, ast.Eq):
                return f"{left} equals {right}"
            elif isinstance(op, ast.In):
                return f"{left} in {right}"
            elif isinstance(op, ast.NotIn):
                return f"{left} not in {right}"
            elif isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                op_str = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
                return f"{left} {op_str.get(type(op), '?')} {right}"
            elif isinstance(op, ast.Is):
                return f"{left} is {right}"
            elif isinstance(op, ast.IsNot):
                return f"{left} is not {right}"

        # assert not x
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            operand = ast.unparse(test.operand)[:60]
            return f"not {operand}"

        # assert x (truthy)
        if isinstance(test, (ast.Name, ast.Attribute)):
            val = ast.unparse(test)[:60]
            return f"{val} is truthy"

        # Fallback: unparse the whole thing
        try:
            full = ast.unparse(assert_node.test)
            return full[:80]
        except Exception:
            return None

    def _extract_raises(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Extract expected exceptions from pytest.raises in tests."""
        raises: list[str] = []
        for node in ast.walk(func_node):
            # with pytest.raises(ExceptionType)
            if isinstance(node, ast.With):
                for item in node.items:
                    call = item.context_expr
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                        if call.func.attr == "raises":
                            for arg in call.args:
                                if isinstance(arg, ast.Name):
                                    raises.append(arg.id)
                                elif isinstance(arg, ast.Attribute):
                                    raises.append(ast.unparse(arg))
        return raises

    def _extract_parametrize_inputs(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[str]:
        """Extract @pytest.mark.parametrize values as example inputs."""
        inputs: list[str] = []
        for dec in func_node.decorator_list:
            # Look for @pytest.mark.parametrize(...)
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                if dec.func.attr == "parametrize":
                    # Second arg is the data list
                    if len(dec.args) >= 2:
                        try:
                            data_repr = ast.unparse(dec.args[1])
                            inputs.append(data_repr[:200])
                        except Exception:
                            pass
        return inputs

    def _extract_expected_values(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[str]:
        """Extract expected values from == comparisons in assertions."""
        expected: list[str] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
                if node.test.ops and isinstance(node.test.ops[0], ast.Eq):
                    for comp in node.test.comparators:
                        try:
                            val = ast.unparse(comp)
                            if len(val) < 100:  # Skip huge expected values
                                expected.append(val)
                        except Exception:
                            pass
        return expected[:5]  # Cap
