"""Tests for architecture_model.extract.constraint_detector."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from architecture_model.extract.constraint_detector import detect_constraints
from architecture_model.core.types import Constraint, ConstraintType, Status


# ---------------------------------------------------------------------------
# pyproject.toml detection
# ---------------------------------------------------------------------------


class TestPyprojectParsing:
    """Test constraint detection from pyproject.toml."""

    def test_detects_python_version(self, tmp_path: Path) -> None:
        """Detects requires-python from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.11"\n',
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        python_constraints = [c for c in constraints if c.metric == "python_version"]
        assert len(python_constraints) == 1
        assert python_constraints[0].threshold == ">=3.11"
        assert python_constraints[0].id == "TC-01"
        assert python_constraints[0].status == Status.ACTIVE
        assert python_constraints[0].type == ConstraintType.TECHNOLOGY
        assert "pyproject.toml" in python_constraints[0].rationale

    def test_detects_key_framework_dependencies(self, tmp_path: Path) -> None:
        """Detects key framework dependencies from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\n'
            'requires-python = ">=3.11"\n'
            'dependencies = ["fastapi>=0.100", "sqlalchemy[asyncio]>=2.0", "pydantic>=2.0"]\n',
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        dep_constraints = [c for c in constraints if "Dependency:" in c.name]
        dep_names = {c.name for c in dep_constraints}
        assert "Dependency: fastapi" in dep_names
        assert "Dependency: sqlalchemy" in dep_names
        # pydantic is NOT in _KEY_FRAMEWORKS, so it should not appear
        assert "Dependency: pydantic" not in dep_names

    def test_detects_poetry_dependencies(self, tmp_path: Path) -> None:
        """Detects dependencies from [tool.poetry.dependencies]."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry.dependencies]\n'
            'python = "^3.11"\n'
            'django = "^4.2"\n'
            'redis = "^5.0"\n'
            'requests = "^2.31"\n',
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        dep_constraints = [c for c in constraints if "Dependency:" in c.name]
        dep_names = {c.name for c in dep_constraints}
        assert "Dependency: django" in dep_names
        assert "Dependency: redis" in dep_names
        # requests is not a key framework
        assert "Dependency: requests" not in dep_names

    def test_handles_malformed_pyproject(self, tmp_path: Path) -> None:
        """Gracefully handles a malformed pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            "this is not valid toml {{{}}}",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        assert constraints == []


# ---------------------------------------------------------------------------
# Dockerfile detection
# ---------------------------------------------------------------------------


class TestDockerfileParsing:
    """Test constraint detection from Dockerfile."""

    def test_detects_base_image(self, tmp_path: Path) -> None:
        """Detects base image from FROM directive."""
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11-slim\nRUN pip install app\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        image_constraints = [c for c in constraints if c.metric == "base_image"]
        assert len(image_constraints) == 1
        assert image_constraints[0].threshold == "python:3.11-slim"
        assert "Dockerfile" in image_constraints[0].rationale

    def test_detects_exposed_ports(self, tmp_path: Path) -> None:
        """Detects EXPOSE directives from Dockerfile."""
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11-slim\nEXPOSE 8000\nEXPOSE 9090\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        port_constraints = [c for c in constraints if c.metric == "exposed_ports"]
        assert len(port_constraints) == 1
        assert "8000" in port_constraints[0].threshold
        assert "9090" in port_constraints[0].threshold

    def test_detects_multi_port_expose(self, tmp_path: Path) -> None:
        """Detects multiple ports on a single EXPOSE line."""
        (tmp_path / "Dockerfile").write_text(
            "FROM node:18\nEXPOSE 3000 3001\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        port_constraints = [c for c in constraints if c.metric == "exposed_ports"]
        assert len(port_constraints) == 1
        assert "3000" in port_constraints[0].threshold
        assert "3001" in port_constraints[0].threshold

    def test_dockerfile_with_no_expose(self, tmp_path: Path) -> None:
        """Dockerfile without EXPOSE only yields base image constraint."""
        (tmp_path / "Dockerfile").write_text(
            "FROM alpine:3.18\nRUN apk add python3\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        port_constraints = [c for c in constraints if c.metric == "exposed_ports"]
        assert len(port_constraints) == 0
        image_constraints = [c for c in constraints if c.metric == "base_image"]
        assert len(image_constraints) == 1


# ---------------------------------------------------------------------------
# .env template detection
# ---------------------------------------------------------------------------


class TestEnvTemplateParsing:
    """Test constraint detection from .env.example / .env.template."""

    def test_counts_env_vars(self, tmp_path: Path) -> None:
        """Counts environment variables from .env.example."""
        (tmp_path / ".env.example").write_text(
            "# Database config\n"
            "DATABASE_URL=postgresql://localhost/db\n"
            "REDIS_URL=redis://localhost\n"
            "SECRET_KEY=changeme\n"
            "# Comment line\n"
            "\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        env_constraints = [c for c in constraints if c.metric == "env_var_count"]
        assert len(env_constraints) == 1
        assert env_constraints[0].threshold == "3"
        assert env_constraints[0].type == ConstraintType.OPERATIONAL
        assert env_constraints[0].id.startswith("OC-")

    def test_prefers_env_example_over_template(self, tmp_path: Path) -> None:
        """Uses .env.example when both files exist."""
        (tmp_path / ".env.example").write_text("A=1\nB=2\n", encoding="utf-8")
        (tmp_path / ".env.template").write_text("X=1\nY=2\nZ=3\n", encoding="utf-8")
        constraints = detect_constraints(tmp_path)
        env_constraints = [c for c in constraints if c.metric == "env_var_count"]
        assert len(env_constraints) == 1
        # Should use .env.example (2 vars, not 3)
        assert env_constraints[0].threshold == "2"


# ---------------------------------------------------------------------------
# CI/CD detection
# ---------------------------------------------------------------------------


class TestCiCdDetection:
    """Test CI/CD platform detection."""

    def test_detects_github_actions(self, tmp_path: Path) -> None:
        """Detects GitHub Actions from .github/workflows/*.yml."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI\non: push\n", encoding="utf-8")
        constraints = detect_constraints(tmp_path)
        ci_constraints = [c for c in constraints if "GitHub Actions" in c.name]
        assert len(ci_constraints) == 1
        assert ci_constraints[0].type == ConstraintType.OPERATIONAL
        assert ci_constraints[0].id.startswith("OC-")

    def test_detects_gitlab_ci(self, tmp_path: Path) -> None:
        """Detects GitLab CI from .gitlab-ci.yml."""
        (tmp_path / ".gitlab-ci.yml").write_text(
            "stages:\n  - test\n", encoding="utf-8"
        )
        constraints = detect_constraints(tmp_path)
        ci_constraints = [c for c in constraints if "GitLab CI" in c.name]
        assert len(ci_constraints) == 1

    def test_github_takes_precedence_over_gitlab(self, tmp_path: Path) -> None:
        """If both GitHub and GitLab configs exist, GitHub is reported."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")
        (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - test\n", encoding="utf-8")
        constraints = detect_constraints(tmp_path)
        ci_constraints = [c for c in constraints if "CI/CD" in c.name]
        # Only GitHub Actions should be reported (early return)
        assert len(ci_constraints) == 1
        assert "GitHub" in ci_constraints[0].name


# ---------------------------------------------------------------------------
# setup.cfg fallback
# ---------------------------------------------------------------------------


class TestSetupCfgFallback:
    """Test setup.cfg python_requires as fallback."""

    def test_uses_setup_cfg_when_no_pyproject(self, tmp_path: Path) -> None:
        """Falls back to setup.cfg python_requires when no pyproject.toml."""
        (tmp_path / "setup.cfg").write_text(
            "[options]\npython_requires = >=3.9\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        python_constraints = [c for c in constraints if c.metric == "python_version"]
        assert len(python_constraints) == 1
        assert python_constraints[0].threshold == ">=3.9"
        assert "setup.cfg" in python_constraints[0].rationale

    def test_pyproject_takes_precedence_over_setup_cfg(self, tmp_path: Path) -> None:
        """pyproject.toml requires-python takes precedence over setup.cfg."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.11"\n',
            encoding="utf-8",
        )
        (tmp_path / "setup.cfg").write_text(
            "[options]\npython_requires = >=3.9\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        python_constraints = [c for c in constraints if c.metric == "python_version"]
        # Only one Python version constraint (from pyproject.toml)
        assert len(python_constraints) == 1
        assert python_constraints[0].threshold == ">=3.11"


# ---------------------------------------------------------------------------
# Empty / missing project
# ---------------------------------------------------------------------------


class TestEmptyProject:
    """Test behavior with empty or missing configuration."""

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """An empty directory returns no constraints."""
        constraints = detect_constraints(tmp_path)
        assert constraints == []

    def test_all_constraints_are_constraint_instances(self, tmp_path: Path) -> None:
        """All returned items are Constraint dataclass instances."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\n'
            'requires-python = ">=3.11"\n'
            'dependencies = ["fastapi>=0.100"]\n',
            encoding="utf-8",
        )
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11-slim\nEXPOSE 8000\n",
            encoding="utf-8",
        )
        constraints = detect_constraints(tmp_path)
        assert len(constraints) > 0
        for c in constraints:
            assert isinstance(c, Constraint)
            assert c.status == Status.ACTIVE
            assert c.rationale  # All should have rationale

    def test_id_format_is_correct(self, tmp_path: Path) -> None:
        """IDs follow TC-nn / OC-nn format."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.11"\n'
            'dependencies = ["django>=4.0"]\n',
            encoding="utf-8",
        )
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")

        constraints = detect_constraints(tmp_path)
        for c in constraints:
            assert re.match(r"^(TC|OC)-\d{2}$", c.id), f"Bad ID format: {c.id}"
