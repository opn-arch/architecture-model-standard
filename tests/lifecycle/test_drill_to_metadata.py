"""Tests for drill_to metadata on root-family projectors (Phase 3 Task 16).

Each root-family projector attaches ``facets["drill_to"] = {entity_id:
"familyN.entity_page:<entity_id>"}`` to its :class:`DiagramSpec`.
Coverage per family follows the ``EntityPageProjector`` matrix. This is
metadata only — the rendered ``body`` is unchanged.
"""

from __future__ import annotations

from textwrap import dedent

import pytest

from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.drill import drill_to_map
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

import yaml


_YAML = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: drill
    entities:
      actors:
        - id: ACT-1
          name: Operator
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: Ignition
          status: ACTIVE
      behaviors:
        - id: BEH-1
          name: Start
          status: ACTIVE
      interfaces:
        - id: IF-1
          name: TickAPI
          status: ACTIVE
      constraints:
        - id: CON-1
          name: MaxTemp
          status: ACTIVE
      layers:
        - id: LAY-1
          name: Web
          status: ACTIVE
      components:
        - id: COMP-1
          name: Engine
          status: ACTIVE
      environments:
        - id: ENV-1
          name: Prod
          status: ACTIVE
      resources:
        - id: RES-1
          name: DB
          status: ACTIVE
    relationships: []
    """
)


@pytest.fixture
def model():
    return _parse_raw(yaml.safe_load(_YAML))


def test_drill_to_map_family3_includes_components_and_layers(model):
    dt = drill_to_map(model, 3)
    assert dt["COMP-1"] == "family3.entity_page:COMP-1"
    assert dt["LAY-1"] == "family3.entity_page:LAY-1"
    assert "CAP-F1" not in dt
    assert "ACT-1" not in dt


def test_drill_to_map_family4_includes_behaviors_and_actors(model):
    dt = drill_to_map(model, 4)
    assert dt["BEH-1"] == "family4.entity_page:BEH-1"
    assert dt["ACT-1"] == "family4.entity_page:ACT-1"
    assert "COMP-1" not in dt


def test_drill_to_map_family6_includes_interfaces_and_components(model):
    dt = drill_to_map(model, 6)
    assert dt["IF-1"] == "family6.entity_page:IF-1"
    assert dt["COMP-1"] == "family6.entity_page:COMP-1"


def test_drill_to_map_family1_includes_all_kinds(model):
    dt = drill_to_map(model, 1)
    for eid in ("ACT-1", "CAP-F1", "BEH-1", "IF-1", "CON-1", "LAY-1", "COMP-1"):
        assert dt[eid] == f"family1.entity_page:{eid}"


def test_drill_to_map_family5_includes_components_environments_resources(model):
    dt = drill_to_map(model, 5)
    assert dt["COMP-1"] == "family5.entity_page:COMP-1"
    assert dt["ENV-1"] == "family5.entity_page:ENV-1"
    assert dt["RES-1"] == "family5.entity_page:RES-1"
    assert "CAP-F1" not in dt
    assert "ACT-1" not in dt


def test_drill_to_map_unknown_family_returns_empty(model):
    assert drill_to_map(model, 99) == {}


def test_mermaid_adapter_emits_drill_to(model):
    fn, _v = DEFAULT_REGISTRY.get("family3.component_diagram")
    spec = fn(model, {})
    assert "drill_to" in spec.facets
    assert spec.facets["drill_to"]["COMP-1"] == "family3.entity_page:COMP-1"
    # Ensure body content is unchanged (still a mermaid string).
    assert spec.facets["content_kind"] == "mermaid"
    assert isinstance(spec.facets["body"], str)


def test_nonse_adapter_emits_drill_to(model):
    fn, _v = DEFAULT_REGISTRY.get("family6.icd")
    spec = fn(model, {})
    assert "drill_to" in spec.facets
    assert spec.facets["drill_to"]["IF-1"] == "family6.entity_page:IF-1"
    assert spec.facets["content_kind"] == "markdown"


def test_family8_index_adapter_emits_drill_to(model):
    fn, _v = DEFAULT_REGISTRY.get("family8.index")
    spec = fn(model, {})
    dt = spec.facets["drill_to"]
    # family8 covers component, capability, interface.
    assert dt["COMP-1"] == "family8.entity_page:COMP-1"
    assert dt["CAP-F1"] == "family8.entity_page:CAP-F1"
    assert dt["IF-1"] == "family8.entity_page:IF-1"
    assert "ACT-1" not in dt
    assert "LAY-1" not in dt
