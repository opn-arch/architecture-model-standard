"""Prompt construction for test-guided code generation.

Builds system prompts and user content for two scenarios:
1. Initial generation: model YAML + behavioral contracts → working code
2. Retry generation: model YAML + previous code + failure context → fixed code
"""

from __future__ import annotations


# The key difference from _GENERATE_SYSTEM_PROMPT: this tells the LLM to
# IMPLEMENT method bodies, not use 'pass' stubs.
_GENERATE_WITH_CONTRACTS_SYSTEM = """\
You are an architecture-to-code compiler. Given a UAM architecture model YAML \
with code-level detail AND behavioral contracts from the test suite, generate \
Python source code that:
1. Matches the structural specification exactly (class names, method signatures, imports)
2. IMPLEMENTS method bodies to satisfy the behavioral contracts
3. Produces code that will pass the described test assertions

Rules:
1. Each component entity becomes ONE Python module (filename = component name).
2. If the component has 'symbols', use EXACTLY those class/type names with correct inheritance.
3. Each symbol's 'members' become methods with WORKING implementations.
4. Each symbol's 'supers' become base classes.
5. If the component has 'functions', create those as top-level functions with WORKING implementations.
6. For depends-on relationships with 'imports': add `from .{{target}} import {{symbols}}`.
7. Use type hints on all methods and functions.
8. IMPLEMENT all method/function bodies based on the behavioral contracts below.
9. If a contract says "raises X when Y" → implement that error handling.
10. If a contract says "returns Z" → ensure the method returns that value.
11. If no contract exists for a method, implement reasonable default behavior based on the method name and class context.

{contracts_section}

Output format:
- Separate modules with '# component_name.py' comment headers (matching component names exactly)
- Import statements at the top of each module (stdlib first, then relative)
- Output ONLY Python code — no markdown fences, no explanations."""


_RETRY_SYSTEM = """\
You are fixing Python code that has test failures. Given:
1. The architecture model (what the code SHOULD look like structurally)
2. The previous code attempt (which has bugs)
3. The test failures (what went wrong)

Your job: produce FIXED code for the specified component that:
- Maintains the same structure (class names, method names, imports)
- Fixes the specific test failures described
- Does NOT introduce new bugs

Focus on fixing the EXACT errors described. Do not rewrite unrelated code.

Output ONLY the fixed Python code for the specified component — no markdown fences, no explanations."""


class PromptBuilder:
    """Builds prompts for test-guided code generation."""

    def build_generation_prompt(
        self,
        model_yaml: str,
        contracts_text: str = "",
        component_filter: str | None = None,
    ) -> tuple[str, str]:
        """Build a prompt for initial code generation with behavioral contracts.

        Args:
            model_yaml: The architecture model YAML (enriched, possibly compacted)
            contracts_text: Formatted behavioral contracts from TestContracts.summary_for_prompt()
            component_filter: If set, instruct LLM to only generate this component

        Returns:
            Tuple of (system_prompt, user_content)
        """
        # Build contracts section
        if contracts_text:
            contracts_section = f"## Behavioral Contracts (from test suite)\n\n{contracts_text}"
        else:
            contracts_section = ""

        system = _GENERATE_WITH_CONTRACTS_SYSTEM.format(contracts_section=contracts_section)

        # Build user content
        user_parts = []
        if component_filter:
            user_parts.append(f"Generate ONLY the '{component_filter}' component.\n")
        user_parts.append(model_yaml)

        return system, "\n".join(user_parts)

    def build_retry_prompt(
        self,
        model_yaml: str,
        previous_code: str,
        failure_text: str,
        component: str,
    ) -> tuple[str, str]:
        """Build a targeted retry prompt for fixing a specific failing component.

        Args:
            model_yaml: Architecture model YAML (can be component-specific slice)
            previous_code: The previous code for this component that had failures
            failure_text: Formatted failure report from FailureReport.format_for_retry_prompt()
            component: Name of the component being fixed

        Returns:
            Tuple of (system_prompt, user_content)
        """
        user_parts = [
            f"## Component to fix: {component}\n",
            "## Architecture Model (structural specification)\n",
            model_yaml,
            "\n## Previous Code (has bugs)\n",
            f"```python\n{previous_code}\n```",
            "\n## Test Failures to Fix\n",
            failure_text,
            f"\nGenerate the FIXED code for '{component}.py'. Fix the failures above while maintaining the structural specification.",
        ]

        return _RETRY_SYSTEM, "\n".join(user_parts)

    def build_stub_prompt(self, model_yaml: str) -> tuple[str, str]:
        """Build a prompt for stub-only generation (original behavior, for fallback).

        Uses the original _GENERATE_SYSTEM_PROMPT pattern that generates `pass` bodies.
        """
        from architecture_model.training.surrogate import _GENERATE_SYSTEM_PROMPT

        return _GENERATE_SYSTEM_PROMPT, model_yaml

    def estimate_tokens(self, system: str, user: str) -> int:
        """Rough token count estimate (4 chars per token)."""
        return (len(system) + len(user)) // 4
