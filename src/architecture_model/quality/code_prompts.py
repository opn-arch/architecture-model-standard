"""Prompt templates for LLM-driven code review and improvement."""
from __future__ import annotations
from architecture_model.quality.code_review import CodeAnalysis


def review_prompt(source: str, analysis: CodeAnalysis) -> str:
    """Generate a prompt asking LLM to review code quality."""
    issues_text = "\n".join(
        f"- [{i.severity.value.upper()}] {i.code}: {i.message} (line {i.line})"
        for i in analysis.issues
    )
    return f"""Review this Python module for code quality.

**File:** {analysis.filename}
**Score:** {analysis.score}/100
**Functions:** {len(analysis.functions)}

**Static Analysis Issues:**
{issues_text or "(none)"}

**Source Code:**
```python
{source}
```

Please provide:
1. A brief assessment of overall quality
2. Additional issues not caught by static analysis (logic errors, naming, design)
3. Specific improvement suggestions with code snippets
4. For each suggestion, classify as SAFE (auto-applicable) or RISKY (needs human review)

Return as JSON: {{"assessment": "...", "additional_issues": [...], "suggestions": [{{"description": "...", "safety": "safe|risky", "code": "..."}}]}}"""


def improve_prompt(source: str, analysis: CodeAnalysis, *, goal: str = "") -> str:
    """Generate a prompt asking LLM to improve specific code."""
    goal_text = f"\n**Goal:** {goal}" if goal else ""
    return f"""Improve this Python code.{goal_text}

**File:** {analysis.filename}
**Current Score:** {analysis.score}/100

**Source Code:**
```python
{source}
```

**Known Issues:**
{chr(10).join(f"- {i.message}" for i in analysis.issues) or "(none)"}

Provide the improved code as a complete replacement. Preserve all existing functionality.
Explain each change briefly.

Return as JSON: {{"improved_code": "...", "changes": [{{"description": "...", "safety": "safe|risky"}}]}}"""


def compare_prompt(source_a: str, source_b: str, *, criteria: str = "overall quality") -> str:
    """Generate a prompt to compare two implementations."""
    return f"""Compare these two implementations on: {criteria}

**Implementation A:**
```python
{source_a}
```

**Implementation B:**
```python
{source_b}
```

For each criterion, declare a winner (A, B, or TIE) with rationale.
If one is clearly better overall, recommend it. If both have strengths, suggest a synthesis.

Return as JSON: {{"winner": "A|B|TIE", "rationale": "...", "criteria_results": [{{"criterion": "...", "winner": "A|B|TIE", "reason": "..."}}], "synthesis": "..." }}"""


def safe_change_prompt(source: str, *, change_type: str, function_name: str = "") -> str:
    """Generate a prompt for a specific safe change type."""
    target = f" for function '{function_name}'" if function_name else ""
    return f"""Generate a {change_type}{target} for this code.

```python
{source}
```

Requirements:
- For docstrings: use Google-style format, describe purpose/args/returns
- For type hints: infer types from usage patterns and return values
- For dead imports: list imports with no usage in the module
- Preserve all existing code and behavior exactly

Return as JSON: {{"change_type": "{change_type}", "function": "{function_name}", "replacement_code": "..."}}"""
