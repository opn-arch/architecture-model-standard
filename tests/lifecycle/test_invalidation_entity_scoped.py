"""Tests for entity-scoped view invalidation (Phase 3 Task 18).

``entity_change_stale_set(entity_id, family, model)`` returns the set
of view IDs that must be rebuilt when ``entity_id`` changes:

* the entity's own family-N page,
* its ``contains`` parent's page (roll-up may change),
* each ``contains``-sibling's page (peer roll-up may change),
* the family-N root view.

All IDs use the colon form (``family{N}.entity_page:{entity_id}``) to
match the ``DiagramSpec.id`` convention.
"""

from __future__ import annotations

from textwrap import dedent

import pytest
import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.invalidation import (
    _find_parent,
    _find_peers,
    entity_change_stale_set,
)


_YAML = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: inval
    entities:
      layers:
        - id: LAY-1
          name: Web
          status: ACTIVE
      components:
        - id: COMP-1
          name: Root
          status: ACTIVE
        - id: COMP-1A
          name: Child A
          status: ACTIVE
        - id: COMP-1B
          name: Child B
          status: ACTIVE
        - id: COMP-1C
          name: Child C
          status: ACTIVE
        - id: COMP-ISO
          name: Isolated
          status: ACTIVE
    relationships:
      - {from: COMP-1, to: COMP-1A, type: contains}
      - {from: COMP-1, to: COMP-1B, type: contains}
      - {from: COMP-1, to: COMP-1C, type: contains}
      - {from: LAY-1, to: COMP-1, type: contains}
    """
)


@pytest.fixture
def model():
    return _parse_raw(yaml.safe_load(_YAML))


def test_find_parent_returns_containing_entity(model):
    assert _find_parent("COMP-1A", model) == "COMP-1"
    assert _find_parent("COMP-1", model) == "LAY-1"


def test_find_parent_returns_none_when_no_container(model):
    assert _find_parent("COMP-ISO", model) is None


def test_find_peers_returns_siblings_sorted(model):
    assert _find_peers("COMP-1A", model) == ("COMP-1B", "COMP-1C")


def test_find_peers_empty_when_no_parent(model):
    assert _find_peers("COMP-ISO", model) == ()


def test_entity_change_stale_set_includes_self_and_root(model):
    stale = entity_change_stale_set("COMP-ISO", 3, model)
    assert "family3.entity_page:COMP-ISO" in stale
    assert "family3.root" in stale
    # No parent, no peers.
    assert len(stale) == 2


def test_entity_change_stale_set_includes_parent(model):
    stale = entity_change_stale_set("COMP-1A", 3, model)
    assert "family3.entity_page:COMP-1A" in stale
    assert "family3.entity_page:COMP-1" in stale
    assert "family3.root" in stale


def test_entity_change_stale_set_includes_peers(model):
    stale = entity_change_stale_set("COMP-1A", 3, model)
    assert "family3.entity_page:COMP-1B" in stale
    assert "family3.entity_page:COMP-1C" in stale


def test_entity_change_stale_set_family_prefix_varies(model):
    for fam in (1, 2, 3, 4, 6, 7, 8):
        stale = entity_change_stale_set("COMP-1A", fam, model)
        assert f"family{fam}.entity_page:COMP-1A" in stale
        assert f"family{fam}.root" in stale


def test_entity_change_stale_set_deterministic_across_calls(model):
    a = entity_change_stale_set("COMP-1A", 3, model)
    b = entity_change_stale_set("COMP-1A", 3, model)
    assert a == b
