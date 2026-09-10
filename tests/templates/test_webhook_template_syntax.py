"""Task 24 — child-publish webhook (GitHub Actions) template.

Validates the GH Actions workflow YAML template that triggers parent-repo
federated invalidation when a child repo pushes to main.

Checks:
* the template file exists,
* it parses as valid YAML,
* it declares on.push (main branch),
* it invokes GitHub's repository_dispatch API to notify the parent,
* documented placeholders are present.
"""
from __future__ import annotations

from pathlib import Path

import yaml

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "templates"
    / "child-publish-webhook.yml"
)


def test_template_exists():
    assert TEMPLATE.exists(), TEMPLATE


def test_template_parses_as_yaml():
    doc = yaml.safe_load(TEMPLATE.read_text())
    assert isinstance(doc, dict), doc


def test_template_declares_push_main_trigger():
    doc = yaml.safe_load(TEMPLATE.read_text())
    # PyYAML interprets bare ``on:`` as the boolean True. Accept both.
    on = doc.get("on") if "on" in doc else doc.get(True)
    assert on is not None, doc
    push = on.get("push")
    assert push is not None, on
    branches = push.get("branches", [])
    assert "main" in branches


def test_template_uses_repository_dispatch():
    body = TEMPLATE.read_text()
    assert "repository_dispatch" in body
    assert "event_type" in body


def test_template_has_job_step_that_calls_gh_api():
    doc = yaml.safe_load(TEMPLATE.read_text())
    jobs = doc.get("jobs", {})
    assert jobs, doc
    # At least one step must reference the GH API dispatches endpoint.
    body = TEMPLATE.read_text()
    assert "/dispatches" in body


def test_template_documents_required_placeholders():
    body = TEMPLATE.read_text()
    # Placeholders callers MUST replace before use.
    assert "PARENT_OWNER" in body
    assert "PARENT_REPO" in body
    assert "CHILD_ARCH_ID" in body
    # Token secret name.
    assert "PARENT_DISPATCH_TOKEN" in body


def test_template_passes_child_revision_to_parent():
    body = TEMPLATE.read_text()
    # New generation SHA / revision must reach the parent as payload.
    assert "client_payload" in body
    assert "revision" in body or "sha" in body
