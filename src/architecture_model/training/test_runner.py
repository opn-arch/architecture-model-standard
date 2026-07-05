"""
TestRunner: Creates per-repo venvs, installs, and runs pytest with coverage.

Best-effort: gracefully handles install failures, test timeouts, missing deps.
Caches results to avoid re-running on subsequent pipeline iterations.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TestRunResult:
    """Results from running a repo's test suite."""

    repo_name: str
    success: bool  # Did tests run at all?

    # Test counts
    tests_collected: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    tests_error: int = 0
    pass_rate: float = 0.0  # passed / (collected - skipped)

    # Coverage data (from coverage.json)
    coverage_data: dict[str, Any] = field(default_factory=dict)  # raw coverage.json["files"]
    overall_coverage: float = 0.0  # aggregate line coverage %

    # Test file info
    test_files: list[str] = field(default_factory=list)  # discovered test file paths

    # Errors (for debugging)
    install_error: str | None = None
    run_error: str | None = None

    # Timing
    install_time_s: float = 0.0
    run_time_s: float = 0.0


class TestRunner:
    """Runs a repo's test suite in an isolated venv with coverage."""

    CACHE_FILE = ".test_cache.json"

    def __init__(self, venv_base: Path | None = None, timeout: int = 120):
        self._venv_base = venv_base  # If None, uses repo_path/.venv
        self._timeout = timeout

    def run(self, repo_path: Path, package_name: str) -> TestRunResult:
        """Run tests for a repo. Uses cache if available."""
        repo_name = repo_path.name

        # 1. Check cache
        cached = self._load_cache(repo_path)
        if cached is not None:
            return cached

        # Determine venv path
        if self._venv_base is not None:
            venv_path = self._venv_base / repo_name
        else:
            venv_path = repo_path / ".venv"

        # 2. Create venv (reuse if exists)
        if not venv_path.exists():
            if not self._create_venv(venv_path):
                result = TestRunResult(
                    repo_name=repo_name,
                    success=False,
                    install_error="Failed to create virtual environment",
                )
                self._save_cache(repo_path, result)
                return result

        # 3. Install package + test deps
        t0 = time.time()
        install_ok, install_err = self._install(venv_path, repo_path)
        install_time = time.time() - t0

        if not install_ok:
            result = TestRunResult(
                repo_name=repo_name,
                success=False,
                install_error=install_err,
                install_time_s=install_time,
            )
            self._save_cache(repo_path, result)
            return result

        # 4. Run pytest with coverage
        t0 = time.time()
        pytest_data, run_err = self._run_pytest(venv_path, repo_path, package_name)
        run_time = time.time() - t0

        if run_err and not pytest_data:
            result = TestRunResult(
                repo_name=repo_name,
                success=False,
                run_error=run_err,
                install_time_s=install_time,
                run_time_s=run_time,
            )
            self._save_cache(repo_path, result)
            return result

        # 5. Parse coverage
        coverage_info = self._parse_coverage(repo_path)

        # 6. Discover test files
        test_files = [
            str(p.relative_to(repo_path))
            for p in repo_path.rglob("test_*.py")
            if ".venv" not in str(p) and "__pycache__" not in str(p)
        ]

        # Compute pass rate
        collected = pytest_data.get("collected", 0)
        passed = pytest_data.get("passed", 0)
        skipped = pytest_data.get("skipped", 0)
        denominator = collected - skipped
        pass_rate = (passed / denominator) if denominator > 0 else 0.0

        # 7. Build result
        result = TestRunResult(
            repo_name=repo_name,
            success=True,
            tests_collected=collected,
            tests_passed=passed,
            tests_failed=pytest_data.get("failed", 0),
            tests_skipped=skipped,
            tests_error=pytest_data.get("error", 0),
            pass_rate=pass_rate,
            coverage_data=coverage_info.get("files", {}),
            overall_coverage=coverage_info.get("overall", 0.0),
            test_files=test_files,
            install_time_s=install_time,
            run_time_s=run_time,
        )

        self._save_cache(repo_path, result)
        return result

    def _create_venv(self, venv_path: Path) -> bool:
        """Create a virtual environment at the given path."""
        try:
            subprocess.run(
                ["python", "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return False

    def _install(self, venv_path: Path, repo_path: Path) -> tuple[bool, str]:
        """Install the package and test dependencies into the venv."""
        pip_path = venv_path / "bin" / "pip"

        try:
            result = subprocess.run(
                [
                    str(pip_path),
                    "install",
                    "-e",
                    ".",
                    "pytest",
                    "pytest-cov",
                    "pytest-timeout",
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=str(repo_path),
            )
            if result.returncode != 0:
                return False, result.stderr or result.stdout
            return True, ""
        except subprocess.TimeoutExpired:
            return False, "pip install timed out"
        except OSError as e:
            return False, str(e)

    def _run_pytest(
        self, venv_path: Path, repo_path: Path, package_name: str
    ) -> tuple[dict, str]:
        """Run pytest with coverage and return parsed results + any error."""
        pytest_path = venv_path / "bin" / "pytest"

        try:
            result = subprocess.run(
                [
                    str(pytest_path),
                    f"--cov={package_name}",
                    "--cov-report=json",
                    "--cov-report=",
                    "-q",
                    "--tb=no",
                    "--timeout=60",
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=str(repo_path),
            )
            # pytest exit codes: 0=pass, 1=some failed, 2=interrupted, 3=internal error,
            # 4=usage error, 5=no tests collected
            output = result.stdout + "\n" + result.stderr
            if result.returncode in (0, 1, 5):
                parsed = self._parse_pytest_output(result.stdout)
                return parsed, ""
            else:
                return {}, output
        except subprocess.TimeoutExpired:
            return {}, "pytest timed out"
        except OSError as e:
            return {}, str(e)

    def _parse_pytest_output(self, output: str) -> dict:
        """Parse pytest -q output for test counts.

        Typical pytest -q output ends with a summary line like:
            '5 passed, 2 failed, 1 skipped in 1.23s'
            'no tests ran in 0.01s'
            '10 passed in 2.45s'
        """
        data: dict[str, int] = {
            "collected": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0,
        }

        # Look for the summary line (last non-empty line with timing info)
        lines = output.strip().splitlines()
        summary_line = ""
        for line in reversed(lines):
            line = line.strip()
            if " in " in line and ("passed" in line or "failed" in line or "error" in line or "no tests ran" in line):
                summary_line = line
                break

        if not summary_line:
            return data

        # Remove leading '=' characters (pytest decorates with ====)
        summary_line = summary_line.lstrip("=").rstrip("=").strip()

        # Parse counts: "5 passed", "2 failed", etc.
        import re

        for match in re.finditer(r"(\d+)\s+(passed|failed|skipped|error|errors|warnings?|deselected)", summary_line):
            count = int(match.group(1))
            kind = match.group(2)
            if kind == "passed":
                data["passed"] = count
            elif kind == "failed":
                data["failed"] = count
            elif kind == "skipped":
                data["skipped"] = count
            elif kind in ("error", "errors"):
                data["error"] = count

        data["collected"] = data["passed"] + data["failed"] + data["skipped"] + data["error"]
        return data

    def _parse_coverage(self, repo_path: Path) -> dict:
        """Parse coverage.json written by pytest-cov."""
        cov_path = repo_path / "coverage.json"
        if not cov_path.exists():
            return {"files": {}, "overall": 0.0}

        try:
            with open(cov_path) as f:
                cov_data = json.load(f)

            files = cov_data.get("files", {})

            # Compute overall coverage
            total_covered = 0
            total_statements = 0
            for file_info in files.values():
                summary = file_info.get("summary", {})
                total_covered += summary.get("covered_lines", 0)
                total_statements += summary.get("num_statements", 0)

            overall = (total_covered / total_statements * 100) if total_statements > 0 else 0.0

            return {"files": files, "overall": overall}
        except (json.JSONDecodeError, OSError):
            return {"files": {}, "overall": 0.0}

    def _load_cache(self, repo_path: Path) -> TestRunResult | None:
        """Load cached test results if available."""
        cache_path = repo_path / self.CACHE_FILE
        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)
            return TestRunResult(**data)
        except (json.JSONDecodeError, OSError, TypeError):
            return None

    def _save_cache(self, repo_path: Path, result: TestRunResult) -> None:
        """Save test results to cache."""
        cache_path = repo_path / self.CACHE_FILE
        try:
            with open(cache_path, "w") as f:
                json.dump(asdict(result), f, indent=2)
        except OSError:
            pass  # Best-effort caching
