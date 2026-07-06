"""Test Contract Analyzer — extracts behavioral specifications from test files.

Parses test files using AST and extracts:
- TestContracts: what assertions the tests make
- Constants: literal values tests expect (e.g., ANSI escape codes)
- Required API surface: what symbols/functions the tests import and call

Supports both unittest-style (assertEqual, assertRaises, assertTrue, assertIsInstance)
and pytest-style (assert ==, pytest.raises, assert isinstance) patterns.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from architecture_model.core.types import Constant, TestContract


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class TestAnalysisResult:
    """Result of analyzing a test file for behavioral contracts."""

    test_file: str
    contracts: list[TestContract] = field(default_factory=list)
    constants: list[Constant] = field(default_factory=list)
    required_imports: list[str] = field(default_factory=list)
    test_count: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_test_file(test_file: Path) -> TestAnalysisResult:
    """Parse a test file and extract behavioral contracts.

    Handles both unittest (assertEqual, assertTrue, assertRaises)
    and pytest (assert ==, assert isinstance, pytest.raises) patterns.
    """
    source = test_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test_file))
    filename = test_file.name

    result = TestAnalysisResult(test_file=filename)

    # Extract imports (filter out test framework imports)
    result.required_imports = _extract_imports(tree)

    # Extract contracts from test methods/functions
    test_methods = _find_test_methods(tree)
    result.test_count = len(test_methods)

    for method_name, node in test_methods:
        contracts = _extract_contracts_from_method(node, filename, method_name)
        result.contracts.extend(contracts)

    # Derive constants from value_equality contracts
    result.constants = extract_constants_from_contracts(result.contracts)

    return result


def extract_constants_from_contracts(contracts: list[TestContract]) -> list[Constant]:
    """Derive constants from value_equality contracts.

    e.g., assertion "Fore.BLACK == '\\033[30m'" →
    Constant(name="BLACK", value="30", context="attribute of Fore, produces escape code \\033[30m")
    """
    constants: list[Constant] = []
    seen: set[tuple[str, str]] = set()  # (parent, name) dedup

    for contract in contracts:
        if contract.contract_type != "value_equality":
            continue

        parsed = _parse_escape_code_assertion(contract.assertion)
        if parsed is None:
            continue

        parent, name, code, full_escape = parsed
        key = (parent, name)
        if key in seen:
            continue
        seen.add(key)

        constants.append(
            Constant(
                name=name,
                value=code,
                context=f"attribute of {parent}, produces escape code {full_escape}",
            )
        )

    return constants


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------

# Standard library / test framework modules to exclude
_EXCLUDED_MODULES = frozenset({
    "unittest", "pytest", "sys", "os", "io", "re", "math",
    "collections", "itertools", "functools", "pathlib", "typing",
    "tempfile", "shutil", "json", "copy", "contextlib", "textwrap",
    "unittest.mock", "mock",
})


def _extract_imports(tree: ast.Module) -> list[str]:
    """Extract imported symbols that likely come from the package under test."""
    imports: list[str] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Skip test framework imports
            if _is_excluded_module(module):
                continue
            # Collect imported names
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if name != "*" and not _is_excluded_module(name):
                    imports.append(name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if not _is_excluded_module(module):
                    name = alias.asname if alias.asname else alias.name
                    imports.append(name)

    return imports


def _is_excluded_module(name: str) -> bool:
    """Check if a module/name should be excluded from required_imports."""
    if name in _EXCLUDED_MODULES:
        return True
    # Exclude if it's a submodule of excluded (e.g., unittest.mock)
    parts = name.split(".")
    return parts[0] in _EXCLUDED_MODULES


# ---------------------------------------------------------------------------
# Test method discovery
# ---------------------------------------------------------------------------


def _find_test_methods(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    """Find all test methods/functions in the AST.

    Returns (method_name, node) pairs.
    Handles:
    - unittest TestCase methods (test_* or test* in class)
    - pytest top-level test functions (test_*)
    """
    methods: list[tuple[str, ast.AST]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # unittest-style: methods in TestCase subclass
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and _is_test_method(item.name):
                    methods.append((item.name, item))
        elif isinstance(node, ast.FunctionDef) and _is_test_method(node.name):
            # pytest-style: top-level test functions
            # But skip if inside a class (already handled above)
            if _is_top_level_function(tree, node):
                methods.append((node.name, node))

    return methods


def _is_test_method(name: str) -> bool:
    """Check if a function/method name is a test."""
    return name.startswith("test") and name not in ("setUp", "tearDown", "setUpClass", "tearDownClass")


def _is_top_level_function(tree: ast.Module, target: ast.FunctionDef) -> bool:
    """Check if a FunctionDef is at module level (not inside a class)."""
    for node in tree.body:
        if node is target:
            return True
    return False


# ---------------------------------------------------------------------------
# Contract extraction from a single test method
# ---------------------------------------------------------------------------


def _extract_contracts_from_method(
    node: ast.AST, test_file: str, method_name: str
) -> list[TestContract]:
    """Extract all contracts from a single test method/function."""
    contracts: list[TestContract] = []

    for child in ast.walk(node):
        # unittest-style: self.assertXxx(...)
        if isinstance(child, ast.Call):
            contract = _try_unittest_assertion(child, test_file, method_name)
            if contract:
                contracts.append(contract)

        # pytest-style: assert statements
        elif isinstance(child, ast.Assert):
            contract = _try_pytest_assertion(child, test_file, method_name)
            if contract:
                contracts.append(contract)

        # Context manager: with self.assertRaises(...) or with pytest.raises(...)
        elif isinstance(child, ast.With):
            contract = _try_context_manager_raises(child, test_file, method_name)
            if contract:
                contracts.append(contract)

    return contracts


# ---------------------------------------------------------------------------
# unittest assertion handlers
# ---------------------------------------------------------------------------


def _try_unittest_assertion(
    call: ast.Call, test_file: str, method_name: str
) -> Optional[TestContract]:
    """Try to extract a contract from a unittest self.assertXxx() call."""
    # Must be self.assertXxx
    if not isinstance(call.func, ast.Attribute):
        return None
    if not isinstance(call.func.value, ast.Name):
        return None
    if call.func.value.id != "self":
        return None

    method = call.func.attr

    if method == "assertEqual" and len(call.args) >= 2:
        left = _ast_to_str(call.args[0])
        right = _ast_to_str(call.args[1])
        return TestContract(
            test_file=test_file,
            test_method=method_name,
            assertion=f"{left} == {right}",
            contract_type="value_equality",
        )

    elif method == "assertNotEqual" and len(call.args) >= 2:
        left = _ast_to_str(call.args[0])
        right = _ast_to_str(call.args[1])
        return TestContract(
            test_file=test_file,
            test_method=method_name,
            assertion=f"{left} != {right}",
            contract_type="value_equality",
        )

    elif method == "assertTrue" and len(call.args) >= 1:
        expr = _ast_to_str(call.args[0])
        return TestContract(
            test_file=test_file,
            test_method=method_name,
            assertion=f"assertTrue({expr})",
            contract_type="state_change",
        )

    elif method == "assertFalse" and len(call.args) >= 1:
        expr = _ast_to_str(call.args[0])
        return TestContract(
            test_file=test_file,
            test_method=method_name,
            assertion=f"assertFalse({expr})",
            contract_type="state_change",
        )

    elif method == "assertIsInstance" and len(call.args) >= 2:
        obj = _ast_to_str(call.args[0])
        typ = _ast_to_str(call.args[1])
        return TestContract(
            test_file=test_file,
            test_method=method_name,
            assertion=f"{obj} isinstance {typ}",
            contract_type="type_check",
        )

    elif method == "assertRaises" and len(call.args) >= 1:
        exc_type = _ast_to_str(call.args[0])
        return TestContract(
            test_file=test_file,
            test_method=method_name,
            assertion=f"raises {exc_type}",
            contract_type="raises",
        )

    return None


# ---------------------------------------------------------------------------
# pytest assertion handlers
# ---------------------------------------------------------------------------


def _try_pytest_assertion(
    assert_node: ast.Assert, test_file: str, method_name: str
) -> Optional[TestContract]:
    """Try to extract a contract from a pytest assert statement."""
    test = assert_node.test

    # assert a == b
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        op = test.ops[0]
        left = _ast_to_str(test.left)
        right = _ast_to_str(test.comparators[0])

        if isinstance(op, ast.Eq):
            return TestContract(
                test_file=test_file,
                test_method=method_name,
                assertion=f"{left} == {right}",
                contract_type="value_equality",
            )
        elif isinstance(op, ast.NotEq):
            return TestContract(
                test_file=test_file,
                test_method=method_name,
                assertion=f"{left} != {right}",
                contract_type="value_equality",
            )

    # assert isinstance(obj, Type)
    if isinstance(test, ast.Call):
        if isinstance(test.func, ast.Name) and test.func.id == "isinstance":
            if len(test.args) >= 2:
                obj = _ast_to_str(test.args[0])
                typ = _ast_to_str(test.args[1])
                return TestContract(
                    test_file=test_file,
                    test_method=method_name,
                    assertion=f"{obj} isinstance {typ}",
                    contract_type="type_check",
                )

    return None


# ---------------------------------------------------------------------------
# Context manager raises (both unittest and pytest)
# ---------------------------------------------------------------------------


def _try_context_manager_raises(
    with_node: ast.With, test_file: str, method_name: str
) -> Optional[TestContract]:
    """Extract raises contract from 'with self.assertRaises(E)' or 'with pytest.raises(E)'."""
    for item in with_node.items:
        ctx = item.context_expr
        if not isinstance(ctx, ast.Call):
            continue

        # self.assertRaises(ExcType)
        if isinstance(ctx.func, ast.Attribute):
            if ctx.func.attr == "assertRaises" and len(ctx.args) >= 1:
                exc_type = _ast_to_str(ctx.args[0])
                return TestContract(
                    test_file=test_file,
                    test_method=method_name,
                    assertion=f"raises {exc_type}",
                    contract_type="raises",
                )

            # pytest.raises(ExcType)
            if (
                ctx.func.attr == "raises"
                and isinstance(ctx.func.value, ast.Name)
                and ctx.func.value.id == "pytest"
                and len(ctx.args) >= 1
            ):
                exc_type = _ast_to_str(ctx.args[0])
                return TestContract(
                    test_file=test_file,
                    test_method=method_name,
                    assertion=f"raises {exc_type}",
                    contract_type="raises",
                )

    return None


# ---------------------------------------------------------------------------
# AST to string conversion
# ---------------------------------------------------------------------------


def _ast_to_str(node: ast.AST) -> str:
    """Convert an AST node to a readable string representation."""
    if isinstance(node, ast.Constant):
        return repr(node.value)

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        value = _ast_to_str(node.value)
        return f"{value}.{node.attr}"

    if isinstance(node, ast.Call):
        func = _ast_to_str(node.func)
        args = ", ".join(_ast_to_str(a) for a in node.args)
        return f"{func}({args})"

    if isinstance(node, ast.Subscript):
        value = _ast_to_str(node.value)
        sl = _ast_to_str(node.slice)
        return f"{value}[{sl}]"

    if isinstance(node, ast.BinOp):
        left = _ast_to_str(node.left)
        right = _ast_to_str(node.right)
        op = _binop_symbol(node.op)
        return f"{left} {op} {right}"

    if isinstance(node, ast.UnaryOp):
        operand = _ast_to_str(node.operand)
        if isinstance(node.op, ast.Not):
            return f"not {operand}"
        return f"{operand}"

    if isinstance(node, ast.Tuple):
        elts = ", ".join(_ast_to_str(e) for e in node.elts)
        return f"({elts})"

    if isinstance(node, ast.List):
        elts = ", ".join(_ast_to_str(e) for e in node.elts)
        return f"[{elts}]"

    # Fallback: use ast.unparse if available (Python 3.9+)
    try:
        return ast.unparse(node)
    except Exception:
        return "<unknown>"


def _binop_symbol(op: ast.operator) -> str:
    """Get the symbol for a binary operator."""
    symbols = {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.Div: "/",
        ast.Mod: "%",
        ast.Pow: "**",
    }
    return symbols.get(type(op), "?")


# ---------------------------------------------------------------------------
# Escape code parsing for constant extraction
# ---------------------------------------------------------------------------

# Matches patterns like: \033[NNm or \x1b[NNm (ANSI escape codes)
_ESCAPE_CODE_RE = re.compile(r"\\(?:033|x1b)\[(\d+)m")


def _parse_escape_code_assertion(
    assertion: str,
) -> Optional[tuple[str, str, str, str]]:
    """Parse an assertion like "Fore.BLACK == '\\033[30m'" into components.

    Returns (parent, attr_name, numeric_code, full_escape) or None.
    """
    # Match: Parent.ATTR == 'escape_sequence'
    # The assertion format is: "Fore.BLACK == '\\033[30m'"
    match = re.match(
        r"(\w+)\.(\w+)\s*==\s*['\"](.+?)['\"]",
        assertion,
    )
    if not match:
        return None

    parent = match.group(1)
    attr_name = match.group(2)
    literal = match.group(3)

    # Try to extract the numeric ANSI code from the escape sequence
    code_match = _ESCAPE_CODE_RE.search(literal)
    if not code_match:
        return None

    numeric_code = code_match.group(1)
    return (parent, attr_name, numeric_code, literal)
