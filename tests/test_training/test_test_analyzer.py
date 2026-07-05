"""Tests for TestStructureAnalyzer and TestCoverageAnalyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.training.test_analyzer import (
    TestCoverage,
    TestCoverageAnalyzer,
    TestStructure,
    TestStructureAnalyzer,
)
from architecture_model.training.test_runner import TestRunResult


class TestExtractComponentName:
    """Component name extraction from test filenames."""

    def setup_method(self):
        self.analyzer = TestStructureAnalyzer()

    def test_simple_name(self):
        """test_client.py → 'Client'."""
        assert self.analyzer._extract_component_name("test_client.py") == "Client"

    def test_multi_word(self):
        """test_http_pool.py → 'HTTP Pool'."""
        assert self.analyzer._extract_component_name("test_http_pool.py") == "HTTP Pool"

    def test_suffix_pattern(self):
        """client_test.py → 'Client'."""
        assert self.analyzer._extract_component_name("client_test.py") == "Client"

    def test_abbreviation_api(self):
        """test_api_client.py → 'API Client'."""
        assert self.analyzer._extract_component_name("test_api_client.py") == "API Client"

    def test_abbreviation_db(self):
        """test_db_manager.py → 'DB Manager'."""
        assert self.analyzer._extract_component_name("test_db_manager.py") == "DB Manager"

    def test_abbreviation_url(self):
        """test_url_parser.py → 'URL Parser'."""
        assert self.analyzer._extract_component_name("test_url_parser.py") == "URL Parser"

    def test_conftest_skipped(self):
        """conftest.py → None."""
        assert self.analyzer._extract_component_name("conftest.py") is None

    def test_init_skipped(self):
        """__init__.py → None."""
        assert self.analyzer._extract_component_name("__init__.py") is None

    def test_bare_test(self):
        """test_.py with nothing after prefix → None."""
        assert self.analyzer._extract_component_name("test_.py") is None

    def test_complex_name(self):
        """test_connection_pool_manager.py → 'Connection Pool Manager'."""
        result = self.analyzer._extract_component_name("test_connection_pool_manager.py")
        assert result == "Connection Pool Manager"

    def test_cli_abbreviation(self):
        """test_cli_commands.py → 'CLI Commands'."""
        assert self.analyzer._extract_component_name("test_cli_commands.py") == "CLI Commands"


class TestStructureAnalysis:
    """Full static structure analysis on synthetic test files."""

    def test_structure_analysis(self, tmp_path: Path):
        """Analyze a directory with test files."""
        # Create test files
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        (tests_dir / "test_client.py").write_text(
            "import mypackage.client\n"
            "from mypackage.utils import helper\n"
            "\n"
            "def test_connect():\n"
            "    pass\n"
            "\n"
            "def test_disconnect():\n"
            "    pass\n"
            "\n"
            "def test_send_data():\n"
            "    pass\n"
        )

        (tests_dir / "test_server.py").write_text(
            "import mypackage.server\n"
            "import pytest\n"
            "\n"
            "def test_start():\n"
            "    pass\n"
            "\n"
            "def test_stop():\n"
            "    pass\n"
        )

        (tests_dir / "conftest.py").write_text(
            "import pytest\n"
            "\n"
            "@pytest.fixture\n"
            "def setup():\n"
            "    pass\n"
        )

        analyzer = TestStructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        # Check implied components
        assert "Client" in result.implied_components
        assert "Server" in result.implied_components
        # conftest should not appear as a component
        assert len(result.implied_components) == 2

        # Check test counts
        assert result.test_counts["tests/test_client.py"] == 3
        assert result.test_counts["tests/test_server.py"] == 2
        assert result.total_tests == 5

        # Check imports (pytest should be filtered out)
        client_imports = result.test_imports["tests/test_client.py"]
        assert "mypackage.client" in client_imports
        assert "mypackage.utils" in client_imports
        assert "pytest" not in client_imports

        server_imports = result.test_imports["tests/test_server.py"]
        assert "mypackage.server" in server_imports
        assert "pytest" not in server_imports

    def test_structure_analysis_empty_dir(self, tmp_path: Path):
        """Analyze directory with no test files."""
        analyzer = TestStructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert result.implied_components == []
        assert result.test_counts == {}
        assert result.test_imports == {}
        assert result.total_tests == 0

    def test_structure_analysis_with_provided_files(self, tmp_path: Path):
        """Analyze with explicitly provided test file list."""
        test_file = tmp_path / "test_utils.py"
        test_file.write_text(
            "from mylib import utils\n"
            "\n"
            "def test_parse():\n"
            "    pass\n"
        )

        analyzer = TestStructureAnalyzer()
        result = analyzer.analyze(tmp_path, test_files=["test_utils.py"])

        assert "Utils" in result.implied_components
        assert result.total_tests == 1

    def test_excludes_venv(self, tmp_path: Path):
        """Test files inside .venv are excluded."""
        venv_tests = tmp_path / ".venv" / "lib" / "tests"
        venv_tests.mkdir(parents=True)
        (venv_tests / "test_internal.py").write_text("def test_x(): pass\n")

        # Real test file
        (tmp_path / "test_real.py").write_text("def test_y(): pass\n")

        analyzer = TestStructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert result.total_tests == 1
        assert "Real" in result.implied_components


class TestCoverageAnalysis:
    """Coverage analysis with mock data."""

    def test_coverage_analysis(self):
        """Full coverage analysis with mock run result."""
        run_result = TestRunResult(
            repo_name="mypackage",
            success=True,
            tests_collected=10,
            tests_passed=9,
            tests_failed=1,
            pass_rate=0.9,
            coverage_data={
                "src/mypackage/client.py": {
                    "summary": {"covered_lines": 45, "num_statements": 50}
                },
                "src/mypackage/server.py": {
                    "summary": {"covered_lines": 80, "num_statements": 100}
                },
                "src/mypackage/utils.py": {
                    "summary": {"covered_lines": 10, "num_statements": 100}
                },
            },
        )

        structure = TestStructure(
            implied_components=["Client", "Server"],
            test_counts={
                "tests/test_client.py": 5,
                "tests/test_server.py": 4,
            },
            test_imports={
                "tests/test_client.py": ["mypackage.client", "mypackage.utils"],
                "tests/test_server.py": ["mypackage.server"],
            },
            total_tests=9,
        )

        analyzer = TestCoverageAnalyzer()
        result = analyzer.analyze(run_result, structure)

        # Module importance
        assert result.module_importance["src/mypackage/client.py"] == pytest.approx(0.9)
        assert result.module_importance["src/mypackage/server.py"] == pytest.approx(0.8)
        assert result.module_importance["src/mypackage/utils.py"] == pytest.approx(0.1)

        # Pass rate
        assert result.pass_rate == pytest.approx(0.9)

        # Line totals
        assert result.total_covered_lines == 135
        assert result.total_lines == 250

    def test_coverage_empty(self):
        """Coverage analysis with no coverage data."""
        run_result = TestRunResult(
            repo_name="empty",
            success=True,
            coverage_data={},
        )
        structure = TestStructure(
            implied_components=[],
            test_counts={},
            test_imports={},
            total_tests=0,
        )

        analyzer = TestCoverageAnalyzer()
        result = analyzer.analyze(run_result, structure)

        assert result.module_importance == {}
        assert result.relationship_evidence == []
        assert result.component_weights == {}
        assert result.total_covered_lines == 0
        assert result.total_lines == 0


class TestRelationshipDerivation:
    """Cross-module relationship evidence from coverage + imports."""

    def test_relationship_derivation(self):
        """Modules imported by same test with high coverage create relationships."""
        run_result = TestRunResult(
            repo_name="mypackage",
            success=True,
            coverage_data={
                "src/mypackage/client.py": {
                    "summary": {"covered_lines": 45, "num_statements": 50}  # 90%
                },
                "src/mypackage/transport.py": {
                    "summary": {"covered_lines": 40, "num_statements": 50}  # 80%
                },
                "src/mypackage/logging.py": {
                    "summary": {"covered_lines": 5, "num_statements": 50}  # 10% — below threshold
                },
            },
        )

        structure = TestStructure(
            implied_components=["Client"],
            test_counts={"tests/test_client.py": 5},
            test_imports={
                # This test imports client, transport, and logging
                "tests/test_client.py": [
                    "mypackage.client",
                    "mypackage.transport",
                    "mypackage.logging",
                ],
            },
            total_tests=5,
        )

        analyzer = TestCoverageAnalyzer()
        result = analyzer.analyze(run_result, structure)

        # client (90%) and transport (80%) should have a relationship
        # logging (10%) is below the 30% threshold, so no relationships with it
        assert len(result.relationship_evidence) > 0

        # Find the client-transport relationship
        found = False
        for mod_a, mod_b, strength in result.relationship_evidence:
            if "client" in mod_a and "transport" in mod_b:
                found = True
                # Strength should be min(0.9, 0.8) = 0.8
                assert strength == pytest.approx(0.8)
            elif "transport" in mod_a and "client" in mod_b:
                found = True
                assert strength == pytest.approx(0.8)

        assert found, f"Expected client↔transport relationship, got: {result.relationship_evidence}"

    def test_no_relationship_below_threshold(self):
        """No relationships when coverage is below 30%."""
        run_result = TestRunResult(
            repo_name="mypackage",
            success=True,
            coverage_data={
                "src/a.py": {"summary": {"covered_lines": 10, "num_statements": 100}},  # 10%
                "src/b.py": {"summary": {"covered_lines": 15, "num_statements": 100}},  # 15%
            },
        )

        structure = TestStructure(
            implied_components=["A"],
            test_counts={"tests/test_a.py": 3},
            test_imports={"tests/test_a.py": ["a", "b"]},
            total_tests=3,
        )

        analyzer = TestCoverageAnalyzer()
        result = analyzer.analyze(run_result, structure)

        # Both modules are below 30% threshold — no relationship
        assert len(result.relationship_evidence) == 0

    def test_multiple_tests_multiple_relationships(self):
        """Multiple test files can create multiple relationships."""
        run_result = TestRunResult(
            repo_name="pkg",
            success=True,
            coverage_data={
                "src/pkg/auth.py": {"summary": {"covered_lines": 40, "num_statements": 50}},
                "src/pkg/session.py": {"summary": {"covered_lines": 35, "num_statements": 50}},
                "src/pkg/cache.py": {"summary": {"covered_lines": 45, "num_statements": 50}},
            },
        )

        structure = TestStructure(
            implied_components=["Auth", "Cache"],
            test_counts={
                "tests/test_auth.py": 3,
                "tests/test_cache.py": 2,
            },
            test_imports={
                "tests/test_auth.py": ["pkg.auth", "pkg.session"],
                "tests/test_cache.py": ["pkg.cache", "pkg.session"],
            },
            total_tests=5,
        )

        analyzer = TestCoverageAnalyzer()
        result = analyzer.analyze(run_result, structure)

        # Should have auth↔session and cache↔session relationships
        modules_in_relations = set()
        for mod_a, mod_b, _strength in result.relationship_evidence:
            modules_in_relations.add(mod_a)
            modules_in_relations.add(mod_b)

        assert any("auth" in m for m in modules_in_relations)
        assert any("session" in m for m in modules_in_relations)
        assert any("cache" in m for m in modules_in_relations)
