"""Test-Guided Generator: core orchestrator for generate → test → analyze → regenerate cycle.

Coordinates the retry loop that produces code passing a project's test suite by:
1. Mining behavioral contracts from tests
2. Generating initial code via surrogate LLM
3. Running tests on materialized code
4. Parsing failures and retrying failing components
5. Iterating until convergence or max retries
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from architecture_model.core.merger import compact_for_generation, enrich_from_manifest
from architecture_model.core.parser import dump_model
from architecture_model.core.types import ArchitectureModel
from architecture_model.training.code_writer import CodeWriter, MaterializedPackage
from architecture_model.training.failure_parser import FailureParser, FailureReport
from architecture_model.training.prompt_builder import PromptBuilder
from architecture_model.training.surrogate import Surrogate
from architecture_model.training.test_contract_miner import TestContractMiner, TestContracts
from architecture_model.training.test_runner import TestRunner


@dataclass
class GenerationAttempt:
    """Record of one generation attempt in the retry loop."""

    __test__ = False  # Prevent pytest collection

    iteration: int
    code: str
    pass_rate: float
    failures: FailureReport
    time_seconds: float
    components_regenerated: list[str] = field(default_factory=list)


@dataclass
class TestGuidedResult:
    """Final result of the test-guided generation process."""

    __test__ = False  # Prevent pytest collection

    final_code: str
    final_pass_rate: float
    iterations: int
    attempts: list[GenerationAttempt] = field(default_factory=list)
    converged: bool = False
    structural_score: float | None = None


class TestGuidedGenerator:
    """Generates code that passes tests via iterative refinement.

    Orchestrates the full test-guided generation pipeline:
    model + manifest → enrich → mine contracts → generate → test → retry loop

    The test_runner dependency is stored for use by Task 6 (per-component
    regeneration with venv isolation) but this class runs pytest directly
    via subprocess for the retry loop iterations.
    """

    __test__ = False  # Prevent pytest collection

    _MAX_COMPONENTS_PER_RETRY = 3

    def __init__(
        self,
        surrogate: Surrogate,
        test_runner: TestRunner,
        contract_miner: TestContractMiner,
        prompt_builder: PromptBuilder,
        code_writer: CodeWriter,
        failure_parser: FailureParser,
        max_retries: int = 10,
        convergence_threshold: int = 3,
    ) -> None:
        self._surrogate = surrogate
        self._test_runner = test_runner
        self._contract_miner = contract_miner
        self._prompt_builder = prompt_builder
        self._code_writer = code_writer
        self._failure_parser = failure_parser
        self._max_retries = max_retries
        self._convergence_threshold = convergence_threshold

    async def generate(
        self,
        model: ArchitectureModel,
        manifest: dict,
        repo_path: Path,
        package_name: str,
    ) -> TestGuidedResult:
        """Full test-guided generation pipeline.

        Args:
            model: The architecture model describing the target system.
            manifest: Reality manifest dict (from AST scanning).
            repo_path: Path to the original repo (for tests and contracts).
            package_name: The package being generated (e.g., "click").

        Returns:
            TestGuidedResult with final code, pass rate, and attempt history.
        """
        # 1. Enrich model with manifest data
        enrichment = enrich_from_manifest(model, manifest)
        enriched_model = enrichment.model

        # 2. Compact for LLM generation
        compacted = compact_for_generation(enriched_model)

        # 3. Dump to YAML string
        model_dict = dump_model(compacted)
        model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False)

        # 4. Mine contracts from test suite
        contracts = self._contract_miner.mine(repo_path, package_name)

        # 5. Initial generation
        t0 = time.time()
        code = await self._initial_generation(model_yaml, contracts)
        gen_time = time.time() - t0

        # 6. Materialize and test
        tmp_dir = Path(tempfile.mkdtemp(prefix="tgg_"))
        attempts: list[GenerationAttempt] = []
        package: MaterializedPackage | None = None

        try:
            package = self._code_writer.materialize(code, package_name, tmp_dir)
            self._code_writer.patch_for_testing(package, repo_path)

            # Run tests
            pytest_output = self._run_tests(package.package_dir, package_name)
            failures = self._failure_parser.parse(pytest_output, package_name)

            attempts.append(GenerationAttempt(
                iteration=1,
                code=code,
                pass_rate=failures.pass_rate,
                failures=failures,
                time_seconds=gen_time,
                components_regenerated=[],
            ))

            # 7. If all tests pass, we're done
            if failures.pass_rate >= 1.0:
                return TestGuidedResult(
                    final_code=code,
                    final_pass_rate=failures.pass_rate,
                    iterations=1,
                    attempts=attempts,
                    converged=True,
                    structural_score=None,
                )

            # 8. Retry loop
            iteration = 1
            while iteration <= self._max_retries:
                if self._check_convergence(attempts):
                    break

                iteration += 1
                t0 = time.time()

                # Per-component targeted regeneration
                code, regenerated = await self._targeted_retry(
                    failures=failures,
                    model_yaml=model_yaml,
                    contracts=contracts,
                    current_code=code,
                )

                retry_time = time.time() - t0

                # Re-materialize and test
                self._code_writer.cleanup(package)
                package = self._code_writer.materialize(code, package_name, tmp_dir)
                self._code_writer.patch_for_testing(package, repo_path)

                pytest_output = self._run_tests(package.package_dir, package_name)
                failures = self._failure_parser.parse(pytest_output, package_name)

                attempts.append(GenerationAttempt(
                    iteration=iteration,
                    code=code,
                    pass_rate=failures.pass_rate,
                    failures=failures,
                    time_seconds=retry_time,
                    components_regenerated=regenerated,
                ))

                # Check if all tests pass
                if failures.pass_rate >= 1.0:
                    break

            converged = self._check_convergence(attempts) or failures.pass_rate >= 1.0

            return TestGuidedResult(
                final_code=code,
                final_pass_rate=failures.pass_rate,
                iterations=len(attempts),
                attempts=attempts,
                converged=converged,
                structural_score=None,
            )

        finally:
            # Always cleanup materialized package and temp directory
            if package is not None:
                try:
                    self._code_writer.cleanup(package)
                except Exception:
                    pass
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _initial_generation(
        self, model_yaml: str, contracts: TestContracts
    ) -> str:
        """Generate initial code using enriched model + contracts."""
        contracts_text = contracts.summary_for_prompt("")
        system, user = self._prompt_builder.build_generation_prompt(
            model_yaml, contracts_text, None
        )
        return await self._surrogate.generate_with_prompt(system, user)

    async def _retry_component(
        self,
        component: str,
        model_yaml: str,
        previous_code: str,
        failures: FailureReport,
        contracts: TestContracts,
    ) -> str:
        """Regenerate a single failing component with failure context."""
        failure_text = failures.format_for_retry_prompt(component)
        system, user = self._prompt_builder.build_retry_prompt(
            model_yaml, previous_code, failure_text, component
        )
        return await self._surrogate.generate_with_prompt(system, user)

    async def _targeted_retry(
        self,
        failures: FailureReport,
        model_yaml: str,
        contracts: TestContracts,
        current_code: str,
    ) -> tuple[str, list[str]]:
        """Regenerate only the failing component(s), returning updated full code.

        Identifies the worst-failing components, regenerates each via the
        surrogate LLM with failure context, and splices the new code back
        into the full multi-module output.

        Returns:
            Tuple of (updated_code, list_of_regenerated_component_names).
        """
        components_to_fix = self._identify_failing_components(failures)
        regenerated: list[str] = []

        code = current_code
        for component in components_to_fix:
            component_code = self._extract_component_code(code, component)
            fixed_code = await self._retry_component(
                component=component,
                model_yaml=model_yaml,
                previous_code=component_code,
                failures=failures,
                contracts=contracts,
            )
            code = self._splice_component(code, component, fixed_code)
            regenerated.append(component)

        return code, regenerated

    def _check_convergence(self, attempts: list[GenerationAttempt]) -> bool:
        """True if last N attempts show no pass_rate improvement.

        Convergence is detected when the last `convergence_threshold` attempts
        have no improvement (each attempt's pass_rate <= the one before it).
        """
        n = self._convergence_threshold
        if len(attempts) < n:
            return False

        recent = attempts[-n:]
        # Check if any attempt improved over its predecessor
        for i in range(1, len(recent)):
            if recent[i].pass_rate > recent[i - 1].pass_rate:
                return False
        return True

    def _run_tests(self, package_dir: Path, package_name: str) -> str:
        """Run pytest on the materialized package and return raw output.

        Uses subprocess directly (not TestRunner) since we're testing
        throwaway generated code that changes each iteration.
        """
        try:
            result = subprocess.run(
                [
                    "python", "-m", "pytest",
                    "tests/",
                    "--tb=short",
                    "-v",
                    "--timeout=60",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(package_dir),
            )
            return result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return "TIMEOUT: pytest timed out after 120s\n0 passed, 0 failed in 120s"
        except OSError as e:
            return f"ERROR: {e}\n0 passed, 0 failed in 0s"

    def _identify_failing_components(self, failures: FailureReport) -> list[str]:
        """Identify components with the most failures, ordered by severity."""
        if not failures.by_component:
            return []

        # Sort by number of failures descending
        sorted_components = sorted(
            failures.by_component.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )
        # Return top worst components (limited to avoid over-retrying)
        return [comp for comp, _ in sorted_components[:self._MAX_COMPONENTS_PER_RETRY]]

    def _extract_component_code(self, full_code: str, component: str) -> str:
        """Extract code for a specific component from multi-module code.

        Looks for '# component.py' headers to find the component's code block.
        """
        header_pattern = re.compile(
            r"^#\s*([\w._/\-]+\.py)\s*$",
            re.MULTILINE,
        )
        matches = list(header_pattern.finditer(full_code))

        for i, match in enumerate(matches):
            module_name = match.group(1)
            # Normalize: strip path prefixes
            stem = Path(module_name).stem
            if stem == component:
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(full_code)
                return full_code[start:end].strip()

        # Fallback: return all code if component not found
        return full_code

    def _splice_component(
        self, full_code: str, component: str, new_code: str
    ) -> str:
        """Replace a component's section with new implementation.

        If the component is not found in the code, appends it as a new section.
        """
        header_pattern = re.compile(
            r"^#\s*([\w._/\-]+\.py)\s*$",
            re.MULTILINE,
        )
        matches = list(header_pattern.finditer(full_code))

        for i, match in enumerate(matches):
            module_name = match.group(1)
            stem = Path(module_name).stem
            if stem == component:
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(full_code)
                # Replace the content between headers
                return full_code[:start] + "\n" + new_code + "\n" + full_code[end:]

        # If component not found, append it
        return full_code + f"\n# {component}.py\n{new_code}\n"
