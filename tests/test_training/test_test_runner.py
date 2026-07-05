"""Tests for TestRunner: venv creation, pytest execution, and caching."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from architecture_model.training.test_runner import TestRunResult, TestRunner


class TestRunResultDataclass:
    """TestRunResult construction and serialization."""

    def test_run_result_dataclass(self):
        """Basic construction with defaults."""
        result = TestRunResult(repo_name="my-repo", success=True)
        assert result.repo_name == "my-repo"
        assert result.success is True
        assert result.tests_collected == 0
        assert result.tests_passed == 0
        assert result.tests_failed == 0
        assert result.tests_skipped == 0
        assert result.tests_error == 0
        assert result.pass_rate == 0.0
        assert result.coverage_data == {}
        assert result.overall_coverage == 0.0
        assert result.test_files == []
        assert result.install_error is None
        assert result.run_error is None
        assert result.install_time_s == 0.0
        assert result.run_time_s == 0.0

    def test_run_result_with_values(self):
        """Construction with explicit values."""
        result = TestRunResult(
            repo_name="requests",
            success=True,
            tests_collected=100,
            tests_passed=95,
            tests_failed=3,
            tests_skipped=2,
            tests_error=0,
            pass_rate=0.9694,
            coverage_data={"src/client.py": {"summary": {"covered_lines": 45}}},
            overall_coverage=85.5,
            test_files=["tests/test_client.py"],
            install_time_s=5.2,
            run_time_s=12.3,
        )
        assert result.tests_collected == 100
        assert result.pass_rate == pytest.approx(0.9694)
        assert result.overall_coverage == 85.5
        assert "src/client.py" in result.coverage_data

    def test_run_result_failure(self):
        """Construction for failed run."""
        result = TestRunResult(
            repo_name="broken-repo",
            success=False,
            install_error="ModuleNotFoundError: No module named 'foo'",
        )
        assert result.success is False
        assert "ModuleNotFoundError" in result.install_error


class TestCacheRoundTrip:
    """Cache save/load behavior."""

    def test_cache_round_trip(self, tmp_path: Path):
        """Save and load from JSON cache."""
        runner = TestRunner()

        original = TestRunResult(
            repo_name="test-repo",
            success=True,
            tests_collected=50,
            tests_passed=48,
            tests_failed=2,
            tests_skipped=0,
            tests_error=0,
            pass_rate=0.96,
            coverage_data={"src/main.py": {"summary": {"covered_lines": 30, "num_statements": 40}}},
            overall_coverage=75.0,
            test_files=["tests/test_main.py"],
            install_time_s=3.0,
            run_time_s=8.5,
        )

        # Save
        runner._save_cache(tmp_path, original)

        # Verify file exists
        cache_path = tmp_path / TestRunner.CACHE_FILE
        assert cache_path.exists()

        # Verify JSON is valid
        data = json.loads(cache_path.read_text())
        assert data["repo_name"] == "test-repo"
        assert data["success"] is True
        assert data["tests_passed"] == 48

        # Load
        loaded = runner._load_cache(tmp_path)
        assert loaded is not None
        assert loaded.repo_name == original.repo_name
        assert loaded.success == original.success
        assert loaded.tests_collected == original.tests_collected
        assert loaded.tests_passed == original.tests_passed
        assert loaded.pass_rate == pytest.approx(original.pass_rate)
        assert loaded.coverage_data == original.coverage_data

    def test_cache_missing_returns_none(self, tmp_path: Path):
        """No cache file returns None."""
        runner = TestRunner()
        assert runner._load_cache(tmp_path) is None

    def test_cache_corrupt_returns_none(self, tmp_path: Path):
        """Corrupted cache file returns None."""
        runner = TestRunner()
        cache_path = tmp_path / TestRunner.CACHE_FILE
        cache_path.write_text("not valid json {{{")
        assert runner._load_cache(tmp_path) is None


class TestRunnerHandlesMissingRepo:
    """Graceful failure for non-existent repos."""

    def test_runner_handles_missing_repo(self, tmp_path: Path):
        """Runner returns failure for non-existent repo path."""
        runner = TestRunner()
        missing_path = tmp_path / "does-not-exist"

        # The runner should not crash — it should return a result with success=False
        # because venv creation will fail on a non-existent path
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("No such file or directory")
            result = runner.run(missing_path, "fake_package")

        assert result.success is False
        assert result.repo_name == "does-not-exist"

    def test_runner_uses_cache(self, tmp_path: Path):
        """Runner returns cached result without executing."""
        runner = TestRunner()

        # Pre-populate cache
        cached = TestRunResult(repo_name=tmp_path.name, success=True, tests_passed=10)
        runner._save_cache(tmp_path, cached)

        # Should return cache without running anything
        result = runner.run(tmp_path, "some_package")
        assert result.success is True
        assert result.tests_passed == 10


class TestParsePytestOutput:
    """Parsing pytest -q output summary lines."""

    def test_parse_all_passed(self):
        """Parse output where all tests pass."""
        runner = TestRunner()
        output = "...\n5 passed in 1.23s"
        data = runner._parse_pytest_output(output)
        assert data["passed"] == 5
        assert data["failed"] == 0
        assert data["collected"] == 5

    def test_parse_mixed_results(self):
        """Parse output with passes, failures, and skips."""
        runner = TestRunner()
        output = "...xFFF\n10 passed, 3 failed, 2 skipped in 4.56s"
        data = runner._parse_pytest_output(output)
        assert data["passed"] == 10
        assert data["failed"] == 3
        assert data["skipped"] == 2
        assert data["collected"] == 15

    def test_parse_no_tests(self):
        """Parse output when no tests found."""
        runner = TestRunner()
        output = "no tests ran in 0.01s"
        data = runner._parse_pytest_output(output)
        assert data["collected"] == 0

    def test_parse_with_decorations(self):
        """Parse output with pytest === decorations."""
        runner = TestRunner()
        output = "===== 3 passed, 1 failed in 0.5s ====="
        data = runner._parse_pytest_output(output)
        assert data["passed"] == 3
        assert data["failed"] == 1


class TestParseCoverage:
    """Parsing coverage.json output."""

    def test_parse_coverage_file(self, tmp_path: Path):
        """Parse a valid coverage.json."""
        runner = TestRunner()

        cov_data = {
            "meta": {"version": "7.0"},
            "files": {
                "src/client.py": {
                    "summary": {"covered_lines": 45, "num_statements": 50}
                },
                "src/server.py": {
                    "summary": {"covered_lines": 30, "num_statements": 100}
                },
            },
        }
        (tmp_path / "coverage.json").write_text(json.dumps(cov_data))

        result = runner._parse_coverage(tmp_path)
        assert "src/client.py" in result["files"]
        assert result["overall"] == pytest.approx(50.0)  # 75/150 = 50%

    def test_parse_coverage_missing(self, tmp_path: Path):
        """Missing coverage.json returns empty."""
        runner = TestRunner()
        result = runner._parse_coverage(tmp_path)
        assert result["files"] == {}
        assert result["overall"] == 0.0
