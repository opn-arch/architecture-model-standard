"""
Parse project configuration files to derive technical and organizational constraints.

Scans pyproject.toml, Dockerfile, .env templates, CI config, and setup.cfg to
automatically detect constraints such as Python version requirements, framework
choices, runtime images, exposed ports, and CI/CD platform.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from architecture_model.core.types import Constraint, ConstraintType, Status


# ---------------------------------------------------------------------------
# Key frameworks to detect in dependencies
# ---------------------------------------------------------------------------

_KEY_FRAMEWORKS: set[str] = {
    "fastapi",
    "flask",
    "django",
    "starlette",
    "aiohttp",
    "tornado",
    "sqlalchemy",
    "asyncpg",
    "psycopg2",
    "pymongo",
    "redis",
    "celery",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_constraints(project_root: Path) -> list[Constraint]:
    """Scan project configuration files for derivable constraints.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of Constraint entities derived from config files.
    """
    constraints: list[Constraint] = []
    tc_counter = 0
    oc_counter = 0

    # --- pyproject.toml ---
    tc_counter, oc_counter = _parse_pyproject(
        project_root, constraints, tc_counter, oc_counter
    )

    # --- Dockerfile ---
    tc_counter, oc_counter = _parse_dockerfile(
        project_root, constraints, tc_counter, oc_counter
    )

    # --- .env.example / .env.template ---
    oc_counter = _parse_env_template(project_root, constraints, oc_counter)

    # --- CI/CD config ---
    oc_counter = _parse_ci_config(project_root, constraints, oc_counter)

    # --- setup.cfg fallback for python_requires ---
    tc_counter, oc_counter = _parse_setup_cfg(
        project_root, constraints, tc_counter, oc_counter
    )

    return constraints


# ---------------------------------------------------------------------------
# pyproject.toml parsing
# ---------------------------------------------------------------------------


def _parse_pyproject(
    project_root: Path,
    constraints: list[Constraint],
    tc_counter: int,
    oc_counter: int,
) -> tuple[int, int]:
    """Extract constraints from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.is_file():
        return tc_counter, oc_counter

    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return tc_counter, oc_counter

    # requires-python
    requires_python = data.get("project", {}).get("requires-python", "")
    if requires_python:
        tc_counter += 1
        constraints.append(
            Constraint(
                id=f"TC-{tc_counter:02d}",
                name=f"Python {requires_python}",
                status=Status.ACTIVE,
                description=f"Project requires Python {requires_python}",
                type=ConstraintType.TECHNOLOGY,
                metric="python_version",
                threshold=requires_python,
                rationale="Detected from pyproject.toml requires-python",
            )
        )

    # dependencies (key frameworks)
    deps = _collect_dependencies(data)
    for dep_name in sorted(deps):
        normalized = _normalize_dep_name(dep_name)
        if normalized in _KEY_FRAMEWORKS:
            tc_counter += 1
            constraints.append(
                Constraint(
                    id=f"TC-{tc_counter:02d}",
                    name=f"Dependency: {normalized}",
                    status=Status.ACTIVE,
                    description=f"Project depends on {normalized}",
                    tags=[normalized],
                    type=ConstraintType.TECHNOLOGY,
                    rationale="Detected from pyproject.toml dependencies",
                )
            )

    return tc_counter, oc_counter


def _collect_dependencies(data: dict) -> list[str]:
    """Collect dependency names from pyproject.toml data.

    Checks [project.dependencies] and [tool.poetry.dependencies].
    """
    deps: list[str] = []

    # PEP 621 style
    project_deps = data.get("project", {}).get("dependencies", [])
    for dep in project_deps:
        # Parse requirement specifier: "fastapi>=0.100" -> "fastapi"
        name = re.split(r"[>=<!\[;@\s]", dep, maxsplit=1)[0].strip()
        if name:
            deps.append(name)

    # Poetry style
    poetry_deps = (
        data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    )
    if isinstance(poetry_deps, dict):
        for name in poetry_deps:
            if name.lower() != "python":
                deps.append(name)

    return deps


def _normalize_dep_name(name: str) -> str:
    """Normalize a dependency name for comparison (lowercase, hyphens to underscores removed)."""
    return re.sub(r"[-_.]", "", name.lower())


# ---------------------------------------------------------------------------
# Dockerfile parsing
# ---------------------------------------------------------------------------


def _parse_dockerfile(
    project_root: Path,
    constraints: list[Constraint],
    tc_counter: int,
    oc_counter: int,
) -> tuple[int, int]:
    """Extract constraints from Dockerfile."""
    dockerfile_path = project_root / "Dockerfile"
    if not dockerfile_path.is_file():
        return tc_counter, oc_counter

    try:
        content = dockerfile_path.read_text(encoding="utf-8")
    except OSError:
        return tc_counter, oc_counter

    # FROM line (first non-comment FROM)
    from_match = re.search(
        r"^\s*FROM\s+(\S+)", content, re.MULTILINE | re.IGNORECASE
    )
    if from_match:
        base_image = from_match.group(1)
        tc_counter += 1
        constraints.append(
            Constraint(
                id=f"TC-{tc_counter:02d}",
                name=f"Base image: {base_image}",
                status=Status.ACTIVE,
                description=f"Container runtime uses base image {base_image}",
                type=ConstraintType.TECHNOLOGY,
                metric="base_image",
                threshold=base_image,
                rationale="Detected from Dockerfile FROM directive",
            )
        )

    # EXPOSE lines
    expose_matches = re.findall(
        r"^\s*EXPOSE\s+(.+)$", content, re.MULTILINE | re.IGNORECASE
    )
    ports: list[str] = []
    for match in expose_matches:
        # EXPOSE can have multiple ports: "EXPOSE 8000 8080"
        found = re.findall(r"\d+", match)
        ports.extend(found)

    if ports:
        tc_counter += 1
        port_str = ", ".join(ports)
        constraints.append(
            Constraint(
                id=f"TC-{tc_counter:02d}",
                name=f"Exposed ports: {port_str}",
                status=Status.ACTIVE,
                description=f"Container exposes network port(s): {port_str}",
                tags=["networking"],
                type=ConstraintType.TECHNOLOGY,
                metric="exposed_ports",
                threshold=port_str,
                rationale="Detected from Dockerfile EXPOSE directive",
            )
        )

    return tc_counter, oc_counter


# ---------------------------------------------------------------------------
# .env template parsing
# ---------------------------------------------------------------------------


def _parse_env_template(
    project_root: Path,
    constraints: list[Constraint],
    oc_counter: int,
) -> int:
    """Count required env vars from .env.example or .env.template."""
    env_path: Path | None = None
    for name in (".env.example", ".env.template"):
        candidate = project_root / name
        if candidate.is_file():
            env_path = candidate
            break

    if env_path is None:
        return oc_counter

    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return oc_counter

    # Count non-empty, non-comment lines that look like KEY=...
    var_count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", stripped):
                var_count += 1

    if var_count > 0:
        oc_counter += 1
        constraints.append(
            Constraint(
                id=f"OC-{oc_counter:02d}",
                name=f"Environment configuration ({var_count} vars)",
                status=Status.ACTIVE,
                description=(
                    f"Application requires {var_count} environment variable(s) "
                    f"as defined in {env_path.name}"
                ),
                tags=["configuration"],
                type=ConstraintType.OPERATIONAL,
                metric="env_var_count",
                threshold=str(var_count),
                rationale=f"Detected from {env_path.name}",
            )
        )

    return oc_counter


# ---------------------------------------------------------------------------
# CI/CD config parsing
# ---------------------------------------------------------------------------


def _parse_ci_config(
    project_root: Path,
    constraints: list[Constraint],
    oc_counter: int,
) -> int:
    """Detect CI/CD platform from workflow config files."""
    # GitHub Actions
    workflows_dir = project_root / ".github" / "workflows"
    if workflows_dir.is_dir():
        yml_files = list(workflows_dir.glob("*.yml")) + list(
            workflows_dir.glob("*.yaml")
        )
        if yml_files:
            oc_counter += 1
            constraints.append(
                Constraint(
                    id=f"OC-{oc_counter:02d}",
                    name="CI/CD: GitHub Actions",
                    status=Status.ACTIVE,
                    description="Project uses GitHub Actions for CI/CD",
                    tags=["ci-cd", "github"],
                    type=ConstraintType.OPERATIONAL,
                    rationale="Detected from .github/workflows/*.yml",
                )
            )
            return oc_counter

    # GitLab CI
    gitlab_ci = project_root / ".gitlab-ci.yml"
    if gitlab_ci.is_file():
        oc_counter += 1
        constraints.append(
            Constraint(
                id=f"OC-{oc_counter:02d}",
                name="CI/CD: GitLab CI",
                status=Status.ACTIVE,
                description="Project uses GitLab CI/CD",
                tags=["ci-cd", "gitlab"],
                type=ConstraintType.OPERATIONAL,
                rationale="Detected from .gitlab-ci.yml",
            )
        )

    return oc_counter


# ---------------------------------------------------------------------------
# setup.cfg fallback
# ---------------------------------------------------------------------------


def _parse_setup_cfg(
    project_root: Path,
    constraints: list[Constraint],
    tc_counter: int,
    oc_counter: int,
) -> tuple[int, int]:
    """Extract python_requires from setup.cfg as fallback.

    Only adds a constraint if no Python version constraint was already found
    from pyproject.toml.
    """
    # Skip if we already have a python version constraint
    if any(c.metric == "python_version" for c in constraints):
        return tc_counter, oc_counter

    setup_cfg_path = project_root / "setup.cfg"
    if not setup_cfg_path.is_file():
        return tc_counter, oc_counter

    try:
        content = setup_cfg_path.read_text(encoding="utf-8")
    except OSError:
        return tc_counter, oc_counter

    # Look for python_requires under [options]
    match = re.search(
        r"^\s*python_requires\s*=\s*(.+)$", content, re.MULTILINE
    )
    if match:
        requires = match.group(1).strip()
        tc_counter += 1
        constraints.append(
            Constraint(
                id=f"TC-{tc_counter:02d}",
                name=f"Python {requires}",
                status=Status.ACTIVE,
                description=f"Project requires Python {requires}",
                type=ConstraintType.TECHNOLOGY,
                metric="python_version",
                threshold=requires,
                rationale="Detected from setup.cfg python_requires",
            )
        )

    return tc_counter, oc_counter
