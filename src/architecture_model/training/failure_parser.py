"""Failure Parser — parses pytest output into structured TestFailure objects.

Enables the retry loop to understand exactly what went wrong and feed
structured error context back to the LLM for regeneration.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestFailure:
    """Structured representation of a single test failure."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    test_name: str  # e.g., "test_basic_functionality"
    test_file: str  # e.g., "tests/test_basic.py"
    error_type: str  # "AssertionError", "ImportError", "AttributeError", etc.
    error_message: str  # The actual error text
    failed_assertion: str | None = None  # The assert line that failed
    expected: str | None = None  # Expected value
    actual: str | None = None  # Actual value
    relevant_component: str | None = None  # Which source module is implicated
    traceback_hint: str = ""  # 1-2 line traceback showing where in source it failed


@dataclass
class FailureReport:
    """Aggregated failure analysis from a test run."""

    failures: list[TestFailure] = field(default_factory=list)
    total_passed: int = 0
    total_failed: int = 0
    total_collected: int = 0
    pass_rate: float = 0.0

    # Grouped analysis
    by_component: dict[str, list[TestFailure]] = field(default_factory=dict)
    by_error_type: dict[str, int] = field(default_factory=dict)

    def format_for_retry_prompt(
        self, component: str | None = None, max_failures: int = 10
    ) -> str:
        """Format failures as LLM-friendly text for retry generation.

        Output format:
        ## Test Failures (X failed, Y passed)

        ### Component: {name}
        - test_name: ErrorType: message
          Expected: ...
          Actual: ...
        """
        lines = [
            f"## Test Failures ({self.total_failed} failed, {self.total_passed} passed)\n"
        ]

        if component:
            failures = self.by_component.get(component, [])
        else:
            failures = self.failures

        failures = failures[:max_failures]

        # Group by component for display
        grouped: dict[str, list[TestFailure]] = defaultdict(list)
        for f in failures:
            grouped[f.relevant_component or "unknown"].append(f)

        for comp, comp_failures in grouped.items():
            lines.append(f"### Component: {comp}")
            for f in comp_failures:
                lines.append(
                    f"- {f.test_name}: {f.error_type}: {f.error_message[:100]}"
                )
                if f.expected:
                    lines.append(f"  Expected: {f.expected[:80]}")
                if f.actual:
                    lines.append(f"  Actual: {f.actual[:80]}")
                if f.failed_assertion:
                    lines.append(f"  Assertion: {f.failed_assertion[:80]}")
            lines.append("")

        return "\n".join(lines)


class FailureParser:
    """Parses pytest output into structured failure reports."""

    def parse(self, pytest_output: str, package_name: str) -> FailureReport:
        """Parse pytest --tb=short -v output into a FailureReport.

        Args:
            pytest_output: Combined stdout+stderr from pytest run
            package_name: The package name (for component mapping)
        """
        # 1. Parse summary line
        total_passed, total_failed, total_collected = self._parse_summary(
            pytest_output
        )

        # 2. Parse individual failure blocks
        failures = self._parse_failure_blocks(pytest_output, package_name)

        # 2b. Parse collection errors (ImportError, ModuleNotFoundError, etc.)
        collection_errors = self._parse_collection_errors(pytest_output, package_name)
        failures.extend(collection_errors)

        # 3. Build grouped views
        by_component: dict[str, list[TestFailure]] = defaultdict(list)
        by_error_type: dict[str, int] = defaultdict(int)
        for f in failures:
            by_component[f.relevant_component or "unknown"].append(f)
            by_error_type[f.error_type] += 1

        pass_rate = total_passed / total_collected if total_collected > 0 else 0.0

        return FailureReport(
            failures=failures,
            total_passed=total_passed,
            total_failed=total_failed,
            total_collected=total_collected,
            pass_rate=pass_rate,
            by_component=dict(by_component),
            by_error_type=dict(by_error_type),
        )

    def _parse_summary(self, output: str) -> tuple[int, int, int]:
        """Parse the pytest summary line.

        Examples:
            "5 passed, 3 failed in 1.2s"
            "225 passed, 1 skipped in 0.48s"
            "10 passed, 5 failed, 2 error in 3.4s"
        """
        passed = 0
        failed = 0
        errors = 0

        m = re.search(r"(\d+) passed", output)
        if m:
            passed = int(m.group(1))

        m = re.search(r"(\d+) failed", output)
        if m:
            failed = int(m.group(1))

        m = re.search(r"(\d+) error", output)
        if m:
            errors = int(m.group(1))

        # "collected X items / Y errors"  
        m = re.search(r"collected (\d+) item", output)
        m_errors_in_collection = re.search(r"(\d+) error", output)
        if m:
            collected = int(m.group(1))
            # Add collection errors to collected count (they represent tests
            # that couldn't even run)
            if m_errors_in_collection:
                collected += int(m_errors_in_collection.group(1))
        else:
            collected = passed + failed + errors

        # Treat collection errors as failures for pass_rate purposes
        failed += errors

        return passed, failed, collected

    def _parse_collection_errors(
        self, output: str, package_name: str
    ) -> list[TestFailure]:
        """Parse collection errors (ImportError, ModuleNotFoundError, etc.).

        These appear as 'ERROR collecting tests/test_foo.py' blocks with
        tracebacks showing import chains. They indicate fundamental issues
        like missing modules or broken imports.
        """
        errors: list[TestFailure] = []

        # Find ERROR collecting blocks
        error_pattern = re.compile(
            r"_+ ERROR collecting ([\w/\\.]+) _+\n(.*?)(?=\n_+ ERROR|\n={5,}|\n!{5,})",
            re.DOTALL,
        )
        for match in error_pattern.finditer(output):
            test_file = match.group(1)
            block = match.group(2)

            # Extract error type and message from the "E   ..." line
            e_line_match = re.search(r"^E\s+(\w+Error): (.+)$", block, re.MULTILINE)
            if not e_line_match:
                e_line_match = re.search(r"^E\s+(.+)$", block, re.MULTILINE)

            if e_line_match:
                if e_line_match.lastindex == 2:
                    error_type = e_line_match.group(1)
                    error_message = e_line_match.group(2)
                else:
                    error_type = "CollectionError"
                    error_message = e_line_match.group(1)
            else:
                error_type = "CollectionError"
                error_message = f"Failed to collect {test_file}"

            # Try to find which component is causing the error
            relevant_component = self._map_to_component(block, test_file, package_name)

            # Build a traceback hint from the block
            traceback_hint = ""
            lines = block.strip().split("\n")
            # Find lines referencing the package
            pkg_lines = [
                l.strip() for l in lines
                if package_name in l and "in <module>" not in l
            ]
            if pkg_lines:
                traceback_hint = pkg_lines[-1][:120]

            errors.append(TestFailure(
                test_name=f"COLLECTION_{Path(test_file).stem}",
                test_file=test_file,
                error_type=error_type,
                error_message=error_message,
                relevant_component=relevant_component,
                traceback_hint=traceback_hint,
            ))

        return errors

    def _parse_failure_blocks(
        self, output: str, package_name: str
    ) -> list[TestFailure]:
        """Parse FAILURES section of pytest output."""
        failures: list[TestFailure] = []

        # Parse FAILED lines from short test summary info
        failed_pattern = re.compile(
            r"FAILED\s+([\w/\\.]+)::(\w+)(?:\s*-\s*(.+))?"
        )
        for match in failed_pattern.finditer(output):
            test_file = match.group(1)
            test_name = match.group(2)
            error_summary = match.group(3) or ""

            # Parse error type and message
            error_type, error_message = self._parse_error_summary(error_summary)

            # Try to find the full traceback block for this test
            tb_block = self._find_traceback_block(output, test_name)

            # Extract assertion details
            failed_assertion = None
            expected = None
            actual = None
            traceback_hint = ""

            if tb_block:
                failed_assertion = self._extract_assertion_line(tb_block)
                expected, actual = self._extract_expected_actual(tb_block)
                traceback_hint = self._extract_traceback_hint(
                    tb_block, package_name
                )

            # Also try to extract expected/actual from the error_message itself
            if expected is None and actual is None and "==" in error_message:
                expected, actual = self._extract_expected_actual_from_message(
                    error_message
                )

            # Map to component
            relevant_component = self._map_to_component(
                tb_block or "", test_file, package_name
            )

            failures.append(
                TestFailure(
                    test_name=test_name,
                    test_file=test_file,
                    error_type=error_type,
                    error_message=error_message,
                    failed_assertion=failed_assertion,
                    expected=expected,
                    actual=actual,
                    relevant_component=relevant_component,
                    traceback_hint=traceback_hint,
                )
            )

        # If no FAILED lines found, try parsing FAILURES section directly
        if not failures and "FAILURES" in output:
            failures = self._parse_failures_section(output, package_name)

        return failures

    def _parse_error_summary(self, error_summary: str) -> tuple[str, str]:
        """Parse 'AssertionError: assert x == y' into (type, message)."""
        if ":" in error_summary:
            parts = error_summary.split(":", 1)
            return parts[0].strip(), parts[1].strip()
        if error_summary:
            return error_summary.strip(), ""
        return "Unknown", ""

    def _find_traceback_block(self, output: str, test_name: str) -> str | None:
        """Find the traceback block for a specific test in the FAILURES section."""
        pattern = re.compile(
            rf"_{3,}\s*{re.escape(test_name)}\s*_{3,}(.*?)(?=_{3,}|\Z)",
            re.DOTALL,
        )
        match = pattern.search(output)
        return match.group(1) if match else None

    def _extract_assertion_line(self, tb_block: str) -> str | None:
        """Extract the assert statement that failed."""
        for line in tb_block.split("\n"):
            stripped = line.strip()
            if stripped.startswith(">") and "assert" in stripped:
                return stripped.lstrip("> ").strip()
            if stripped.startswith("E") and "assert" in stripped:
                return stripped.lstrip("E ").strip()
        return None

    def _extract_expected_actual(
        self, tb_block: str
    ) -> tuple[str | None, str | None]:
        """Extract expected and actual values from assertion comparison in traceback.

        pytest shows:
        E       assert 'actual' == 'expected'
        E       AssertionError: assert 'actual' == 'expected'
        """
        expected = None
        actual = None

        for line in tb_block.split("\n"):
            stripped = line.strip()
            if "==" in stripped and (
                "assert" in stripped or stripped.startswith("E")
            ):
                parts = stripped.split("==", 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    left = re.sub(
                        r"^[E>\s]*(AssertionError:\s*)?assert\s*", "", left
                    )
                    actual = left.strip()[:100]
                    expected = parts[1].strip()[:100]
                    break

        return expected, actual

    def _extract_expected_actual_from_message(
        self, error_message: str
    ) -> tuple[str | None, str | None]:
        """Extract expected/actual from the error message line itself.

        E.g., "assert 'actual_value' == 'expected_value'"
        """
        if "==" not in error_message:
            return None, None

        parts = error_message.split("==", 1)
        if len(parts) == 2:
            left = parts[0].strip()
            left = re.sub(r"^assert\s*", "", left)
            actual = left.strip()[:100]
            expected = parts[1].strip()[:100]
            return expected, actual

        return None, None

    def _extract_traceback_hint(self, tb_block: str, package_name: str) -> str:
        """Extract 1-2 relevant lines from the traceback (source location)."""
        hints: list[str] = []
        for line in tb_block.split("\n"):
            if package_name in line and "File" in line:
                hints.append(line.strip())
            if len(hints) >= 2:
                break
        return "\n".join(hints)

    def _map_to_component(
        self, tb_block: str, test_file: str, package_name: str
    ) -> str | None:
        """Map a failure to its source component.

        Strategy:
        1. Look for source file references in traceback
        2. Fall back to test file name (test_core.py -> "core")
        """
        # Strategy 1: traceback references
        pattern = re.compile(rf"{re.escape(package_name)}/(\w+)\.py")
        match = pattern.search(tb_block)
        if match:
            return match.group(1)

        # Strategy 2: test file name
        if "/" in test_file or "\\" in test_file:
            test_basename = Path(test_file).stem
        else:
            test_basename = test_file
        if test_basename.startswith("test_"):
            return test_basename[5:]

        return None

    def _parse_failures_section(
        self, output: str, package_name: str
    ) -> list[TestFailure]:
        """Parse the FAILURES section when FAILED summary lines aren't available."""
        failures: list[TestFailure] = []
        if "FAILURES" not in output:
            return failures

        section = output.split("FAILURES")[1]
        blocks = re.split(r"_{3,}\s*(\w+)\s*_{3,}", section)

        # blocks alternates: [pre, test_name, content, test_name, content, ...]
        for i in range(1, len(blocks) - 1, 2):
            test_name = blocks[i]
            content = blocks[i + 1] if i + 1 < len(blocks) else ""

            error_type = "Unknown"
            error_message = ""
            for line in content.split("\n"):
                if line.strip().startswith("E") and "Error" in line:
                    parts = line.strip().lstrip("E ").split(":", 1)
                    if len(parts) == 2:
                        error_type = parts[0].strip()
                        error_message = parts[1].strip()
                    break

            component = self._map_to_component(content, "", package_name)

            failures.append(
                TestFailure(
                    test_name=test_name,
                    test_file="",
                    error_type=error_type,
                    error_message=error_message,
                    relevant_component=component,
                    traceback_hint=self._extract_traceback_hint(
                        content, package_name
                    ),
                )
            )

        return failures
