"""LLM-driven code improvement — parse responses, plan improvements, run loop."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from architecture_model.quality.code_review import CodeAnalysis, CodeIssue
from architecture_model.quality.code_safety import classify_suggestion, SafetyLevel, SAFE_CHANGE_TYPES
from architecture_model.quality.monitoring import monitored


@dataclass
class ReviewSuggestion:
    description: str
    safety: str  # "safe" | "risky"
    code: str = ""


@dataclass
class ReviewResult:
    assessment: str
    additional_issues: list[str]
    suggestions: list[ReviewSuggestion]


@dataclass
class ImproveResult:
    improved_code: str
    changes: list[dict[str, str]]


@dataclass
class CompareResult:
    winner: str  # "A" | "B" | "TIE"
    rationale: str
    criteria_results: list[dict[str, str]]
    synthesis: str = ""


@dataclass
class ImprovementStep:
    change_type: str
    target: str  # function name or "module"
    description: str
    safety: SafetyLevel
    priority: int  # lower = higher priority


@dataclass
class ImprovementPlan:
    filename: str
    current_score: int
    steps: list[ImprovementStep]
    estimated_score_after: int


@dataclass
class ImprovementReport:
    """Result of an autonomous improvement loop."""
    filename: str
    iterations: int
    initial_score: int
    final_score: int
    changes_applied: list[str]
    changes_skipped: list[str]
    test_passed: bool


def parse_review_response(llm_output: str) -> ReviewResult:
    """Parse LLM review response JSON."""
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        return ReviewResult(assessment=llm_output, additional_issues=[], suggestions=[])
    return ReviewResult(
        assessment=data.get("assessment", ""),
        additional_issues=data.get("additional_issues", []),
        suggestions=[
            ReviewSuggestion(**s) for s in data.get("suggestions", [])
        ],
    )


def parse_improve_response(llm_output: str) -> ImproveResult:
    """Parse LLM improvement response JSON."""
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        return ImproveResult(improved_code="", changes=[])
    return ImproveResult(
        improved_code=data.get("improved_code", ""),
        changes=data.get("changes", []),
    )


def parse_compare_response(llm_output: str) -> CompareResult:
    """Parse LLM comparison response JSON."""
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        return CompareResult(winner="TIE", rationale=llm_output, criteria_results=[])
    return CompareResult(
        winner=data.get("winner", "TIE"),
        rationale=data.get("rationale", ""),
        criteria_results=data.get("criteria_results", []),
        synthesis=data.get("synthesis", ""),
    )


def plan_improvements(analysis: CodeAnalysis) -> ImprovementPlan:
    """Create an improvement plan from static analysis results."""
    steps: list[ImprovementStep] = []
    priority = 0

    for issue in analysis.issues:
        if not issue.fixable:
            continue
        # Map issue codes to change types
        change_type = _issue_to_change_type(issue.code)
        if change_type:
            safety = SAFE_CHANGE_TYPES.get(change_type, None)
            steps.append(ImprovementStep(
                change_type=change_type,
                target=issue.function or "module",
                description=issue.message,
                safety=safety.safety if safety else SafetyLevel.RISKY,
                priority=priority,
            ))
            priority += 1

    # Estimate score improvement: each fixed issue improves by its penalty
    est_improvement = sum(5 for s in steps if s.safety == SafetyLevel.SAFE)
    est_score = min(100, analysis.score + est_improvement)

    return ImprovementPlan(
        filename=analysis.filename,
        current_score=analysis.score,
        steps=steps,
        estimated_score_after=est_score,
    )


def _issue_to_change_type(code: str) -> str | None:
    """Map a CodeIssue code to a safe change type."""
    mapping = {
        "MISSING_MODULE_DOCSTRING": "docstring",
        "MISSING_FUNCTION_DOCSTRING": "docstring",
        "MISSING_RETURN_TYPE": "type_hint",
        "MISSING_PARAM_TYPE": "type_hint",
        "LONG_FUNCTION": "function_split",
        "HIGH_COMPLEXITY": "function_split",
    }
    return mapping.get(code)


@monitored("quality.code_improver")
def improve(
    source: str,
    filename: str,
    *,
    llm_callback: Callable[[str, str, dict], str] | None = None,
    test_command: str = "",
    max_iterations: int = 3,
    target_score: int = 80,
) -> ImprovementReport:
    """Run autonomous improvement loop on a source file.

    Loop: analyze -> plan -> (LLM review if available) -> apply safe changes -> test -> repeat
    Stops when target_score reached or max_iterations exceeded.
    """
    from architecture_model.quality.code_review import analyze_source
    from architecture_model.quality.code_prompts import improve_prompt
    import subprocess

    current_source = source
    changes_applied: list[str] = []
    changes_skipped: list[str] = []
    initial_score = 0
    final_score = 0
    iteration = 0

    for iteration in range(max_iterations):
        analysis = analyze_source(current_source, filename=filename)
        if iteration == 0:
            initial_score = analysis.score
        final_score = analysis.score

        if analysis.score >= target_score:
            break

        plan = plan_improvements(analysis)
        if not plan.steps:
            break

        # If LLM available, get improved code
        if llm_callback:
            prompt = improve_prompt(current_source, analysis, goal="Fix all safe issues")
            try:
                llm_output = llm_callback("code_improve", prompt, {"filename": filename})
                if llm_output:
                    result = parse_improve_response(llm_output)
                    if result.improved_code:
                        # Verify the improved code parses
                        try:
                            import ast
                            ast.parse(result.improved_code)
                            current_source = result.improved_code
                            for change in result.changes:
                                safety = classify_suggestion(change.get("description", ""))
                                if safety == SafetyLevel.SAFE:
                                    changes_applied.append(change.get("description", ""))
                                else:
                                    changes_skipped.append(change.get("description", ""))
                        except SyntaxError:
                            changes_skipped.append("LLM output had syntax errors")
            except Exception:
                pass
        else:
            # No LLM — just report what would be done
            for step in plan.steps:
                changes_skipped.append(f"[no LLM] {step.description}")
            break

    # Run tests if specified
    test_passed = True
    if test_command and changes_applied:
        try:
            result = subprocess.run(
                test_command, shell=True, capture_output=True, timeout=120,
            )
            test_passed = result.returncode == 0
        except Exception:
            test_passed = False

    return ImprovementReport(
        filename=filename, iterations=iteration + 1,
        initial_score=initial_score, final_score=final_score,
        changes_applied=changes_applied, changes_skipped=changes_skipped,
        test_passed=test_passed,
    )
