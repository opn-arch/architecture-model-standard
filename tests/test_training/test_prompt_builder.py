import pytest
from architecture_model.training.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def setup_method(self):
        self.builder = PromptBuilder()
        self.sample_yaml = """meta:
  schema_version: "1.3"
  project: "test"
entities:
  components:
    - id: comp-core
      name: core
      symbols:
        - name: Context
          kind: class
          members: [invoke, forward]
      functions: [main]
relationships:
  - type: depends-on
    from: comp-core
    to: comp-utils
    imports: [echo]"""

        self.sample_contracts = """- Context.invoke: resolves params, calls callback. Raises: UsageError
- Context.forward: delegates to another command
- main: entry point, creates Context and invokes"""

        self.sample_failures = """## Test Failures (3 failed, 10 passed)

### Component: core
- test_invoke_calls_callback: AssertionError: assert None == 42
  Expected: 42
  Actual: None
- test_forward_delegates: AttributeError: 'Context' has no attribute 'forward'"""

    def test_generation_prompt_includes_model(self):
        """User content contains the model YAML."""
        system, user = self.builder.build_generation_prompt(self.sample_yaml)
        assert "comp-core" in user
        assert "Context" in user

    def test_generation_prompt_includes_contracts(self):
        """System prompt includes behavioral contracts when provided."""
        system, user = self.builder.build_generation_prompt(
            self.sample_yaml, contracts_text=self.sample_contracts
        )
        assert "Behavioral Contracts" in system
        assert "resolves params" in system

    def test_generation_prompt_without_contracts(self):
        """Works without contracts (empty contracts section)."""
        system, user = self.builder.build_generation_prompt(self.sample_yaml)
        assert "IMPLEMENT" in system  # Still asks for implementations
        assert "Behavioral Contracts" not in system

    def test_generation_prompt_tells_llm_to_implement(self):
        """Unlike stub prompt, tells LLM to implement bodies."""
        system, user = self.builder.build_generation_prompt(self.sample_yaml)
        assert "IMPLEMENT" in system
        assert "pass" not in system.lower() or "pass the" in system.lower()

    def test_generation_prompt_component_filter(self):
        """When component_filter set, tells LLM to only generate that module."""
        system, user = self.builder.build_generation_prompt(
            self.sample_yaml, component_filter="core"
        )
        assert "ONLY" in user
        assert "'core'" in user

    def test_retry_prompt_includes_previous_code(self):
        """Retry prompt contains the previous (broken) code."""
        prev_code = "class Context:\n    def invoke(self): pass"
        system, user = self.builder.build_retry_prompt(
            self.sample_yaml, prev_code, self.sample_failures, "core"
        )
        assert "class Context:" in user
        assert "def invoke(self): pass" in user

    def test_retry_prompt_includes_failures(self):
        """Retry prompt contains failure descriptions."""
        prev_code = "class Context:\n    pass"
        system, user = self.builder.build_retry_prompt(
            self.sample_yaml, prev_code, self.sample_failures, "core"
        )
        assert "test_invoke_calls_callback" in user
        assert "assert None == 42" in user

    def test_retry_prompt_specifies_component(self):
        """Retry prompt clearly states which component to fix."""
        prev_code = "class Context:\n    pass"
        system, user = self.builder.build_retry_prompt(
            self.sample_yaml, prev_code, self.sample_failures, "core"
        )
        assert "core" in user
        assert "Component to fix" in user

    def test_retry_system_prompt_is_fixing_oriented(self):
        """Retry system prompt focuses on FIXING, not generating from scratch."""
        prev_code = "x = 1"
        system, user = self.builder.build_retry_prompt(
            self.sample_yaml, prev_code, "", "core"
        )
        assert "fixing" in system.lower() or "fix" in system.lower()

    def test_stub_prompt_uses_original(self):
        """stub prompt falls back to original _GENERATE_SYSTEM_PROMPT."""
        system, user = self.builder.build_stub_prompt(self.sample_yaml)
        assert "pass" in system or "..." in system  # Original says use pass/...
        assert user == self.sample_yaml

    def test_estimate_tokens(self):
        """Token estimation is roughly correct (4 chars/token)."""
        system = "a" * 400
        user = "b" * 600
        estimate = self.builder.estimate_tokens(system, user)
        assert estimate == 250  # (400 + 600) / 4
