"""Plugin-hook endpoint extraction — Phase 4-A Task 10.

Parses ``pyproject.toml`` ``[project.entry-points.*]`` tables and
setuptools ``entry_points={...}`` arguments in ``setup.py``. Emits
:class:`Endpoint` records with ``kind="plugin_hook"``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.pipeline.endpoint_extract import extract_plugin_hook_endpoints


@pytest.fixture
def pyproject_repo(tmp_path: Path) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        dedent(
            """
            [project]
            name = "my-tool"

            [project.entry-points."opencode_arch.projectors"]
            mission = "my_tool.projectors:mission"
            risk = "my_tool.projectors:risk"

            [project.entry-points."architecture_model.plugins"]
            enricher = "my_tool.enrich:Enricher"

            [project.scripts]
            mytool = "my_tool.cli:main"
            """
        ).lstrip()
    )
    return tmp_path


@pytest.fixture
def setup_py_repo(tmp_path: Path) -> Path:
    setup = tmp_path / "setup.py"
    setup.write_text(
        dedent(
            """
            from setuptools import setup

            setup(
                name="legacy",
                entry_points={
                    "console_scripts": [
                        "legacy-cli = legacy.cli:main",
                    ],
                    "opencode_arch.projectors": [
                        "spec = legacy.proj:spec",
                    ],
                },
            )
            """
        ).lstrip()
    )
    return tmp_path


def test_extract_plugin_hooks_from_pyproject(pyproject_repo):
    endpoints = extract_plugin_hook_endpoints(pyproject_repo)
    names = {e.name for e in endpoints}
    assert "mission" in names
    assert "risk" in names
    assert "enricher" in names
    # console_scripts / [project.scripts] should ALSO surface as plugin hooks
    # since they are dispatchable entry points.
    assert "mytool" in names


def test_extract_plugin_hooks_groups_captured(pyproject_repo):
    endpoints = extract_plugin_hook_endpoints(pyproject_repo)
    by_name = {e.name: e for e in endpoints}
    assert by_name["mission"].metadata["entry_point_group"] == (
        "opencode_arch.projectors"
    )
    assert by_name["enricher"].metadata["entry_point_group"] == (
        "architecture_model.plugins"
    )


def test_extract_plugin_hooks_target_captured(pyproject_repo):
    endpoints = extract_plugin_hook_endpoints(pyproject_repo)
    mission = next(e for e in endpoints if e.name == "mission")
    assert mission.metadata["target"] == "my_tool.projectors:mission"


def test_extract_plugin_hooks_from_setup_py(setup_py_repo):
    endpoints = extract_plugin_hook_endpoints(setup_py_repo)
    names = {e.name for e in endpoints}
    assert "legacy-cli" in names
    assert "spec" in names
    legacy = next(e for e in endpoints if e.name == "legacy-cli")
    assert legacy.metadata["entry_point_group"] == "console_scripts"
    assert legacy.metadata["target"] == "legacy.cli:main"


def test_extract_plugin_hooks_deterministic(pyproject_repo):
    a = extract_plugin_hook_endpoints(pyproject_repo)
    b = extract_plugin_hook_endpoints(pyproject_repo)
    assert [(e.name, e.metadata["entry_point_group"]) for e in a] == [
        (e.name, e.metadata["entry_point_group"]) for e in b
    ]


def test_extract_plugin_hooks_all_kind_plugin_hook(pyproject_repo):
    endpoints = extract_plugin_hook_endpoints(pyproject_repo)
    assert endpoints
    assert all(e.kind == "plugin_hook" for e in endpoints)


def test_extract_plugin_hooks_empty_repo_returns_empty(tmp_path):
    assert extract_plugin_hook_endpoints(tmp_path) == []
