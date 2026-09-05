"""Tests for apply_model_patch executor (N52)."""
from __future__ import annotations

import pytest

from architecture_model.ai.patch import apply_model_patch
from architecture_model.ai.proposals import ModelPatch, Provenance
from architecture_model.core.errors import ParseError
from architecture_model.core.parser import _parse_raw


def _base_model():
    return _parse_raw(
        {
            "meta": {"project": "p", "schema_version": "1.3"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "C1", "status": "ACTIVE"},
                ],
            },
            "relationships": [],
        }
    )


def _patch(ops):
    return ModelPatch(
        provenance=Provenance(
            work_order_id="wo-1",
            model_version="rev-1",
            prompt_digest="d",
        ),
        operations=ops,
    )


def test_apply_add_component():
    m = _base_model()
    p = _patch(
        [
            {
                "op": "add",
                "target_kind": "components",
                "value": {"id": "COMP-2", "name": "C2", "status": "ACTIVE"},
            }
        ]
    )
    m2 = apply_model_patch(m, p)
    ids = {c.id for c in m2.entities.components}
    assert ids == {"COMP-1", "COMP-2"}


def test_apply_remove_component():
    m = _base_model()
    p = _patch([{"op": "remove", "target_id": "COMP-1"}])
    m2 = apply_model_patch(m, p)
    assert m2.entities.components == []


def test_apply_replace_component_field():
    m = _base_model()
    p = _patch(
        [
            {
                "op": "replace",
                "target_id": "COMP-1",
                "field": "name",
                "value": "renamed",
            }
        ]
    )
    m2 = apply_model_patch(m, p)
    assert m2.entities.components[0].name == "renamed"


def test_apply_unknown_op_raises_parse_error():
    m = _base_model()
    p = _patch([{"op": "nuke", "target_id": "COMP-1"}])
    with pytest.raises(ParseError):
        apply_model_patch(m, p)


def test_apply_move_op_raises_parse_error_not_supported():
    m = _base_model()
    p = _patch([{"op": "move", "target_id": "COMP-1"}])
    with pytest.raises(ParseError):
        apply_model_patch(m, p)


def test_apply_does_not_mutate_input():
    m = _base_model()
    original_ids = [c.id for c in m.entities.components]
    apply_model_patch(
        m, _patch([{"op": "remove", "target_id": "COMP-1"}])
    )
    assert [c.id for c in m.entities.components] == original_ids
