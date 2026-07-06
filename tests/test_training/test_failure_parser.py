"""Tests for FailureParser — parses pytest output into structured TestFailure objects."""
from __future__ import annotations

import pytest

from architecture_model.training.failure_parser import (
    FailureParser,
    FailureReport,
    TestFailure,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic pytest output samples
# ---------------------------------------------------------------------------

SAMPLE_SHORT_SUMMARY = """\
============================= short test summary info ============================
FAILED tests/test_basic.py::test_basic_functionality - AssertionError: assert 'I EXECUTED' in ''
FAILED tests/test_basic.py::test_return_values - AssertionError: assert None == 42
FAILED tests/test_types.py::test_choice_type - AssertionError: assert 'invalid' == 'valid'
========================= 3 failed, 10 passed in 0.5s =========================
"""

SAMPLE_IMPORT_ERROR = """\
============================= short test summary info ============================
FAILED tests/test_basic.py::test_basic_functionality - ImportError: cannot import name 'Command' from 'click'
========================= 1 failed, 0 passed, 5 error in 0.2s =========================
"""

SAMPLE_VERBOSE_TRACEBACKS = """\
================================== FAILURES ===================================
___________________________ test_basic_functionality ___________________________

    def test_basic_functionality(runner):
        @click.command()
        def cli():
            click.echo("I EXECUTED")

        result = runner.invoke(cli, [])
>       assert not result.exception
E       AssertionError: assert not AttributeError("module 'click' has no attribute 'command'")

tests/test_basic.py:18: AssertionError
___________________________ test_return_values ___________________________

    def test_return_values():
>       with cli.make_context("foo", []) as ctx:
E       AttributeError: 'function' object has no attribute 'make_context'

tests/test_basic.py:54: AssertionError
============================= short test summary info ============================
FAILED tests/test_basic.py::test_basic_functionality - AssertionError: assert not AttributeError(...)
FAILED tests/test_basic.py::test_return_values - AttributeError: 'function' object has no attribute 'make_context'
========================= 2 failed, 5 passed in 0.3s =========================
"""

SAMPLE_WITH_COLLECTED = """\
collected 20 items

tests/test_core.py::test_parse PASSED
tests/test_core.py::test_validate PASSED
tests/test_core.py::test_load FAILED

============================= short test summary info ============================
FAILED tests/test_core.py::test_load - AssertionError: assert 'loaded' == 'error'
========================= 1 failed, 19 passed in 1.2s =========================
"""

SAMPLE_TRACEBACK_WITH_COMPONENT = """\
================================== FAILURES ===================================
___________________________ test_parse_model ___________________________

    def test_parse_model():
        from architecture_model.training.pipeline import TrainingPipeline
        p = TrainingPipeline()
>       result = p.run()
E       AssertionError: assert result.success

    File "/project/src/architecture_model/training/pipeline.py", line 42, in run
        return self._execute()

tests/test_pipeline.py:12: AssertionError
============================= short test summary info ============================
FAILED tests/test_pipeline.py::test_parse_model - AssertionError: assert result.success
========================= 1 failed, 4 passed in 0.8s =========================
"""

SAMPLE_EQUALITY_ASSERTION = """\
============================= short test summary info ============================
FAILED tests/test_core.py::test_output_format - AssertionError: assert 'actual_value' == 'expected_value'
========================= 1 failed, 5 passed in 0.4s =========================
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseSummaryLine:
    """Test _parse_summary extracts passed/failed/collected counts."""

    def test_parses_summary_line(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_SHORT_SUMMARY, "click")

        assert report.total_passed == 10
        assert report.total_failed == 3
        assert report.total_collected == 13  # 10 + 3

    def test_parses_summary_with_errors(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_IMPORT_ERROR, "click")

        assert report.total_passed == 0
        assert report.total_failed == 6  # 1 FAILED + 5 collection errors
        assert report.total_collected == 6  # 0 + 1 + 5 errors

    def test_parses_collected_items_line(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_WITH_COLLECTED, "architecture_model")

        assert report.total_collected == 20


class TestParseFailedAssertionError:
    """Test parsing failures with AssertionError."""

    def test_parses_failed_with_assertion_error(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_SHORT_SUMMARY, "click")

        assert len(report.failures) == 3
        f = report.failures[0]
        assert f.test_name == "test_basic_functionality"
        assert f.test_file == "tests/test_basic.py"
        assert f.error_type == "AssertionError"
        assert "I EXECUTED" in f.error_message


class TestParseFailedImportError:
    """Test parsing failures with ImportError."""

    def test_parses_failed_with_import_error(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_IMPORT_ERROR, "click")

        assert len(report.failures) == 1
        f = report.failures[0]
        assert f.test_name == "test_basic_functionality"
        assert f.error_type == "ImportError"
        assert "Command" in f.error_message


class TestParseFailedAttributeError:
    """Test parsing failures with AttributeError."""

    def test_parses_failed_with_attribute_error(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_VERBOSE_TRACEBACKS, "click")

        # Should find the second failure with AttributeError
        attr_failures = [f for f in report.failures if f.error_type == "AttributeError"]
        assert len(attr_failures) >= 1
        f = attr_failures[0]
        assert f.test_name == "test_return_values"
        assert "make_context" in f.error_message


class TestExtractExpectedActual:
    """Test extraction of expected/actual values from equality assertions."""

    def test_extracts_expected_actual_from_equality(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_EQUALITY_ASSERTION, "core")

        assert len(report.failures) == 1
        f = report.failures[0]
        assert f.error_type == "AssertionError"
        # The error message contains "assert 'actual_value' == 'expected_value'"
        # Parser should extract expected and actual from this
        assert f.expected is not None or f.actual is not None
        # At minimum the error_message should contain both values
        assert "actual_value" in f.error_message or (f.actual and "actual_value" in f.actual)


class TestMapToComponentFromTraceback:
    """Test component mapping from traceback file references."""

    def test_maps_failure_to_component_from_traceback(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_TRACEBACK_WITH_COMPONENT, "architecture_model/training")

        assert len(report.failures) >= 1
        f = report.failures[0]
        assert f.relevant_component == "pipeline"


class TestMapToComponentFromTestName:
    """Test component mapping fallback from test file name."""

    def test_maps_failure_to_component_from_test_name(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_WITH_COLLECTED, "architecture_model")

        assert len(report.failures) == 1
        f = report.failures[0]
        # test_core.py → component "core"
        assert f.relevant_component == "core"


class TestFormatForRetryPrompt:
    """Test FailureReport.format_for_retry_prompt output."""

    def test_format_for_retry_prompt(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_SHORT_SUMMARY, "click")
        output = report.format_for_retry_prompt()

        assert "## Test Failures" in output
        assert "3 failed" in output
        assert "10 passed" in output
        assert "test_basic_functionality" in output
        assert "AssertionError" in output

    def test_format_for_retry_prompt_filters_component(self):
        # Create a report with failures mapped to different components
        report = FailureReport(
            failures=[
                TestFailure(
                    test_name="test_parse",
                    test_file="tests/test_core.py",
                    error_type="AssertionError",
                    error_message="assert False",
                    relevant_component="core",
                ),
                TestFailure(
                    test_name="test_validate",
                    test_file="tests/test_validator.py",
                    error_type="ValueError",
                    error_message="invalid input",
                    relevant_component="validator",
                ),
            ],
            total_passed=5,
            total_failed=2,
            total_collected=7,
            pass_rate=5 / 7,
            by_component={
                "core": [TestFailure(
                    test_name="test_parse",
                    test_file="tests/test_core.py",
                    error_type="AssertionError",
                    error_message="assert False",
                    relevant_component="core",
                )],
                "validator": [TestFailure(
                    test_name="test_validate",
                    test_file="tests/test_validator.py",
                    error_type="ValueError",
                    error_message="invalid input",
                    relevant_component="validator",
                )],
            },
            by_error_type={"AssertionError": 1, "ValueError": 1},
        )

        output = report.format_for_retry_prompt(component="core")
        assert "test_parse" in output
        assert "test_validate" not in output


class TestHandlesEmptyOutput:
    """Test graceful handling of empty output."""

    def test_handles_empty_output(self):
        parser = FailureParser()
        report = parser.parse("", "mypackage")

        assert report.total_passed == 0
        assert report.total_failed == 0
        assert report.total_collected == 0
        assert report.failures == []
        assert report.pass_rate == 0.0


class TestPassRateCalculation:
    """Test pass rate computation."""

    def test_pass_rate_calculation(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_SHORT_SUMMARY, "click")

        # 10 passed, 3 failed = 10/13 ≈ 0.769
        assert report.pass_rate == pytest.approx(10 / 13, rel=1e-3)


class TestByErrorTypeGrouping:
    """Test grouping failures by error type."""

    def test_by_error_type_grouping(self):
        parser = FailureParser()
        report = parser.parse(SAMPLE_VERBOSE_TRACEBACKS, "click")

        # Should have both AssertionError and AttributeError
        assert "AssertionError" in report.by_error_type or "AttributeError" in report.by_error_type
        total_counted = sum(report.by_error_type.values())
        assert total_counted == report.total_failed
