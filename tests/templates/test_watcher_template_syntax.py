"""Task 23 — child-publish filesystem watcher template.

The template is a POSIX shell script that watches a child architecture
repo's ``.architecture/lifecycle/CURRENT`` file and invokes the parent
repo's federated-invalidation CLI. Validate:

* the template file exists and is executable-shaped (shebang present),
* required placeholders are documented,
* the script is syntactically valid POSIX shell (``bash -n``).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "templates"
    / "child-publish-watcher.sh"
)


def test_template_exists():
    assert TEMPLATE.exists(), TEMPLATE


def test_template_has_shebang():
    first = TEMPLATE.read_text().splitlines()[0]
    assert first.startswith("#!"), first
    assert "sh" in first


def test_template_documents_required_placeholders():
    body = TEMPLATE.read_text()
    # Placeholders callers MUST replace before use.
    assert "CHILD_REPO" in body
    assert "PARENT_REPO" in body
    assert "CHILD_ARCH_ID" in body


def test_template_invokes_opencode_arch_invalidate():
    body = TEMPLATE.read_text()
    assert "opencode-arch" in body
    assert "invalidate" in body
    assert "--federated-child" in body


def test_template_watches_current_pointer():
    body = TEMPLATE.read_text()
    assert ".architecture/lifecycle/CURRENT" in body


def test_template_supports_fswatch_or_inotifywait():
    body = TEMPLATE.read_text()
    assert "fswatch" in body or "inotifywait" in body


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_template_is_valid_shell_syntax():
    # bash -n parses without executing.
    result = subprocess.run(
        ["bash", "-n", str(TEMPLATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
