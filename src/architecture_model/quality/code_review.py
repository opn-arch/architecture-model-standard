"""Static code analysis engine — complexity, docstrings, type hints, code smells."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from architecture_model.quality.monitoring import monitored


class IssueSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CodeIssue:
    code: str           # e.g., "MISSING_FUNCTION_DOCSTRING"
    severity: IssueSeverity
    message: str
    line: int = 0
    function: str = ""
    fixable: bool = False  # safe for auto-apply


@dataclass
class FunctionAnalysis:
    name: str
    line: int
    complexity: int         # cyclomatic complexity
    length: int             # body line count
    param_count: int
    has_docstring: bool
    has_return_type: bool
    untyped_params: list[str]
    issues: list[CodeIssue] = field(default_factory=list)


@dataclass
class CodeAnalysis:
    filename: str
    line_count: int
    has_module_docstring: bool
    functions: list[FunctionAnalysis]
    issues: list[CodeIssue]
    score: int  # 0-100


def _cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count cyclomatic complexity: 1 + decision points."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp)):
            complexity += 1
        elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # and/or add branches
            complexity += len(child.values) - 1
        elif isinstance(child, ast.Match):
            complexity += len(child.cases)
    return complexity


def _function_length(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count lines in function body."""
    if not node.body:
        return 0
    first = node.body[0].lineno
    last = node.body[-1].end_lineno or node.body[-1].lineno
    return last - first + 1


def _analyze_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionAnalysis:
    """Analyze a single function."""
    issues: list[CodeIssue] = []
    has_docstring = bool(ast.get_docstring(node))
    complexity = _cyclomatic_complexity(node)
    length = _function_length(node)

    # Skip self/cls
    params = [a for a in node.args.args if a.arg not in ("self", "cls")]
    param_count = len(params)
    untyped = [a.arg for a in params if a.annotation is None]
    has_return = node.returns is not None

    if not has_docstring and not node.name.startswith("_"):
        issues.append(CodeIssue(
            code="MISSING_FUNCTION_DOCSTRING", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' has no docstring",
            line=node.lineno, function=node.name, fixable=True,
        ))
    if not has_return and not node.name.startswith("_"):
        issues.append(CodeIssue(
            code="MISSING_RETURN_TYPE", severity=IssueSeverity.INFO,
            message=f"Function '{node.name}' has no return type annotation",
            line=node.lineno, function=node.name, fixable=True,
        ))
    for p in untyped:
        if not node.name.startswith("_"):
            issues.append(CodeIssue(
                code="MISSING_PARAM_TYPE", severity=IssueSeverity.INFO,
                message=f"Parameter '{p}' in '{node.name}' has no type annotation",
                line=node.lineno, function=node.name, fixable=True,
            ))
    if length > 50:
        issues.append(CodeIssue(
            code="LONG_FUNCTION", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' is {length} lines (>50)",
            line=node.lineno, function=node.name, fixable=True,
        ))
    if param_count > 6:
        issues.append(CodeIssue(
            code="TOO_MANY_PARAMS", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' has {param_count} parameters (>6)",
            line=node.lineno, function=node.name,
        ))
    if complexity > 10:
        issues.append(CodeIssue(
            code="HIGH_COMPLEXITY", severity=IssueSeverity.WARNING,
            message=f"Function '{node.name}' has cyclomatic complexity {complexity} (>10)",
            line=node.lineno, function=node.name, fixable=True,
        ))

    return FunctionAnalysis(
        name=node.name, line=node.lineno, complexity=complexity,
        length=length, param_count=param_count, has_docstring=has_docstring,
        has_return_type=has_return, untyped_params=untyped, issues=issues,
    )


def _score(analysis_issues: list[CodeIssue], func_count: int) -> int:
    """Compute code quality score 0-100."""
    if func_count == 0:
        return 100
    penalty = 0
    for issue in analysis_issues:
        if issue.severity == IssueSeverity.ERROR:
            penalty += 15
        elif issue.severity == IssueSeverity.WARNING:
            penalty += 5
        elif issue.severity == IssueSeverity.INFO:
            penalty += 2
    # Normalize: max penalty = 100
    return max(0, 100 - min(100, penalty))


@monitored("quality.code_review", quality=lambda r: {"score": r.score, "issues": len(r.issues)})
def analyze_source(source: str, *, filename: str = "<unknown>") -> CodeAnalysis:
    """Analyze Python source code for quality issues."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return CodeAnalysis(
            filename=filename, line_count=source.count("\n") + 1,
            has_module_docstring=False, functions=[], issues=[
                CodeIssue(code="SYNTAX_ERROR", severity=IssueSeverity.ERROR,
                          message="Failed to parse source", fixable=False)
            ], score=0,
        )

    has_module_doc = bool(ast.get_docstring(tree))
    all_issues: list[CodeIssue] = []

    if not has_module_doc:
        all_issues.append(CodeIssue(
            code="MISSING_MODULE_DOCSTRING", severity=IssueSeverity.INFO,
            message="Module has no docstring", fixable=True,
        ))

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fa = _analyze_function(node)
            functions.append(fa)
            all_issues.extend(fa.issues)

    return CodeAnalysis(
        filename=filename,
        line_count=source.count("\n") + 1,
        has_module_docstring=has_module_doc,
        functions=functions,
        issues=all_issues,
        score=_score(all_issues, len(functions)),
    )


def analyze_file(filepath: str) -> CodeAnalysis:
    """Analyze a Python file."""
    with open(filepath) as f:
        source = f.read()
    return analyze_source(source, filename=filepath)


def analyze_component(files: list[str]) -> list[CodeAnalysis]:
    """Analyze all files in a component."""
    return [analyze_file(f) for f in files if f.endswith(".py")]
