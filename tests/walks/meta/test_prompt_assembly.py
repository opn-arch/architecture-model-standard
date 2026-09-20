"""Tests for _prompt_assembly.py (Part 12 helper)."""
from __future__ import annotations

import pytest

from architecture_model.walks.meta._prompt_assembly import (
    assemble_promise_prompt,
    default_template_body,
)


def _minimal_v3_model() -> dict:
    """Two-cap parent/child v3 model with a single promise on the child."""
    return {
        "meta": {"schema_version": "3.0"},
        "entities": {
            "capabilities": [
                {
                    "id": "CAP-P",
                    "name": "Parent",
                    "description": "parent cap",
                    "promises": [],
                },
                {
                    "id": "CAP-C",
                    "name": "Child",
                    "description": "child cap",
                    "promises": [
                        {
                            "id": "PR-CAP-C-goals",
                            "attribute": "goals",
                            "content": ["initial goal text"],
                            "status": "proposed",
                        },
                        {
                            "id": "PR-CAP-C-success",
                            "attribute": "success_criteria",
                            "content": [],
                            "status": "proposed",
                        },
                    ],
                },
                {
                    "id": "CAP-S",
                    "name": "Sibling",
                    "description": "sibling cap",
                    "promises": [],
                },
            ],
            "components": [
                {
                    "id": "COMP-1",
                    "name": "Comp One",
                    "description": "a component",
                },
            ],
            "behaviors": [],
            "interfaces": [],
            "actors": [],
            "constraints": [],
            "layers": [],
        },
        "relationships": [
            {"from": "CAP-P", "to": "CAP-C", "type": "contains"},
            {"from": "CAP-P", "to": "CAP-S", "type": "contains"},
            {"from": "COMP-1", "to": "CAP-C", "type": "realizes"},
            {"from": "CAP-C", "to": "COMP-1", "type": "depends-on"},
            {"from": "CAP-C", "to": "CAP-S", "type": "mounted-on"},  # excluded
        ],
    }


def test_unknown_entity_raises_key_error():
    model = _minimal_v3_model()
    with pytest.raises(KeyError):
        assemble_promise_prompt(model, "DOES-NOT-EXIST", "goals", "intent")


def test_promises_block_marks_target_attribute():
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model, "CAP-C", "goals", "intent body", template_body="{promises_block}"
    )
    lines = prompt.strip().splitlines()
    # PR-CAP-C-goals comes first (sorted), has marker "→"; PR-CAP-C-success has " "
    assert lines[0].startswith("→")
    assert "PR-CAP-C-goals" in lines[0]
    assert lines[1].startswith(" ")
    assert "PR-CAP-C-success" in lines[1]


def test_entity_without_promises_renders_none():
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model, "CAP-P", "goals", "intent", template_body="{promises_block}"
    )
    assert prompt.strip() == "_(none)_"


def test_deterministic_output_is_byte_stable():
    model = _minimal_v3_model()
    a = assemble_promise_prompt(model, "CAP-C", "goals", "the note")
    b = assemble_promise_prompt(model, "CAP-C", "goals", "the note")
    assert a == b


def test_parent_chain_root_only():
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model, "CAP-P", "goals", "n", template_body="{parent_chain}"
    )
    assert prompt.strip() == "ROOT / **`CAP-P` — Parent**"


def test_parent_chain_multi_level():
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model, "CAP-C", "goals", "n", template_body="{parent_chain}"
    )
    assert prompt.strip() == "ROOT / `CAP-P` — Parent / **`CAP-C` — Child**"


def test_siblings_section_lists_other_children_of_parent():
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model, "CAP-C", "goals", "n", template_body="{siblings_block}"
    )
    # CAP-S is the sibling under CAP-P; CAP-C itself excluded.
    assert prompt.strip() == "- `CAP-S` — Sibling"


def test_relations_section_filters_allowlist_and_sorts():
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model, "CAP-C", "goals", "n", template_body="{relations_block}"
    )
    # CAP-C outbound: depends-on → COMP-1 (allowed), mounted-on → CAP-S (excluded).
    lines = prompt.strip().splitlines()
    assert len(lines) == 1
    assert lines[0] == "- `depends-on` → `COMP-1` — Comp One"


def test_default_template_body_loads_from_package_resource():
    body = default_template_body()
    assert "{attribute}" in body
    assert "{entity_id}" in body
    assert "{note_body}" in body


def test_full_prompt_smoke():
    """End-to-end: full template renders without KeyError, with all sections."""
    model = _minimal_v3_model()
    prompt = assemble_promise_prompt(
        model,
        "CAP-C",
        "success_criteria",
        "must handle failure with backoff",
    )
    # Every placeholder from the default template should be substituted.
    assert "{" not in prompt or "{" in prompt.split("```")[1]  # JSON code block ok
    # Key content markers present.
    assert "CAP-C" in prompt
    assert "success_criteria" in prompt
    assert "must handle failure with backoff" in prompt
    assert "Child" in prompt  # entity name
    assert "→" in prompt  # marker on target promise
